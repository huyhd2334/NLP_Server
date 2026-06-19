from fastapi import APIRouter
from app.controllers.rag_controller import RAG_responses_controller
from app.schemas.rag_schema import RAGRequest
router_rag = APIRouter()

@router_rag.post("/rag-chat")

async def ragRouter(req: RAGRequest):
    try:
        print("[DEBUG] calling RAG_responses_controller")
        results = await RAG_responses_controller(query=req.query, documents=req.documents)
        return results

    except Exception as e:
        print("[Error]: ", e)
        raise e
