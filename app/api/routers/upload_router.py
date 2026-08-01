from fastapi import APIRouter
from app.controllers.upload_controller import *
# from app.schemas.upload_schema import UploadRequest
from fastapi import UploadFile, File, Form

router_upload_file = APIRouter()

@router_upload_file.post("/upload")

async def uploadRouter(file: UploadFile=File(...),
                       file_id: str=Form(...)):
    try:
        print("[DEBUG] Uploading....")
        file_bytes = await file.read()

        result = await upload_controller(
            file_bytes=file_bytes,
            object_name=file.filename,
            file_id=file_id
        )        

        return result
    
    except Exception as e:
        print("[Error]: ", e)
        raise e
        