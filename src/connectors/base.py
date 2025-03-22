from abc import ABC, abstractmethod

# Abstract interface for all connectors
class Connector(ABC):
    @abstractmethod
    def connect(self):
        pass
    
    @abstractmethod
    def read_data(self, source):
        pass
    
    @abstractmethod
    def parse_data(self, data):
        pass