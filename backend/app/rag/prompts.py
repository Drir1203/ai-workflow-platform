"""RAG 问答 prompt 构造：围栏上下文 + 只依片段作答指令。"""

from .retriever import RetrievedChunk


def build_qa_prompt(query: str, chunks: list[RetrievedChunk]) -> str:
    """把检索片段拼进围栏上下文，要求模型只依片段作答并标注引用。"""
    context_parts: list[str] = []
    for i, c in enumerate(chunks, start=1):
        ref = f"[{c.document_name} #{c.seq}]"
        context_parts.append(f"<片段{i} 来源={ref}>\n{c.content}\n</片段{i}>")
    context = "\n\n".join(context_parts)
    return (
        "你是项目知识库问答助手。请严格依据下面给定的知识库片段回答用户问题。\n"
        "要求：\n"
        "1. 只使用片段中的信息作答，不要编造片段之外的内容；\n"
        "2. 在回答中引用信息来源，格式如 [文档名 #段落号]；\n"
        "3. 如果片段中没有相关信息，请直接说明「知识库中未找到相关信息」，不要猜测。\n\n"
        f"知识库片段：\n{context}\n\n"
        f"用户问题：{query}\n\n"
        "回答："
    )
