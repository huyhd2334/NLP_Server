from fastapi import FastAPI
from app.api.routers.task_router import routers

app = FastAPI()

app.include_router(routers)

@app.get("/")
def root():
    return {"message": "AI Task System Running"}