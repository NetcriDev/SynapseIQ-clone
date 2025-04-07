from abc import ABC, abstractmethod
from typing import Any
import os

class BaseParser(ABC):
    @abstractmethod
    def parser(self, file_bytes: bytes, filename: str) -> dict[str, Any]:
        """Processes the file and returns a structured JSON."""
        pass

#print(__file__)
#print(os.path.dirname(__file__))