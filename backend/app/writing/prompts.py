"""AI 写作提示词：三个操作的系统提示词 + 消息拼装。"""

_SYSTEM_PROMPTS: dict[str, str] = {
    "continue": (
        "你是专业的中文写作助手。请根据已有文本的风格、语气与结构自然续写，"
        "直接输出续写内容，不要重复已有文字，不要加任何解释。"
    ),
    "polish": (
        "你是专业的中文编辑。请优化下面文本的措辞、语法与流畅度，"
        "保持原意、结构与 Markdown 格式不变，直接输出润色后的完整文本。"
    ),
    "summarize": (
        "你是专业的摘要助手。请提炼下面文本的核心要点，"
        "用 Markdown 列表分条输出，直接输出摘要内容。"
    ),
}


def build_writing_messages(operation: str, text: str) -> list[dict]:
    """拼装 AI 写作的消息列表：系统提示词 + 用户文本。"""
    return [
        {"role": "system", "content": _SYSTEM_PROMPTS[operation]},
        {"role": "user", "content": text},
    ]
