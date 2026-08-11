"""
小鱼骨项目 — AI 对话编排引擎
负责：系统提示词构建、AI 输出 JSON 解析、工具调用循环
注意：本模块不导入 arcpy，不感知子进程细节
"""
import json
import time as _time
from .config import (
    get_ai_client, get_ai_model, get_ai_provider, OLLAMA_BASE_URL,
)
from .tool_registry import TOOLS


# ── 系统提示词模板 ────────────────────────────────────────────────────
_SYSTEM_PROMPT_TEMPLATE = """【小鱼骨项目强制执行规则 — 违反任何一条必须重新生成】

【工具调用格式铁律】
铁律1: 调用工具时只输出纯JSON {{"name": "工具名", "arguments": {{"参数名": "参数值"}}}}，一个字不能多
铁律2: 禁止输出```、```json、<tool_call>、markdown等任何标签或包装
铁律3: 禁止在JSON前后加解释、说明、问候语、多余换行
铁律4: 参数值中的路径统一使用正斜杠 /，禁止反斜杠
铁律5: 工具参数严格按照工具定义传入，禁止篡改参数名、随意赋值

【多任务解析与执行铁律】
铁律6: 自动拆分连续多条自然语言指令，梳理先后执行次序
铁律7: 主动识别任务前后依赖关系，前置任务未完成不得执行后续依赖任务
铁律8: 任务相互隔离，变量、文件、空间状态互不干扰，杜绝任务数据混杂错乱
铁律9: 逐条校验单任务合法性，参数缺失、要素不存在等问题自动识别标记

【任务结果总结铁律】
铁律10: 全部任务执行结束后，自动汇总整体执行情况
铁律11: 统计总任务数量、成功数量、失败数量，逐条罗列任务执行结果
铁律12: 标注失败任务，清晰写明报错诱因，同步给出简易修正方向
铁律13: 整理规整问题清单，条理分明呈现内容，避免信息混乱交织

【GIS操作行为铁律】
铁律14: 所有GIS操作必须调用对应工具，禁止自行编写ArcPy代码
铁律15: 创建要素类必须调用 Create_Element 工具，禁止自行调用CreateFeatureclass相关逻辑
铁律16: 要素类名称仅填写纯名称，禁止附带.shp后缀
铁律17: GDB地理数据库仅填写纯名称，工具自动补充.gdb后缀
铁律18: 创建操作完成后，必须调用Describe_GDB或list_files_in_workspace核验结果，严禁虚构执行状态
铁律19: 仅获取文件夹名称无完整路径时，先调用get_current_workspace获取目录，检索拼接完整路径后再传参，禁止主观猜测路径
铁律20: 所有对象名称（文件名、要素类名、数据集名、字段名）必须原样匹配用户输入，禁止中英文自动翻译互通。用户说"城市"就只能找"城市"，绝不能找"City"；用户说"roads"就只能找"roads"，绝不能找"道路"
铁律21: 当优先参考路径已设置且用户只给对象名称不给出完整路径时，严格三步执行：第1步调用 Tree_List 或 list_files_in_workspace 扫描优先参考路径；第2步在扫描结果中定位与用户名称完全一致的目标；第3步补齐完整路径后执行操作。三步缺一不可，严禁跳过扫描直接编造路径

【地图数据展示铁律】
铁律22: 当你调用 Geocode 或 POISearch 获取到坐标数据后，必须在最终回复末尾附加 __MAP_DATA__ 标记
铁律23: 让地图自动标点的格式：__MAP_DATA__:{{"center":[纬度,经度],"zoom":15,"markers":[{{"name":"名称","lat":纬度,"lon":经度}},...]}}
铁律24: center 取中心点坐标，zoom 根据范围选 12~17，markers 包含所有返回的 POI
铁律25: __MAP_DATA__ 必须单独一行放在回复末尾，AI 的文字回复正常输出在前面

【当前环境】
当前工作目录：{workspace}
{focus_path}你是小鱼骨GIS助手，回答简洁专业。不凭空判定目录内容，优先调用工具获取真实数据。

【可用工具及调用示例】
{tools_desc}"""


# ── 工具描述预渲染（服务启动时执行一次，避免每次请求重算） ──────────
_TOOL_EXAMPLES = {
    "get_current_workspace": '{"name": "get_current_workspace", "arguments": {}}',
    "list_files_in_workspace": '{"name": "list_files_in_workspace", "arguments": {}}',
}

def _build_tools_desc() -> str:
    """遍历 TOOLS 列表生成 AI 可读文本（仅模块加载时调用一次）"""
    lines = []
    for tool in TOOLS:
        params_desc = []
        for p in tool.params:
            req_mark = "必填" if p.required else "可选"
            params_desc.append(f"    {p.name}({p.type},{req_mark}): {p.description}")
        param_text = "\n".join(params_desc) if params_desc else "    无参数"
        example = _TOOL_EXAMPLES.get(tool.name, "")
        lines.append(f"- {tool.name}: {tool.description}\n  参数:\n{param_text}")
        if example:
            lines.append(f"  调用示例: {example}")
    return "\n".join(lines)

_TOOLS_DESC_CACHE = _build_tools_desc()  # 启动时预渲染一次

def build_system_prompt(workspace: str, focus_path: str = "") -> str:
    """构建完整系统提示词"""
    fp = (
        f"当前优先参考路径：{focus_path}\n"
        "（用户只给名称时，必须先扫描此目录找到对象补齐完整路径，再操作）\n"
    ) if focus_path else ""
    return _SYSTEM_PROMPT_TEMPLATE.format(
        workspace=workspace,
        focus_path=fp,
        tools_desc=_TOOLS_DESC_CACHE,
    )


def parse_tool_call(text: str) -> dict | None:
    """从 AI 原始输出中提取 JSON 工具调用指令，支持多种格式容错"""
    if not text:
        return None
    text = text.strip()

    candidates = []

    # 1. 整个文本就是 JSON
    candidates.append(text)

    # 2. 去掉 markdown 代码块 ```json ... ``` 或 ``` ... ```
    for marker in ["```json", "```"]:
        if text.startswith(marker):
            end_marker = text.find("\n", len(marker))
            inner = text[end_marker + 1:] if end_marker != -1 else text[len(marker):]
            if inner.endswith("```"):
                inner = inner[:-3]
            candidates.append(inner.strip())
        if marker in text:
            idx = text.find(marker)
            inner_start = text.find("\n", idx + len(marker))
            if inner_start != -1:
                inner = text[inner_start + 1:]
                end_idx = inner.rfind("```")
                if end_idx != -1:
                    inner = inner[:end_idx]
                candidates.append(inner.strip())

    # 3. 括号计数提取第一个完整 JSON 对象
    start = text.find("{")
    if start != -1:
        depth = 0
        end = -1
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end != -1:
            candidates.append(text[start:end + 1])

    for candidate in candidates:
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict) and "name" in obj:
                return obj
        except (json.JSONDecodeError, Exception):
            pass

    return None


# ── 任务拆分与上下文管理 ────────────────────────────────────────────────

import re as _re

# 分隔符：中文逗号/句号/顿号/分号 + 英文逗号/分号 + 换行
_TASK_SEP = _re.compile(r'[，,。、；;\n]+')

# 会话级优先参考路径
_FOCUS_PATH = ""
_WIN_PATH_RE = _re.compile(r'[A-Za-z]:[/\\][^\s,，。、；;]+')


def _extract_focus_path(prompt: str) -> str:
    """从用户输入中提取绝对路径，找到 .gdb 之前的部分作为优先参考路径"""
    paths = _WIN_PATH_RE.findall(prompt)
    if not paths:
        return ""
    raw = paths[0].replace("\\", "/")
    parts = [p for p in raw.split("/") if p]
    if len(parts) < 2:
        return ""
    # 从右往左定位 .gdb
    gdb_idx = -1
    for i in range(len(parts) - 1, -1, -1):
        if ".gdb" in parts[i].lower():
            gdb_idx = i
            break
    if gdb_idx <= 0:
        return ""
    # .gdb 之前的部分即为优先参考路径
    return "/".join(parts[:gdb_idx])


def _split_tasks(prompt: str) -> list[str]:
    """按中英文标点拆分用户输入为独立子任务列表"""
    parts = _TASK_SEP.split(prompt)
    return [p.strip() for p in parts if p.strip()]


def _clean_history(history: list) -> list:
    """只保留系统消息和工具执行结果，丢弃旧用户指令防止窜扰"""
    cleaned = []
    for msg in history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "system":
            cleaned.append(msg)
        elif role == "user" and content.startswith("工具执行结果"):
            cleaned.append(msg)
    return cleaned


# ── 单任务工具调用循环 ──────────────────────────────────────────────────# ── 单任务工具调用循环 ──────────────────────────────────────────────────

def _run_one_task(
    task_prompt: str,
    messages: list,
    workspace: str,
    execute_tool_fn,
) -> str:
    """
    执行单个子任务：多步工具调用循环。
    AI 可连续调用多个工具（如先 Geocode → 再 POISearch），
    最多 max_turns 次工具调用后自动终止并返回最终回复。
    """
    messages.append({"role": "user", "content": task_prompt})
    max_turns = 5

    for turn in range(max_turns):
        t0 = _time.time()
        response = get_ai_client().chat.completions.create(
            model=get_ai_model(), messages=messages, temperature=0.1
        )
        ai_text = response.choices[0].message.content.strip()
        print(f"[AI推理耗时] {get_ai_provider()} turn {turn+1}: {_time.time() - t0:.2f}s")

        tool_call = parse_tool_call(ai_text)
        if tool_call is None:
            return ai_text

        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("arguments", {})
        if not isinstance(tool_args, dict):
            tool_args = {}

        result = execute_tool_fn(tool_name, tool_args, workspace)

        messages.append({"role": "assistant", "content": ai_text})
        messages.append({
            "role": "user",
            "content": f"工具执行结果：\n{result}"
        })

    messages.append({
        "role": "user",
        "content": "已达到最大工具调用次数，请根据已有结果直接回答用户问题，不要再调用工具。"
    })
    response = get_ai_client().chat.completions.create(
        model=get_ai_model(), messages=messages, temperature=0.1
    )
    return response.choices[0].message.content.strip()


# ── 任务调度器 ────────────────────────────────────────────────────────

class TaskScheduler:
    """多任务调度器：依赖校验 → 原子执行 → 失败重试 → 状态汇总"""

    def __init__(self, workspace: str, execute_tool_fn):
        self._tasks: list[dict] = []
        self._status: dict[str, str] = {}    # task_id → waiting|running|success|failed|retry
        self._results: dict[str, str] = {}   # task_id → answer text
        self._workspace = workspace
        self._execute = execute_tool_fn
        self._max_retries = 2

    @property
    def task_count(self) -> int:
        return len(self._tasks)

    def add(self, task_id: str, prompt: str) -> None:
        """注册一个子任务"""
        self._tasks.append({"id": task_id, "prompt": prompt})
        self._status[task_id] = "等待中"

    def run(self, messages: list) -> str:
        """
        顺序执行全部任务。
        - 每个任务执行前校验前置依赖（前序任务必须全部成功）
        - 失败自动重试（最多 self._max_retries 次）
        - 原子隔离：任务间通过 messages 共享进度，异常不污染后续
        返回汇总报告字符串。
        """
        for i, task in enumerate(self._tasks):
            tid = task["id"]

            # ── 依赖校验：前序任务是否全部成功 ──
            for j in range(i):
                prev_id = self._tasks[j]["id"]
                if self._status[prev_id] != "成功":
                    self._status[tid] = "失败"
                    self._results[tid] = f"前置任务 [{prev_id}] 未成功，跳过执行"
                    continue

            if self._status[tid] == "失败":
                continue  # 依赖校验未通过

            # ── 执行 + 重试 ──
            self._status[tid] = "执行中"
            for attempt in range(self._max_retries + 1):
                try:
                    ans = _run_one_task(
                        task["prompt"], messages,
                        self._workspace, self._execute,
                    )
                    self._status[tid] = "成功"
                    self._results[tid] = ans
                    break
                except Exception as e:
                    if attempt < self._max_retries:
                        self._status[tid] = f"重试 {attempt+1}/{self._max_retries}"
                    else:
                        self._status[tid] = "失败"
                        self._results[tid] = f"重试 {self._max_retries} 次后仍失败：{e}"

        return self._build_summary()

    def _build_summary(self) -> str:
        """生成带状态图标的汇总报告"""
        icons = {"成功": "[OK]", "失败": "[FAIL]", "等待中": "[...]", "执行中": "[...]"}
        lines = [f"任务执行汇总（共 {len(self._tasks)} 项）", ""]
        success_count = 0
        fail_count = 0
        for task in self._tasks:
            tid = task["id"]
            st = self._status[tid]
            icon = icons.get(st, "[...]")
            if "重试" in st:
                icon = "[RETRY]"
            prompt_preview = task["prompt"][:50]
            lines.append(f"  {icon} {tid}: {prompt_preview}")
            if st == "成功":
                success_count += 1
            elif st == "失败":
                fail_count += 1
                lines.append(f"       原因: {self._results.get(tid, '未知')[:80]}")
        lines.append("")
        lines.append(f"成功 {success_count} / 失败 {fail_count}")
        return "\n".join(lines)


# ── 对话处理入口 ──────────────────────────────────────────────────────

def process_chat(prompt: str, history: list, workspace: str,
                 execute_tool_fn) -> dict:
    """
    处理一轮对话。自动拆分多任务输入，TaskScheduler 调度执行。
    返回 {"answer": str, "current_workspace": str} 或 {"error": str}
    """
    global _FOCUS_PATH
    try:
        # 从用户输入提取优先参考路径
        fp = _extract_focus_path(prompt)
        if fp:
            _FOCUS_PATH = fp
        system_content = build_system_prompt(workspace, _FOCUS_PATH)
        tasks = _split_tasks(prompt)

        messages = [{"role": "system", "content": system_content}]
        messages.extend(_clean_history(history))

        # 单任务：直接执行
        if len(tasks) == 1:
            answer = _run_one_task(tasks[0], messages, workspace, execute_tool_fn)
            return {"answer": answer, "current_workspace": workspace}

        # 多任务：调度器接管
        scheduler = TaskScheduler(workspace, execute_tool_fn)
        for i, task in enumerate(tasks):
            scheduler.add(f"T{i+1}", task)
        summary = scheduler.run(messages)
        return {"answer": summary, "current_workspace": workspace}

    except Exception as e:
        err_msg = str(e)
        if "Connection" in err_msg or "connect" in err_msg:
            if get_ai_provider() == "api":
                err_msg = (
                    f"无法连接 DeepSeek API，请检查网络或 API Key 是否有效。"
                    f"原始错误：{err_msg}"
                )
            else:
                err_msg = (
                    f"无法连接 Ollama ({OLLAMA_BASE_URL})，"
                    f"请确认 Ollama 已启动。原始错误：{err_msg}"
                )
        return {"error": err_msg}
