import array

from app.services.llm_service import llm_responser
from app.services.upload_services.embedding_service import embed
from app.services.upload_services.chunking_service import chunk_text
from app.services.rag_services.vector_service import search
from app.services.rag_services.norm_service import norm_query

async def RAG_responses(query: str, documents: list[str], top_k: int):

    query_norm = norm_query(query)
    print("[DEBUG] query_norm done", query_norm)
    
    query_embedded = await embed(query_norm)
    print("[DEBUG] query_embedded done", query_embedded)

    chunks = await search(query_embed=query_embedded, file_ids=documents, top_k=top_k)
    print("[DEBUG] chunks done", chunks)

    llm_res = await llm_responser(query, chunks)
    print("[DEBUG] llm_res done", llm_res)

    return llm_res
    
