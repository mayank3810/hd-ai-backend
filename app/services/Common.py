from app.helpers.AzureStorage import AzureBlobUploader
import os


class CommonService:
    def __init__(self):
        self.azure_uploader = AzureBlobUploader()
        
    async def upload_file(self,file_path,folder_name="strategy-cues-storage",file_type=".png"):
        try:
            
            file_url=self.azure_uploader.upload_file_to_azure_blob(file_path,folder_name,file_type)       
            return {
                    "success": True,
                    "data": file_url
                }
        except Exception as e:
            return {
                "success": False,
                "data": str(e),
                "error":'Unable to upload file'
            }
    
    async def delete_file(self,file_url: str) -> dict:
        try:

            # Call helper to delete the file from Azure Blob
            self.azure_uploader.delete_file(file_url)

            return {
                "success": True,
                "data": f"file  deleted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to delete file: {str(e)}"
            }
