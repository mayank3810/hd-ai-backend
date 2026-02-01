from pydantic import BaseModel

class DeleteFileSchema(BaseModel):
    file_url:str