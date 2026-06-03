from fastapi import APIRouter
from app.controllers.task_controller import generate_task_controller
from app.schemas.task_schema import task_generate_request

routers = APIRouter()

@routers.post("/generate-task")

async def generate_task_router(req: task_generate_request):
    result = await generate_task_controller(req.description)
    
    return {
        "tasks": result
    }

# @routers.post("/generate-task-2")

# def generate_task_router(req):
#     return generate_task_controller(req)