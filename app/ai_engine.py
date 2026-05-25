"""
小鱼骨项目 — AI 对话编排引擎
负责：系统提示词构建、AI 输出 JSON 解析、工具调用循环
注意：本模块不导入 arcpy，不感知子进程细节
"""
import json
from .config import client, OLLAMA_MODEL, OLLAMA_BASE_URL
from .tool_registry import TOOLS


# ── 系统提示词模板 ────────────────────────────────────────────────────
_SYSTEM_PROMPT_TEMPLATE = """【小鱼骨项目强制执行规则 — 违反任何一条必须重新生成】

【工具调用格式铁律】
铁律1: 调用工具时只输出纯JSON {{"name": "工具名", "arguments": {{"参数名": "参数值"}}}}，一个字不能多
铁律2: 禁止输出```、```json、<tool_call>、markdown等任何标签或包装
铁律3: 禁止在JSON前后加解释、说明、问候语、换行
铁律4: 参数值中的路径统一使用正斜杠 /，禁止反斜杠
铁律5: 工具参数严格按照工具定义传入，禁止瞎改参数名或参数值

【GIS操作行为铁律】
铁律6: 所有GIS操作必须调用对应工具，禁止自己写ArcPy代码
铁律7: 创建要素类必须调用 Create_Element 工具，禁止自己写 CreateFeatureclass 代码
铁律8: 要素类名称必须是纯名称（如 roads），绝对不能加 .shp 后缀（禁止 roads.shp）
铁律9: GDB 地理数据库名称必须是纯名称（如 MyProject），工具会自动加 .gdb 后缀
铁律10: 创建成功后必须调用 Describe_GDB 或 list_files_in_workspace 工具验证，禁止凭空编造结果
铁律11: 当用户只给文件夹名称（如"Data文件夹"）而非完整路径时，必须先调用 get_current_workspace 获取工作目录，再调用 Tree_List 或 list_files_in_workspace 查找目标，然后拼接完整路径（工作目录 + 文件夹名）传入工具。禁止在未确认路径的情况下直接猜测

【当前环境】
当前工作目录：{workspace}
你是小鱼骨GIS助手，回答简洁专业。不要凭空猜测目录内容，优先调用工具获取实际信息。

【可用工具及调用示例】
{tools_desc}"""


def build_tools_prompt() -> str:
    """把 TOOLS 列表转成 AI 可读的格式描述文本"""
    examples = {
        "get_current_workspace": '{"name": "get_current_workspace", "arguments": {}}',
        "list_files_in_workspace": '{"name": "list_files_in_workspace", "arguments": {}}',
    }
    lines = []
    for tool in TOOLS:
        params_desc = []
        for p in tool.params:
            req_mark = "必填" if p.required else "可选"
            params_desc.append(f"    {p.name}({p.type},{req_mark}): {p.description}")
        param_text = "\n".join(params_desc) if params_desc else "    无参数"

        example = examples.get(tool.name, "")
        lines.append(f"- {tool.name}: {tool.description}\n  参数:\n{param_text}")
        if example:
            lines.append(f"  调用示例: {example}")
    return "\n".join(lines)


def build_system_prompt(workspace: str) -> str:
    """构建完整的系统提示词"""
    return _SYSTEM_PROMPT_TEMPLATE.format(
        workspace=workspace,
        tools_desc=build_tools_prompt()
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


# ── 对话处理入口 ──────────────────────────────────────────────────────

def process_chat(prompt: str, history: list, workspace: str,
                 execute_tool_fn) -> dict:
    """
    处理一轮对话，返回 {"answer": str, "current_workspace": str} 或 {"error": str}
    execute_tool_fn: (name, args, workspace) -> str
    """
    try:
        system_content = build_system_prompt(workspace)

        messages = [{"role": "system", "content": system_content}]
        messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        # 工具调用循环（最多 3 轮）
        for _ in range(3):
            response = client.chat.completions.create(
                model=OLLAMA_MODEL,
                messages=messages,
                temperature=0.1
            )
            ai_text = response.choices[0].message.content.strip()

            tool_call = parse_tool_call(ai_text)
            if tool_call is None:
                return {"answer": ai_text, "current_workspace": workspace}

            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("arguments", {})
            if not isinstance(tool_args, dict):
                tool_args = {}

            result = execute_tool_fn(tool_name, tool_args, workspace)

            messages.append({"role": "assistant", "content": ai_text})
            messages.append({
                "role": "user",
                "content": (
                    f"工具执行结果：\n{result}\n\n"
                    "请根据这个结果直接回答用户的问题，不要再调用工具。"
                )
            })

        # 兜底：循环耗尽后强制 AI 直接回答
        response = client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=messages,
            temperature=0.1
        )
        return {"answer": response.choices[0].message.content, "current_workspace": workspace}

    except Exception as e:
        err_msg = str(e)
        if "Connection" in err_msg or "connect" in err_msg:
            err_msg = (
                f"无法连接 Ollama ({OLLAMA_BASE_URL})，"
                f"请确认 Ollama 已启动。原始错误：{err_msg}"
            )
        return {"error": err_msg}
