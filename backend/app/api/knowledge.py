"""知识库 RAG API：文档上传/列表/删除、本地目录扫描、知识问答（R8/R9/R10）。"""

import asyncio
import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..ai import get_ai_engine
from ..config import settings
from ..core.ratelimit import rate_limit
from ..db import get_db
from ..models.document import Document
from ..models.document_chunk import DocumentChunk
from ..models.project import Project
from ..models.user import User
from ..rag import KeywordRetriever, chunk_text, count_tokens, parse_document
from ..rag.prompts import build_qa_prompt
from ..schemas.document import (
    DocumentRead,
    KnowledgeQuery,
    KnowledgeResponse,
    KnowledgeSource,
    ScanResult,
)
from .deps import get_current_user

router = APIRouter(prefix="/api/projects/{project_id}", tags=["knowledge"])

_ALLOWED_TYPES = {"md", "txt", "pdf", "docx"}

# 限流依赖：按「来源 IP + scope」滑动窗口计数，超限抛 429。
# 端点的 `_rl: None = Depends(...)` 参数不传值，只负责把依赖挂进请求链路，见 core/ratelimit.py
_llm_limit = rate_limit(settings.ratelimit_llm_per_min, 60, scope="llm")
_upload_limit = rate_limit(settings.ratelimit_upload_per_min, 60, scope="upload")


async def _get_project_or_404(db: AsyncSession, project_id: str, user: User) -> Project:
    """取当前租户下的项目；不存在或归属他租户一律 404，不泄露存在性（IDOR 防护）。
    知识库所有接口都挂在项目下，必须先过这道租户门才能读写文档。"""
    project = await db.get(Project, project_id)
    if project is None or project.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="project not found")
    return project


def _content_type_from_name(name: str) -> str:
    """文件名后缀 → 支持的文档类型；markdown/mdown 归一为 md。"""
    ext = Path(name).suffix.lower().lstrip(".")
    if ext in ("markdown", "mdown"):
        return "md"
    return ext if ext in _ALLOWED_TYPES else ""


async def _ingest_text(
    db: AsyncSession,
    project: Project,
    name: str,
    content_type: str,
    text: str,
    source: str = "upload",
    source_path: str | None = None,
) -> Document:
    """切片入库（单事务）。解析已成功 → 直接建 ready 文档 + 全量 chunks。"""
    chunks = chunk_text(text, max_chars=settings.rag_chunk_chars)
    doc = Document(
        tenant_id=project.tenant_id,
        project_id=project.id,
        name=name,
        source=source,
        content_type=content_type,
        status="ready",
        source_path=source_path,
        doc_meta={"chunks": len(chunks)},
    )
    db.add(doc)
    await db.flush()
    for i, c in enumerate(chunks):
        db.add(
            DocumentChunk(
                tenant_id=project.tenant_id,
                project_id=project.id,
                document_id=doc.id,
                seq=i,
                content=c,
                token_count=count_tokens(c),
            )
        )
    await db.commit()
    await db.refresh(doc)
    return doc


@router.post("/documents", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    project_id: str,
    file: UploadFile = File(...),
    _rl: None = Depends(_upload_limit),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Document:
    project = await _get_project_or_404(db, project_id, user)
    data = await file.read()
    if len(data) > settings.rag_max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"文件超过 {settings.rag_max_upload_mb}MB 限制",
        )
    content_type = _content_type_from_name(file.filename or "")
    if content_type not in _ALLOWED_TYPES:
        raise HTTPException(status_code=422, detail="不支持的文档格式，仅支持 md/txt/pdf/docx")
    try:
        text = parse_document(content_type, data)
    except ValueError as exc:
        # 解析失败也留一条 error 记录，便于前端展示失败原因
        doc = Document(
            tenant_id=project.tenant_id,
            project_id=project.id,
            name=file.filename or "unnamed",
            source="upload",
            content_type=content_type,
            status="error",
            error=str(exc),
        )
        db.add(doc)
        await db.commit()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _ingest_text(db, project, file.filename or "unnamed", content_type, text)


@router.get("/documents", response_model=list[DocumentRead])
async def list_documents(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Document]:
    await _get_project_or_404(db, project_id, user)
    result = await db.execute(
        select(Document)
        .where(Document.project_id == project_id)
        .order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/documents/scan", response_model=ScanResult)
async def scan_documents(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ScanResult:
    """扫描 project.local_path 下的 md/txt 递归导入（R10）。文件 IO 在线程池执行。"""
    project = await _get_project_or_404(db, project_id, user)
    root = project.local_path
    if not root:
        raise HTTPException(status_code=400, detail="项目未配置 local_path，无法扫描")
    if not os.path.isdir(root):
        raise HTTPException(status_code=400, detail=f"local_path 不存在: {root}")

    ext_set = {f".{e.lstrip('.')}" for e in settings.rag_scan_extensions}
    docs, skipped = await _collect_scan_docs(root, ext_set)

    result = await db.execute(
        select(Document.source_path).where(
            Document.project_id == project_id, Document.source == "scan"
        )
    )
    existing = {row[0] for row in result.all() if row[0]}

    imported = 0
    for rel, content_type, text in docs:
        if rel in existing:
            skipped.append(rel)
            continue
        await _ingest_text(db, project, rel, content_type, text, source="scan", source_path=rel)
        imported += 1
    return ScanResult(imported=imported, skipped=skipped)


async def _collect_scan_docs(root: str, ext_set: set[str]) -> tuple[list[tuple[str, str, str]], list[str]]:
    """在线程池里枚举并解析扫描目录，返回 (导入文档, 跳过文件)。"""

    def _walk_and_parse():
        docs: list[tuple[str, str, str]] = []
        skipped: list[str] = []
        for dirpath, _dirnames, filenames in os.walk(root):
            for fname in sorted(filenames):
                if Path(fname).suffix.lower() not in ext_set:
                    continue
                full = os.path.join(dirpath, fname)
                rel = os.path.relpath(full, root)
                content_type = _content_type_from_name(fname)
                if content_type not in _ALLOWED_TYPES:
                    skipped.append(rel)
                    continue
                try:
                    text = parse_document(content_type, Path(full).read_bytes())
                except Exception:  # noqa: BLE001 - 单文件失败不阻断整个扫描
                    skipped.append(rel)
                    continue
                docs.append((rel, content_type, text))
        return docs, skipped

    return await asyncio.to_thread(_walk_and_parse)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    project_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    await _get_project_or_404(db, project_id, user)
    doc = await db.get(Document, document_id)
    # 文档归属必须同时匹配租户与项目，防跨租户删除
    if doc is None or doc.project_id != project_id or doc.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="document not found")
    # SQLite 默认不强制外键，显式删 chunks 保证级联一致
    await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
    await db.delete(doc)
    await db.commit()


@router.post("/knowledge", response_model=KnowledgeResponse)
async def query_knowledge(
    project_id: str,
    payload: KnowledgeQuery,
    _rl: None = Depends(_llm_limit),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> KnowledgeResponse:
    """项目知识问答：关键词检索 top-k → 围栏 prompt → engine.chat（R9）。"""
    await _get_project_or_404(db, project_id, user)
    retriever = KeywordRetriever(top_k=settings.rag_top_k)
    chunks = await retriever.top_chunks(db, project_id, payload.query, top_k=settings.rag_top_k)
    if not chunks:
        # 空检索短路：不调 LLM，省 token
        return KnowledgeResponse(answer="知识库中未找到相关信息。", sources=[])

    engine = get_ai_engine()
    answer = await engine.chat(build_qa_prompt(payload.query, chunks), user=user.email)
    sources = [
        KnowledgeSource(
            document_id=c.document_id,
            document_name=c.document_name,
            seq=c.seq,
            content=c.content[:300],
            matched=list(c.matched),
        )
        for c in chunks
    ]
    return KnowledgeResponse(answer=answer, sources=sources)
