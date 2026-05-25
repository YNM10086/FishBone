"""
scripts/ 共享输出协议 — 所有独立脚本通过此模块输出结构化 JSON
协议：stdout 只输出一行 JSON {"ok": bool, "message"|"error": str}
"""
import json
import sys


def send(data: dict) -> None:
    """写入一行 JSON 到 stdout"""
    json.dump(data, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.stdout.flush()


def success(message: str) -> None:
    send({"ok": True, "message": message})


def error(message: str) -> None:
    send({"ok": False, "error": message})
