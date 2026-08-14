"""关键词检索：ASCII 词 + 中文滑动二元组，content LIKE 计分取 top-k。

中文无空格分词，整句 LIKE 匹配不上；「部署流程」拆成 部署/署流/流程 后
逐 token 匹配，按命中去重 token 数计分。SQLite/PG 通用。
"""

import re
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, DocumentChunk

_CJK = re.compile(r"[一-鿿]")
_ASCII_WORD = re.compile(r"[a-zA-Z0-9_]+")

_STOPWORDS = frozenset(
    {
        "的", "了", "是", "在", "和", "与", "及", "或", "这", "那",
        "请", "我", "你", "他", "有", "把", "被", "对", "等", "如何", "什么",
    }
)

_MAX_KEYWORDS = 12
_MAX_ROWS_PER_KEYWORD = 500


@dataclass(frozen=True)
class RetrievedChunk:
    document_id: str
    document_name: str
    seq: int
    content: str
    matched: tuple[str, ...]


def extract_keywords(query: str, limit: int = _MAX_KEYWORDS) -> list[str]:
    """查询切词：ASCII 词（小写）+ 中文滑动二元组，过滤停用词并去重。"""
    kws: list[str] = []
    seen: set[str] = set()
    for word in _ASCII_WORD.findall(query.lower()):
        if word and word not in seen:
            seen.add(word)
            kws.append(word)
    cjk = "".join(_CJK.findall(query))
    for i in range(len(cjk) - 1):
        bigram = cjk[i : i + 2]
        if bigram in _STOPWORDS or bigram in seen:
            continue
        seen.add(bigram)
        kws.append(bigram)
    return kws[:limit]


class Retriever(Protocol):
    """检索抽象：日后换 embedding 检索时实现 VectorRetriever 即可。"""

    async def top_chunks(
        self, db: AsyncSession, project_id: str, query: str, top_k: int | None = None
    ) -> list[RetrievedChunk]: ...


class KeywordRetriever:
    """按关键词命中数计分：命中 token 越多排越前，同分按段落序。"""

    def __init__(self, top_k: int = 5) -> None:
        self.top_k = top_k

    async def top_chunks(
        self, db: AsyncSession, project_id: str, query: str, top_k: int | None = None
    ) -> list[RetrievedChunk]:
        k = top_k or self.top_k
        keywords = extract_keywords(query)
        if not keywords:
            return []
        # chunk_id -> (chunk, doc_name, 命中 token 集合)
        by_id: dict[str, tuple[DocumentChunk, str, set[str]]] = {}
        for kw in keywords:
            stmt = (
                select(DocumentChunk, Document.name)
                .join(Document, Document.id == DocumentChunk.document_id)
                .where(
                    DocumentChunk.project_id == project_id,
                    DocumentChunk.content.contains(kw),
                )
                .limit(_MAX_ROWS_PER_KEYWORD)
            )
            rows = (await db.execute(stmt)).all()
            for chunk, doc_name in rows:
                entry = by_id.setdefault(chunk.id, (chunk, doc_name, set()))
                entry[2].add(kw)
        ranked = sorted(by_id.values(), key=lambda t: (-len(t[2]), t[0].seq))
        return [
            RetrievedChunk(
                document_id=chunk.id,
                document_name=name,
                seq=chunk.seq,
                content=chunk.content,
                matched=tuple(sorted(matched)),
            )
            for chunk, name, matched in ranked[:k]
        ]
