from typing import Any, Optional, Dict, BinaryIO, List
import os
import json
from io import BytesIO
import ibm_boto3
from ibm_boto3.s3.transfer import TransferConfig
from ibm_botocore.client import Config
from ibm_botocore.exceptions import ClientError

class IbmObjectStoreRepository:
    def __init__(self, api_key: str, service_instance_id: str, auth_endpoint: str, endpoint: str, bucket_name: str):
        """
        Initializes the connection to IBM Cloud Object Storage.
        
        Args:
            api_key: IBM Cloud API Key
            service_instance_id: Resource Instance ID for the Object Storage instance
            auth_endpoint: Authentication endpoint (e.g. 'https://iam.cloud.ibm.com/xyz/token')
            endpoint: Service endpoint URL
            bucket_name: Name of the bucket to use
        """
        self.bucket_name = bucket_name
        
        # Create resource using IBM COS SDK
        self.cos = ibm_boto3.resource('s3',
            ibm_api_key_id=api_key,
            ibm_service_instance_id=service_instance_id,
            ibm_auth_endpoint=auth_endpoint,
            config=Config(signature_version='oauth'),
            endpoint_url=endpoint
        )
        
        # Create client for some operations
        self.cos_client = ibm_boto3.client('s3',
            ibm_api_key_id=api_key,
            ibm_service_instance_id=service_instance_id,
            ibm_auth_endpoint=auth_endpoint,
            config=Config(signature_version='oauth'),
            endpoint_url=endpoint
        )
        
        # Create bucket if it doesn't exist
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self) -> None:
        """
        Ensures the specified bucket exists, creating it if necessary.
        """
        try:
            self.cos.meta.client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            # If a 404 error is returned, the bucket doesn't exist
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                self.cos.create_bucket(Bucket=self.bucket_name)
            else:
                raise
    
    def upload_file(self, file_path: str, object_key: str, metadata: Dict[str, str] = None) -> bool:
        """
        Uploads a file to the object storage.
        
        Args:
            file_path: Path to the local file
            object_key: Key (name) to use in the object storage
            metadata: Optional metadata to store with the object
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File {file_path} not found")
            
        try:
            # Configure the transfer to use multiple threads for large files
            transfer_config = TransferConfig(multipart_threshold=1024 * 1024 * 5,  # 5MB
                                           multipart_chunksize=1024 * 1024 * 5)
            
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata
            
            # Upload the file
            self.cos.Object(self.bucket_name, object_key).upload_file(
                Filename=file_path,
                ExtraArgs=extra_args,
                Config=transfer_config
            )
            return True
        except ClientError as e:
            print(f"Error uploading file: {str(e)}")
            return False
    
    def upload_data(self, data: bytes, object_key: str, metadata: Dict[str, str] = None) -> bool:
        """
        Uploads data to the object storage.
        
        Args:
            data: Bytes to upload
            object_key: Key (name) to use in the object storage
            metadata: Optional metadata to store with the object
            
        Returns:
            True if successful, False otherwise
        """
        try:
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata
                
            # Upload the data
            self.cos.Object(self.bucket_name, object_key).put(
                Body=data,
                **extra_args
            )
            return True
        except ClientError as e:
            print(f"Error uploading data: {str(e)}")
            return False
    
    def download_file(self, object_key: str, destination_path: str) -> bool:
        """
        Downloads a file from the object storage.
        
        Args:
            object_key: Key of the object to download
            destination_path: Path where the file should be saved
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.cos.Object(self.bucket_name, object_key).download_file(destination_path)
            return True
        except ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                print(f"Object {object_key} not found")
            else:
                print(f"Error downloading file: {str(e)}")
            return False
    
    def download_data(self, object_key: str) -> Optional[bytes]:
        """
        Downloads data from the object storage.
        
        Args:
            object_key: Key of the object to download
            
        Returns:
            The data as bytes or None if the object doesn't exist
        """
        try:
            response = self.cos.Object(self.bucket_name, object_key).get()
            return response['Body'].read()
        except ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                print(f"Object {object_key} not found")
            else:
                print(f"Error downloading data: {str(e)}")
            return None
    
    def list_objects(self, prefix: str = "") -> List[Dict[str, Any]]:
        """
        Lists objects in the bucket with an optional prefix.
        
        Args:
            prefix: Optional prefix to filter objects
            
        Returns:
            List of object information dictionaries
        """
        try:
            objects = []
            if prefix:
                response = self.cos_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            else:
                response = self.cos_client.list_objects_v2(Bucket=self.bucket_name)
                
            if 'Contents' in response:
                for obj in response['Contents']:
                    objects.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'],
                        'etag': obj['ETag']
                    })
            return objects
        except ClientError as e:
            print(f"Error listing objects: {str(e)}")
            return []
    
    def delete_object(self, object_key: str) -> bool:
        """
        Deletes an object from the storage.
        
        Args:
            object_key: Key of the object to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.cos.Object(self.bucket_name, object_key).delete()
            return True
        except ClientError as e:
            print(f"Error deleting object: {str(e)}")
            return False
    
    def object_exists(self, object_key: str) -> bool:
        """
        Checks if an object exists in the storage.
        
        Args:
            object_key: Key of the object to check
            
        Returns:
            True if the object exists, False otherwise
        """
        try:
            self.cos.Object(self.bucket_name, object_key).load()
            return True
        except ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                return False
            else:
                print(f"Error checking if object exists: {str(e)}")
                return False
    
    def get_object_metadata(self, object_key: str) -> Optional[Dict[str, Any]]:
        """
        Gets metadata for an object.
        
        Args:
            object_key: Key of the object
            
        Returns:
            Dictionary with metadata or None if the object doesn't exist
        """
        try:
            obj = self.cos.Object(self.bucket_name, object_key)
            response = obj.get()
            metadata = {
                'content_length': response['ContentLength'],
                'content_type': response['ContentType'],
                'last_modified': response['LastModified'],
                'etag': response['ETag']
            }
            if 'Metadata' in response:
                metadata['user_metadata'] = response['Metadata']
            return metadata
        except ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                print(f"Object {object_key} not found")
            else:
                print(f"Error getting object metadata: {str(e)}")
            return None
    
    def save_json(self, data: Dict[str, Any], object_key: str) -> bool:
        """
        Saves JSON data to the object storage.
        
        Args:
            data: Dictionary to save as JSON
            object_key: Key to use for the object
            
        Returns:
            True if successful, False otherwise
        """
        try:
            json_data = json.dumps(data).encode('utf-8')
            return self.upload_data(
                data=json_data,
                object_key=object_key,
                metadata={'ContentType': 'application/json'}
            )
        except Exception as e:
            print(f"Error saving JSON: {str(e)}")
            return False
    
    def load_json(self, object_key: str) -> Optional[Dict[str, Any]]:
        """
        Loads JSON data from the object storage.
        
        Args:
            object_key: Key of the JSON object
            
        Returns:
            Parsed JSON data or None if the object doesn't exist
        """
        try:
            data = self.download_data(object_key)
            if data:
                return json.loads(data.decode('utf-8'))
            return None
        except Exception as e:
            print(f"Error loading JSON: {str(e)}")
            return None
    
    def generate_presigned_url(self, object_key: str, expires_in: int = 3600, method: str = 'get') -> Optional[str]:
        """
        Generates a presigned URL for an object.
        
        Args:
            object_key: Key of the object
            expires_in: Expiration time in seconds (default 1 hour)
            method: HTTP method ('get', 'put', etc.)
            
        Returns:
            Presigned URL or None if an error occurred
        """
        try:
            url = self.cos_client.generate_presigned_url(
                ClientMethod=f'{method}_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key
                },
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            print(f"Error generating presigned URL: {str(e)}")
            return None