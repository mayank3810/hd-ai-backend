import os
import shutil
from fastapi import APIRouter, Form, HTTPException, UploadFile, File, Depends,Header
from fastapi.responses import JSONResponse
from app.middleware.JWTVerification import jwt_validator
from app.schemas.ServerResponse import ServerResponse
from app.helpers.Utilities import Utils
from app.schemas.Common import DeleteFileSchema
from app.dependencies import get_common_service

router = APIRouter(prefix="/api/v1/common", tags=["common"])
    
@router.post("/upload-file",response_model=ServerResponse)
async def upload_file(
    file: UploadFile=File(None), 
    service = Depends(get_common_service),
    jwt_payload: dict = Depends(jwt_validator)
  
):
    try:
        file_path = Utils.generate_hex_string() + file.filename
        file_path = file_path.replace(" ", "_")

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        data = await service.upload_file(file_path)
        
        os.remove(file_path)
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail={"data": None, "error":str(e),"success": False})
    
@router.delete("/delete-file", response_model=ServerResponse)
async def delete_file(
    body: DeleteFileSchema,
    service = Depends(get_common_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        # Delegate file deletion to the service layer
        data = await service.delete_file(body.file_url)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    

        


    
    