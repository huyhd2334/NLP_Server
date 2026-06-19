from app.services.rag_services.rag_service import RAG_responses

async def RAG_responses_controller(query: str, documents: list[str]):
    res = await RAG_responses(query, documents, top_k=3)
    
    if res["success"] :
        print(res)
        return res
    else:
        return {"success": res["success"]}
