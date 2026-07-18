"""
小鱼骨项目 — 对话历史持久化
每次对话后自动保存到 _chat_history.json，启动时自动加载
历史过长时自动精简压缩，避免 token 膨胀
"""
import json
import os
from .config import PROJECT_ROOT

_HISTORY_FILE = os.path.join(PROJECT_ROOT, "_chat_history.json")

# ── 压缩策略 ─────────────────────────────────────────────────────────
MAX_EXCHANGES = 30       # 最多保留 30 轮对话
KEEP_FIRST = 2           # 保留前 2 轮（初始上下文）
KEEP_LAST = 10           # 保留后 10 轮（近期上下文）


def _compress_history(history: list) -> list:
    """历史超出阈值时压缩中间部分为摘要，保留首尾完整"""
    if len(history) <= MAX_EXCHANGES * 2:
        return history

    # 统计对话轮数（一个 user + assistant 算一轮）
    exchanges = 0
    for msg in history:
        if msg.get("role") == "user":
            exchanges += 1
    if exchanges <= MAX_EXCHANGES:
        return history

    # 按角色配对找到截断边界
    first_end = 0
    count = 0
    for i, msg in enumerate(history):
        if msg.get("role") == "user":
            count += 1
            if count == KEEP_FIRST:
                first_end = i + 2  # 包含对应的 assistant 回复
                break

    last_start = len(history)
    count = 0
    for i in range(len(history) - 1, -1, -1):
        if history[i].get("role") == "assistant":
            count += 1
            if count == KEEP_LAST:
                last_start = i
                break

    if first_end >= last_start:
        return history

    # 提取被压缩部分的 user 消息做摘要
    middle = history[first_end:last_start]
    summary_parts = []
    for msg in middle:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user" and content:
            summary_parts.append(content[:80])

    if summary_parts:
        summary_text = "【历史摘要】此前对话涉及：" + " | ".join(summary_parts[:6])
        if len(summary_parts) > 6:
            summary_text += f" 等共 {len(summary_parts)} 项"
        compressed = [{"role": "system", "content": summary_text}]
    else:
        compressed = []

    return history[:first_end] + compressed + history[last_start:]


def save_history(history: list) -> None:
    compressed = _compress_history(history)
    with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(compressed, f, ensure_ascii=False, indent=2)


def load_history() -> list:
    if not os.path.exists(_HISTORY_FILE):
        return []
    try:
        with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def clear_history() -> None:
    if os.path.exists(_HISTORY_FILE):
        os.remove(_HISTORY_FILE)
