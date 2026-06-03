from pydantic import BaseModel

class task_generate_request(BaseModel):
    description : str