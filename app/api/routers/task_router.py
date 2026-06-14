from fastapi import APIRouter, Header
from app.controllers.task_controller import generate_task_controller
from app.schemas.task_schema import task_generate_request
import json
routers = APIRouter()

@routers.post("/generate-task")
async def generate_task_router(
    data: dict,
    authorization: str = Header(None),
    x_user_id: str = Header(None),
    x_user_name: str = Header(None) ):

    try:
        result = await generate_task_controller(data["description"])
        return result

    except Exception as e:
        print("ERROR:", e)
        raise e