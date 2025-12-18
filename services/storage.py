import os
import boto3
import shutil
from fastapi import UploadFile
from ..core.logger import get_logger

logger = get_logger(__name__)

class StorageService:
    def __init__(self):
        self.aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.s3_bucket = os.getenv("S3_BUCKET_NAME")
        
        self.s3_client = None
        if self.aws_access_key and self.aws_secret_key and self.s3_bucket:
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_key,
                    region_name=self.aws_region
                )
                logger.info("S3 Client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {e}")
        else:
            logger.warning("AWS credentials or S3 bucket not configured. Falling back to local storage.")

    def upload_file(self, file: UploadFile, destination_path: str) -> str:
        """
        Uploads a file to S3 or saves locally.
        Returns the file path or S3 URL.
        """
        if self.s3_client:
            try:
                # Reset file pointer
                file.file.seek(0)
                
                # Upload to S3
                self.s3_client.upload_fileobj(
                    file.file,
                    self.s3_bucket,
                    destination_path,
                    ExtraArgs={'ContentType': file.content_type}
                )
                
                url = f"https://{self.s3_bucket}.s3.{self.aws_region}.amazonaws.com/{destination_path}"
                logger.info(f"File uploaded to S3: {url}")
                return url
            except Exception as e:
                logger.error(f"S3 upload failed: {e}. Falling back to local storage.")
                # Fallback to local
        
        # Local Storage
        upload_dir = "backend/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Ensure destination_path is just the filename for local storage to avoid directory traversal issues
        filename = os.path.basename(destination_path)
        local_path = f"{upload_dir}/{filename}"
        
        try:
            file.file.seek(0)
            with open(local_path, "wb+") as file_object:
                shutil.copyfileobj(file.file, file_object)
            
            logger.info(f"File saved locally: {local_path}")
            return local_path
        except Exception as e:
            logger.error(f"Local file save failed: {e}")
            raise e

storage_service = StorageService()
