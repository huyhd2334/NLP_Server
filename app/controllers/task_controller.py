from app.services.task_service import task_generate_service

async def generate_task_controller(req):
    res = await task_generate_service(req)
    
    if res["success"] :
        return {"success": res["success"], "tasks": res["tasks"]}
    else:
        return {"success": res["success"]}
