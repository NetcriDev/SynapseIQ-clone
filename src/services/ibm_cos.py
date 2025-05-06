import os
from io import BytesIO
import ibm_boto3
from ibm_botocore.client import Config, ClientError
from threading import Lock
import pandas as pd

class IBMCOSManager:
    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        # Singleton pattern: ensures only one instance is created
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(IBMCOSManager, cls).__new__(cls)
        return cls._instance

    def __init__(self,
                 api_key=None,
                 service_crn=None,
                 endpoint=None,
                 verify_ssl=True):

        # Prevents re-initialization of the singleton instance
        if hasattr(self, "_initialized") and self._initialized:
            return

        self.api_key = api_key or os.environ.get("COS_API_KEY_ID")
        self.service_crn = service_crn or os.environ.get("COS_INSTANCE_CRN")
        self.endpoint = endpoint or os.environ.get("COS_ENDPOINT")
        self.verify_ssl = verify_ssl

        # Initializes the IBM COS (Cloud Object Storage) client
        self.cos_client = ibm_boto3.client(
            "s3",
            ibm_api_key_id=self.api_key,
            ibm_service_instance_id=self.service_crn,
            endpoint_url=self.endpoint,
            verify=self.verify_ssl,
            config=Config(signature_version="oauth")
        )

        self._initialized = True

    def _format_key(self, folder: str, year: str, filename: str) -> str:
        # Builds a structured key/path for storage based on folder/year/filename
        folder = folder.strip("/ ")
        year = year.strip("/ ")
        filename = filename.strip("/ ")
        return f"{folder}/{year}/{filename}" if folder else filename


    def object_exists(self, bucket: str, key: str) -> bool:
        """Checks if a given object (file) exists in the specified bucket."""
        try:
            self.cos_client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise


    def upload_file(self, file_path: str, bucket: str, filename: str, year: str = "", folder: str = "", overwrite: bool = True) -> bool:
        """Uploads a file from the local filesystem to IBM COS (Cloud Object Storage)."""
        key = self._format_key(folder, year, filename)
        if not overwrite and self.object_exists(bucket, key):
            print(f"[!] File {key} already exists in {bucket} (overwrite=False)")
            return False
        try:
            self.cos_client.upload_file(file_path, bucket, key)
            print(f"File uploaded: {bucket}/{key}")
            return True
        except ClientError as e:
            print(f"Error uploading file from disk: {e}")
            return False


    def upload_file_stream(self, stream: BytesIO, bucket: str, filename: str, year: str = "", folder: str = "", overwrite: bool = True) -> bool:
        """Uploads a file from an in-memory stream (BytesIO) to IBM COS."""
        key = self._format_key(folder, year, filename)
        if not overwrite and self.object_exists(bucket, key):
            print(f"File {key} already exists in {bucket} (overwrite=False)")
            return ""
        try:
            self.cos_client.upload_fileobj(stream, Bucket=bucket, Key=key)
            print(f"Stream file uploaded: {bucket}/{key}")
            return f"{bucket}/{key}"
        except ClientError as e:
            print(f"Error uploading file from memory: {e}")
            return ""


    def get_object_stream(self, bucket: str, key: str) -> BytesIO:
        """Retrieves an object from IBM COS as a BytesIO stream."""
        try:
            response = self.cos_client.get_object(Bucket=bucket, Key=key)
            return BytesIO(response["Body"].read())
        except ClientError as e:
            print(f"Error retrieving file: {e}")
            return None
        
        
    def download_file(self, bucket: str, key: str, destination_path: str) -> bool:
        """Download a file from COS to the local file system"""
        try:
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            self.cos_client.download_file(Bucket=bucket, Key=key, Filename=destination_path)
            print(f"Downloaded {bucket}/{key} -> {destination_path}")
            return True
        except ClientError as e:
            print(f"Error downloading file: {e}")
            return False

    def upload_dataframe_to_cos_csv(self, df: pd.DataFrame, bucket: str, 
                                    filename: str, year: str = "", folder: str = "", 
                                    overwrite: bool = True) -> bool:
        """
        Converts a DataFrame into CSV format and uploads it to IBM COS in memory.

        Parameters:
        - df: DataFrame to upload
        - bucket: Destination bucket name in IBM COS
        - filename: Name of the CSV file (e.g., 'report.csv')
        - folder: Logical folder path inside the bucket (e.g., 'reports/2025')
        - overwrite: Whether to overwrite the file if it already exists

        Returns:
        - The location where the file was uploaded if the upload was successful, "" otherwise
        """
        try:
            # Convert to CSV in memory
            buffer = BytesIO()
            df.to_csv(buffer, index=False)
            buffer.seek(0)

            # Subir con la clase IBM COS
            return self.upload_file_stream(
                stream=buffer,
                bucket=bucket,
                filename=filename,
                year=year,
                folder=folder,
                overwrite=overwrite
            )
        except Exception as e:
            print(f"Error loading DataFrame as CSV: {e}")
            return ""




    def delete_object(self, bucket: str, key: str) -> bool:
        """Deletes an object from the specified bucket."""
        try:
            self.cos_client.delete_object(Bucket=bucket, Key=key)
            print(f"Object deleted: {bucket}/{key}")
            return True
        except ClientError as e:
            print(f"Error deleting file: {e}")
            return False


    def list_objects(self, bucket: str, prefix: str = ""):
        """Lists objects stored in a specific folder (prefix) in the bucket."""
        try:
            response = self.cos_client.list_objects(Bucket=bucket, Prefix=prefix)
            return [obj["Key"] for obj in response.get("Contents", [])]
        except ClientError as e:
            print(f"Error listing objects: {e}")
            return []
