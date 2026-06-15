from pydantic import BaseModel

class UploadRequest(BaseModel):
    bucket_name: str
    object_name: str
    file_id: str