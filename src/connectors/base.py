from abc import ABC, abstractmethod
class BaseConnector(ABC):
    @abstractmethod
    def fetch_files(self) -> list[tuple[bytes, str]]:
        #"""Must return a list of tuples (file_content, file_name)"""
        pass