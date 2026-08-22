"""
锁策略修复验证 + 数据集内创建要素验证（2026-08-22）
场景：
  1. 数据集内创建点要素（排除 create_element 代码问题）
  2. 活锁（活 PID 的 .lock）：Buffer 应放行并成功（不再拦截）
  3. 死锁（死 PID 的 .lock）：自动清理并提示
运行：python tests/test_lock_fix.py（需先运行 tests/test_gen_data.py）
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.tool_registry import execute_tool  # noqa: E402

TEST_DATA = os.path.join(ROOT, "test_data")
GDB = os.path.join(TEST_DATA, "arcpy_test.gdb")

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = ""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} — {detail}")


def run(name: str, args: dict, ws: str = "") -> str:
    r = execute_tool(name, args, ws)
    print(f"  -> {r[:180].replace(chr(10), ' | ')}")
    return r


def main():
    if not os.path.isdir(GDB):
        print(f"[错误] 测试数据不存在：{GDB}\n请先运行 tests/test_gen_data.py（ArcGIS Pro Python）")
        sys.exit(1)

    # ══ 场景 1：数据集内创建点要素 ══
    print("== Create_Dataset + Create_Element（数据集内）==")
    r = run("Create_Dataset", {"gdb_path": GDB, "dataset_name": "演示数据集"})
    check("创建要素数据集成功", "要素数据集创建成功" in r, r)
    r = run("Create_Element", {
        "out_path": f"{GDB}/演示数据集",
        "out_name": "点要素",
        "geometry_type": "POINT",
    })
    check("数据集内创建点要素成功", "要素类创建成功" in r, r)

    # ══ 场景 2：活锁放行（模拟 ArcGIS Pro 打开 GDB 浏览） ══
    print("== 活锁场景：Buffer 应放行并成功 ==")
    lock = os.path.join(GDB, "_demo_activelock.lock")
    with open(lock, "w", encoding="utf-8") as f:
        f.write(f"ProcessID: {os.getpid()}")  # 当前进程存活 → 活锁
    try:
        r = run("Buffer", {
            "in_features": f"{GDB}/道路",
            "out_feature_class": f"{GDB}/缓冲区_活锁演示",
            "buffer_distance": "100 Meters",
        })
        check("活锁不拦截", "缓冲区分析完成" in r, r)
        check("无 __BLOCK_ALERT__", "__BLOCK_ALERT__" not in r, r)
    finally:
        os.remove(lock)

    # ══ 场景 3：死锁自动清理 ══
    print("== 死锁场景：自动清理 ==")
    lock2 = os.path.join(GDB, "_demo_deadlock.lock")
    with open(lock2, "w", encoding="utf-8") as f:
        f.write("ProcessID: 99999999")  # 不存在 → 死锁
    try:
        r = run("Buffer", {
            "in_features": f"{GDB}/道路",
            "out_feature_class": f"{GDB}/缓冲区_死锁演示",
            "buffer_distance": "100 Meters",
        })
        check("死锁自动清理并提示", "已自动清理 1 个残留" in r, r)
    finally:
        if os.path.exists(lock2):
            os.remove(lock2)

    # ══ 汇总 ══
    print()
    print(f"结果：PASS {PASS} / FAIL {FAIL}")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
