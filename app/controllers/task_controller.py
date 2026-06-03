from app.services.task_service import task_generate_service

async def generate_task_controller(req):
    return await task_generate_service(req)