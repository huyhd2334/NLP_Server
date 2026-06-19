from fastapi import FastAPI
from app.api.routers.task_router import routers
from app.api.routers.upload_router import router_upload_file
from app.api.routers.rag_route import router_rag

from app.services.rag_services.vector_service import init_qdrant

app = FastAPI()

app.include_router(routers)
app.include_router(router_upload_file)
app.include_router(router_rag)

@app.on_event("startup")
async def startup_event():
    init_qdrant()

@app.get("/")
def root():
    return {"message": "AI Task System Running"}

