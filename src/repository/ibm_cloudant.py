from typing import Any, Optional, Dict
import uuid
from cloudant.client import Cloudant
from cloudant.error import CloudantException
from cloudant.document import Document

class IbmCloudantRepository:
    def __init__(self, username: str, api_key: str, database_name: str):
        """
        Initializes the connection to IBM Cloudant.
        
        Args:
            username: Username for the Cloudant instance
            api_key: API key for authentication
            database_name: Name of the database to use
        """
        self.client = Cloudant(username, api_key, connect=True)
        
        # Create the database if it doesn't exist
        if database_name not in self.client.all_dbs():
            self.db = self.client.create_database(database_name)
        else:
            self.db = self.client[database_name]
    
    def create(self, data: Dict[str, Any]) -> str:
        """
        Creates a new document in the database.
        
        Args:
            data: Dictionary with the data to save
            
        Returns:
            The ID of the created document
            
        Raises:
            ValueError: If there are issues with the data
        """
        file_hash = data.get("hash")
        
        if not file_hash:
            raise ValueError("Missing 'hash' in data.")
            
        # Check if a document with this hash already exists
        if self.exists(file_hash):
            raise ValueError(f"Record with hash '{file_hash}' already exists.")
        
        # Use the hash as the document ID
        document = self.db.create_document(data)
        document["_id"] = file_hash
        document.save()
        
        return document["_id"]
    
    def read(self, identifier: str) -> Optional[Dict[str, Any]]:
        """
        Reads a document by its identifier.
        
        Args:
            identifier: The document ID (hash)
            
        Returns:
            The complete document or None if it doesn't exist
        """
        try:
            if identifier in self.db:
                return dict(self.db[identifier])
            return None
        except CloudantException:
            return None
    
    def update(self, identifier: str, updates: Dict[str, Any]) -> None:
        """
        Updates an existing document.
        
        Args:
            identifier: The document ID (hash)
            updates: Dictionary with the fields to update
            
        Raises:
            KeyError: If the document doesn't exist
        """
        try:
            if identifier not in self.db:
                raise KeyError(f"Record with hash '{identifier}' not found.")
            
            document = self.db[identifier]
            for key, value in updates.items():
                if key != "_id" and key != "_rev":  # Don't modify special fields
                    document[key] = value
            
            document.save()
        except CloudantException as e:
            raise KeyError(f"Error updating document: {str(e)}")
    
    def delete(self, identifier: str) -> None:
        """
        Deletes a document.
        
        Args:
            identifier: The document ID (hash)
        """
        if identifier in self.db:
            document = self.db[identifier]
            document.delete()
    
    def exists(self, file_hash: str) -> bool:
        """
        Checks if a document with the specified hash exists.
        
        Args:
            file_hash: The hash to check
            
        Returns:
            True if it exists, False otherwise
        """
        return file_hash in self.db
    
    def save_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Saves metadata for a file.
        
        Args:
            metadata: Dictionary with the metadata
            
        Raises:
            ValueError: If the hash is missing in the metadata
        """
        file_hash = metadata.get("hash")
        
        if not file_hash:
            raise ValueError("Missing 'hash' in metadata.")
        
        try:
            if file_hash in self.db:
                # Update existing document
                document = self.db[file_hash]
                document.update(metadata)
                document.save()
            else:
                # Create new document
                self.db.create_document(metadata)
        except CloudantException as e:
            raise ValueError(f"Error saving metadata: {str(e)}")
    
    def save_json(self, structured_json: Dict[str, Any]) -> None:
        """
        Saves structured JSON data.
        
        Args:
            structured_json: Dictionary with the JSON data
            
        Raises:
            ValueError: If the hash is missing in the data
        """
        file_hash = structured_json.get("hash")
        
        if not file_hash:
            raise ValueError("Missing 'hash' in structured_json.")
        
        try:
            if file_hash in self.db:
                # Update existing document
                document = self.db[file_hash]
                document.update(structured_json)
                document.save()
            else:
                # Create new document
                self.db.create_document(structured_json)
        except CloudantException as e:
            raise ValueError(f"Error saving JSON: {str(e)}")
            
    def close(self) -> None:
        """Closes the connection to Cloudant"""
        if self.client:
            self.client.disconnect()