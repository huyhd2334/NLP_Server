from fastapi import APIRouter
from app.controllers.upload_controller import *
from app.schemas.upload_schema import UploadRequest

router_upload_file = APIRouter()

@router_upload_file.post("/upload")

async def uploadRouter(req: UploadRequest):
    try:
        result = await upload_controller(
            bucket_name=req.bucket_name,
            object_name=req.object_name,
            file_id=req.file_id
        )        
        return result
    except Exception as e:
        print("[Error]: ", e)
        raise e
        