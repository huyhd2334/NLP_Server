from app.services.upload_services import main_upload_service

async def upload_controller(req):
    res = await main_upload_service(req)
    if res["success"] :
        return {"success": res["success"]}
    else:
        return {"success": res["success"]}