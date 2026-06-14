from fastapi import FastAPI
from app.api.routers.task_router import routers
from app.services.upload_services.vector_service import init_qdrant

app = FastAPI()

app.include_router(routers)

@app.on_event("startup")
async def startup_event():
    init_qdrant()

@app.get("/")
def root():
    return {"message": "AI Task System Running"}

