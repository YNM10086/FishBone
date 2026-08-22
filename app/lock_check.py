"""
小鱼骨项目 — ArcGIS 占用锁检测模块
在写操作工具执行前校验目标 GDB 的 .lock 锁文件：
- 活锁：锁文件存在且持有进程存活 → 拦截操作
- 死锁：锁文件存在但持有进程已死 → 自动清理后放行
- 未知锁：读不出 PID → 保守拦截（宁可多拦不错删）
"""
import ctypes
import os
import re

_LOCK_SUFFIX = ".lock"
_GDB_SUFFIX = ".gdb"

# 文本锁文件中的 PID 提取模式：ProcessID: 1234 / PID=1234 / Process: 1234
_PID_RE = re.compile(r"(?:process\s*(?:id)?|pid)\s*[=:]\s*(\d{2,})", re.IGNORECASE)


def _extract_gdb_paths(args: dict) -> list[str]:
    """从工具参数中收集所有路径，定位其中涉及的 .gdb 目录（去重、存在性校验）"""
    gdbs: set[str] = set()
    for value in args.values():
        if not isinstance(value, str):
            continue
        path = value.strip().strip('"').strip("'")
        if not path:
            continue
        idx = path.lower().find(_GDB_SUFFIX)
        if idx == -1:
            continue
        gdb = os.path.normpath(path[: idx + len(_GDB_SUFFIX)])
        if os.path.isdir(gdb):
            gdbs.add(gdb)
    return sorted(gdbs)


def _list_lock_files(gdb_path: str) -> list[str]:
    """列出 GDB 内的 .lock 隐藏文件（含 GDB 目录外的 <gdb>.lock）"""
    lock_files: list[str] = []
    try:
        for name in os.listdir(gdb_path):
            if name.lower().endswith(_LOCK_SUFFIX):
                lock_files.append(os.path.join(gdb_path, name))
    except OSError:
        pass
    outside = gdb_path + _LOCK_SUFFIX
    if os.path.exists(outside):
        lock_files.append(outside)
    return lock_files


def _read_pid(lock_file: str) -> int | None:
    """从锁文件内容提取持有进程 PID；读不出则返回 None（保守处理）"""
    try:
        with open(lock_file, "rb") as f:
            raw = f.read(4096)
    except OSError:
        return None
    text = raw.decode("utf-8", errors="ignore")
    match = _PID_RE.search(text)
    if match:
        return int(match.group(1))
    return None


def _is_process_alive(pid: int) -> bool:
    """Windows 下检测进程是否存活（OpenProcess + GetExitCodeProcess == STILL_ACTIVE）"""
    if pid <= 0:
        return False
    try:
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        try:
            exit_code = ctypes.c_ulong(0)
            if not ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return False
            return exit_code.value == 259  # STILL_ACTIVE
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    except Exception:
        return False


def check_locks(args: dict) -> dict:
    """
    主入口：检查工具参数涉及的 GDB 锁状态
    返回 {"blocked": bool, "alive": list, "cleaned": list, "unknown": list}
    - alive:   活锁文件（持有进程存活）——ArcGIS Pro 打开 GDB 浏览属正常现象，
               锁为共享锁，外部 arcpy 写入通常可成功，故【不拦截】，仅记录
    - cleaned: 已清理的死锁文件（持有进程已死，残留锁会阻塞 Pro/arcpy）
    - unknown: 读不出 PID 的锁文件——同样【不拦截】，
               真实冲突由 runner 的 000464/schema lock 翻译兜底
    （2026-08-22 调整：原"活锁一律拦截"导致开着 Pro 时所有写操作被误拦，
     缓冲区/创建要素等无法使用；改为放行 + 死锁清理 + 错误兜底翻译）
    """
    result: dict = {"blocked": False, "alive": [], "cleaned": [], "unknown": []}

    for gdb in _extract_gdb_paths(args):
        for lock_file in _list_lock_files(gdb):
            pid = _read_pid(lock_file)
            if pid is None:
                result["unknown"].append(lock_file)
                continue
            if _is_process_alive(pid):
                result["alive"].append(lock_file)
                continue
            # 死锁：持有进程已死，安全清理后放行
            try:
                os.remove(lock_file)
                result["cleaned"].append(lock_file)
            except OSError:
                # 删除失败（文件被占用/权限）→ 记为 unknown，不拦截
                result["unknown"].append(lock_file)

    return result
