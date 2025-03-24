from abc import ABC, abstractmethod
from typing import Any

class BaseParser(ABC):
    @abstractmethod
    def parser(self, file_bytes: bytes, filename: str) -> dict[str, Any]:
        """Processes the file and returns a structured JSON."""
        pass
