from fastapi import APIRouter
from app.controllers.upload_controller import *

routers = APIRouter()

@routers.post("/upload")

async def uploadRouter(req):
    try:
        result = await upload_controller(req)
        return result
    except Exception as e:
        print("[Error]: ", e)
        raise e
        