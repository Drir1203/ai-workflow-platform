"""文档解析：md/txt/pdf/docx → 纯文本。"""

import io
import re

from docx import Document as DocxDocument
from pypdf import PdfReader

_CONTENT_TYPES = {
    "md": "md",
    "markdown": "md",
    "txt": "txt",
    "text": "txt",
    "pdf": "pdf",
    "docx": "docx",
}


def _decode_text(data: bytes) -> str:
    """文本解码：优先 UTF-8，中文 GBK/GB18030 兜底。"""
    for enc in ("utf-8", "gb18030"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _collapse(text: str) -> str:
    """归一换行并压缩连续空行为单个空行（保留段落边界给 chunker）。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\n{3,}", "\n\n", text)


def parse_text(raw: str) -> str:
    return _collapse(raw)


def parse_markdown(raw: str) -> str:
    """去掉代码围栏（```），保留标题与正文。"""
    text = re.sub(r"(?s)```.*?```", "", raw)
    return _collapse(text)


def parse_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    pages: list[str] = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001 - 单页提取失败不阻断整份文档
            pages.append("")
    return _collapse("\n".join(pages))


def parse_docx(data: bytes) -> str:
    doc = DocxDocument(io.BytesIO(data))
    return _collapse("\n".join(p.text for p in doc.paragraphs if p.text))


def parse_document(content_type: str, data: bytes) -> str:
    """按类型解析为纯文本。未知格式/解析失败抛 ValueError（带友好文案）。"""
    ct = _CONTENT_TYPES.get(content_type.lower())
    if ct is None:
        raise ValueError(f"不支持的文档格式: {content_type}")
    try:
        if ct == "md":
            return parse_markdown(_decode_text(data))
        if ct == "txt":
            return parse_text(_decode_text(data))
        if ct == "pdf":
            return parse_pdf(data)
        return parse_docx(data)
    except ValueError:
        raise
    except Exception as exc:  # noqa: BLE001 - 统一为友好错误
        raise ValueError(f"文档解析失败: {exc}") from exc
