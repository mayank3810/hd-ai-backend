import os
from azure.storage.blob import BlobServiceClient
from app.helpers.Utilities import Utils
import urllib.parse
import time
import re
import mimetypes
import urllib
from azure.storage.blob import ContentSettings


class AzureBlobUploader:
    def __init__(self):
        try:
            self.__connection_string = os.environ['AZURE_STORAGE_CONNECTION_STRING']
            self.__container_name = os.environ['AZURE_STORAGE_CONTAINER']
        except KeyError:
            raise Exception("AZURE_STORAGE_CONNECTION_STRING and AZURE_STORAGE_CONTAINER must be set.")

        self.__blob_service_client = BlobServiceClient.from_connection_string(self.__connection_string)
        self.__container_client = self.__blob_service_client.get_container_client(self.__container_name)
        self.__generate_random_hex_string = Utils.generate_hex_string
        
    def delete_file(self, file_url: str):
        """Delete file from Azure Blob Storage using full file URL."""
        parsed_url = urllib.parse.urlparse(file_url)
        blob_name = parsed_url.path.lstrip(f"/{self.__container_name}/")  
        blob_client = self.__blob_service_client.get_blob_client(container=self.__container_name, blob=blob_name)
        blob_client.delete_blob()

    def copy_and_upload_to_azure_blob(self, image_url, container_name='temp', folder_name=None, file_type=".png"):
        container_client = self.__blob_service_client.get_container_client(container_name)

        destination_blob_name = self.__generate_random_hex_string() + file_type
        if folder_name:
            destination_blob_name = f"{folder_name}/{destination_blob_name}"

        copied_blob = self.__blob_service_client.get_blob_client(container_name, destination_blob_name)

        copied_blob.start_copy_from_url(image_url)

        for _ in range(60):
            props = copied_blob.get_blob_properties()
            status = props.copy.status
            if status == "success":
                copied_blob_url = f"https://{self.__blob_service_client.account_name}.blob.core.windows.net/{container_name}/{destination_blob_name}"
                return copied_blob_url
            time.sleep(1)

        props = copied_blob.get_blob_properties()
        copy_id = props.copy.id
        copied_blob.abort_copy(copy_id)
        return None

    def upload_file_to_azure_blob(self, file_path, folder_name=None, file_type=".png"):
        container_name=self.__container_name
        container_client = self.__blob_service_client.get_container_client(container_name)

        file_extension = os.path.splitext(file_path)[1]

        random_filename = self.__generate_random_hex_string()
        sanitized_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', random_filename + file_extension)

        if folder_name:
            folder_name = re.sub(r'[^a-zA-Z0-9/_-]', '_', folder_name)
            destination_blob_name = f"{folder_name}/{sanitized_filename}"
        else:
            destination_blob_name = sanitized_filename
            
        destination_blob_name = urllib.parse.quote(destination_blob_name, safe="/")

        blob_client = self.__blob_service_client.get_blob_client(container_name, destination_blob_name)

        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            mime_type = 'application/octet-stream'  # Fallback

        content_settings = ContentSettings(content_type=mime_type)

        try:
            with open(file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True, content_settings=content_settings)
            uploaded_blob_url = f"https://{self.__blob_service_client.account_name}.blob.core.windows.net/{container_name}/{destination_blob_name}"
            return uploaded_blob_url
        except Exception as e:
            print(f"Failed to upload {file_path} to Azure Blob Storage. Error: {str(e)}")
            return None
        
    def upload_file_to_azure_blob_v2(self, file_path, container_name='documents', folder_name=None, file_type=".png"):
        container_name=self.__container_name
        container_client = self.__blob_service_client.get_container_client(container_name)

        file_extension = os.path.splitext(file_path)[1]

        random_filename = self.__generate_random_hex_string()
        sanitized_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', random_filename + file_extension)

        if folder_name:
            folder_name = re.sub(r'[^a-zA-Z0-9/_-]', '_', folder_name)
            destination_blob_name = f"{folder_name}/{sanitized_filename}"
        else:
            destination_blob_name = sanitized_filename
            
        destination_blob_name = urllib.parse.quote(destination_blob_name, safe="/")

        blob_client = self.__blob_service_client.get_blob_client(container_name, destination_blob_name)

        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            mime_type = 'application/octet-stream'  # Fallback

        content_settings = ContentSettings(content_type=mime_type)

        try:
            with open(file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True, content_settings=content_settings)
            uploaded_blob_url = f"https://{self.__blob_service_client.account_name}.blob.core.windows.net/{container_name}/{destination_blob_name}"
            return uploaded_blob_url
        except Exception as e:
            print(f"Failed to upload {file_path} to Azure Blob Storage. Error: {str(e)}")
            return None
