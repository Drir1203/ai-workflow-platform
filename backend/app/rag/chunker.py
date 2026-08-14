"""文本切片：按空行/markdown 标题切段，合并至目标大小，超长硬切。"""

import re

_HEADING = re.compile(r"^#{1,6}\s")


def _split_segments(text: str) -> list[str]:
    """按空行与 markdown 标题行切出初始片段。"""
    segments: list[str] = []
    current: list[str] = []
    for line in text.split("\n"):
        if _HEADING.match(line.strip()) and current:
            segments.append("\n".join(current))
            current = []
        current.append(line)
        if not line.strip():
            segments.append("\n".join(current))
            current = []
    if current:
        segments.append("\n".join(current))
    return segments


def chunk_text(text: str, max_chars: int = 600) -> list[str]:
    """把纯文本切成检索友好的块：短段向下合并、超长段按字符硬切。"""
    if not text.strip():
        return []
    chunks: list[str] = []
    buffer = ""
    for seg in _split_segments(text):
        seg = seg.strip()
        if not seg:
            continue
        if len(seg) > max_chars:
            if buffer:
                chunks.append(buffer)
                buffer = ""
            for i in range(0, len(seg), max_chars):
                part = seg[i : i + max_chars].strip()
                if part:
                    chunks.append(part)
        elif len(buffer) + len(seg) + 1 <= max_chars:
            buffer = f"{buffer}\n{seg}".strip() if buffer else seg
        else:
            chunks.append(buffer)
            buffer = seg
    if buffer:
        chunks.append(buffer)
    return chunks


def count_tokens(text: str) -> int:
    """token 数粗估（中文按字符、英文按空格分词）。信息用途，非计费。"""
    return len(text) // 2 + 1
