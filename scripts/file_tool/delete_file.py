"""
行内工具：删除用户指定的任意文件或文件夹
用法（行内）: 直接调用 run(args, workspace)
用法（脚本）: python delete_file.py '<json_params>'
"""
import sys
import json
import os
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _utils import normalize, safe_strip
from _protocol import success, error


def run(args: dict, _workspace: str) -> str:
    """行内工具入口: (args, workspace) -> str"""
    target_path = safe_strip(args.get("target_path", ""))

    if not target_path:
        return "参数缺失：target_path 为必填，请指定要删除的文件或文件夹路径"

    target_path = normalize(target_path)

    if not os.path.exists(target_path):
        return f"路径不存在：{target_path}"

    try:
        if os.path.isfile(target_path):
            os.remove(target_path)
            kind = "文件"
        elif os.path.isdir(target_path):
            shutil.rmtree(target_path)
            kind = "文件夹"
        else:
            return f"无法识别的路径类型：{target_path}"
    except PermissionError:
        return f"权限不足，无法删除：{target_path}"
    except OSError as e:
        return f"删除失败：{target_path}\n{str(e)}"

    # 严格校验
    if not os.path.exists(target_path):
        return f"{kind}删除成功：{target_path}"
    else:
        return f"删除后校验失败，{kind}可能未被完全删除：{target_path}"


def main():
    """独立脚本入口"""
    params = json.loads(sys.argv[1])
    target_path = params.get("target_path", "")
    result = run({"target_path": target_path}, "")
    if "删除成功" in result:
        success(result)
    else:
        error(result)


if __name__ == "__main__":
    main()
