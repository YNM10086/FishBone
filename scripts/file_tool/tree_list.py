"""
独立脚本 / 行内工具：递归遍历路径，输出带缩进的树状结构
用法（行内）: 直接调用 run(args, workspace)
用法（脚本）: python tree_list.py '<json_params>'
"""
import sys
import json
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _utils import normalize, safe_strip
from _protocol import success, error


def _build_tree(path: str, prefix: str = "") -> list[str]:
    """递归构建树状行列表"""
    lines: list[str] = []
    try:
        entries = sorted(os.listdir(path))
    except PermissionError:
        lines.append(f"{prefix}└── [权限不足]")
        return lines
    except OSError as e:
        lines.append(f"{prefix}└── [错误: {e}]")
        return lines

    visible = [e for e in entries if not e.startswith(".")]

    for i, name in enumerate(visible):
        full = os.path.join(path, name)
        is_last = (i == len(visible) - 1)
        connector = "└── " if is_last else "├── "

        if os.path.isdir(full):
            lines.append(f"{prefix}{connector}📁 {name}")
            sub_prefix = prefix + ("    " if is_last else "│   ")
            lines.extend(_build_tree(full, sub_prefix))
        else:
            lines.append(f"{prefix}{connector}📄 {name}")

    return lines


def run(args: dict, workspace: str) -> str:
    """行内工具入口: (args, workspace) -> str"""
    path = safe_strip(args.get("path", "")) or workspace

    if not path:
        return "未指定路径，且工作目录未设置"

    path = normalize(path)

    if not os.path.isdir(path):
        return f"路径不存在或不是文件夹：{path}"

    root_name = os.path.basename(path) or path
    lines = [f"📁 {root_name}"]
    lines.extend(_build_tree(path))
    return "\n".join(lines)


def main():
    """独立脚本入口"""
    params = json.loads(sys.argv[1])
    path = params.get("path", "")
    ws = params.get("workspace", "")
    result = run({"path": path}, ws)
    success(result)


if __name__ == "__main__":
    main()
