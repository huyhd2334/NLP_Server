from app.services.upload_services.main_upload_service import main_upload_service

async def upload_controller(file_bytes: str, object_name: str, file_id: str):

    res = await main_upload_service(file_bytes, object_name, file_id)
    if res["success"] :
        print("save embedding vector", res["file_id"])
        print("chunk: ", res["chunks"])
        return {"success": res["success"]}
    else:
        return {"success": res["success"]}