from abc import ABC, abstractmethod
from typing import Any, Optional

class BaseRepository(ABC):
    @abstractmethod
    def create(self, data: dict[str, Any]) -> None:
        """Creates a new record in the database."""
        pass

    @abstractmethod
    def read(self, identifier: str) -> Optional[dict[str, Any]]:
        """Reads and returns a record given its unique identifier."""
        pass

    @abstractmethod
    def update(self, identifier: str, updates: dict[str, Any]) -> None:
        """Updates an existing record."""
        pass

    @abstractmethod
    def delete(self, identifier: str) -> None:
        """Deletes a record given its identifier."""
        pass

    @abstractmethod
    def exists(self, file_hash: str) -> bool:
        """Returns True if the file has already been hashed."""
        pass

    @abstractmethod
    def save_metadata(self, metadata: dict[str, Any]) -> None:
        """Stores metadata associated with a file."""
        pass

    @abstractmethod
    def save_json(self, structured_json: dict[str, Any]) -> None:
        """Saves the processed structured JSON from the file."""
        pass
