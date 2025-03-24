from .base import BaseConnector

class IbmConnector(BaseConnector):
    def fetch_files(self):
        # logic for connecting and downloading from IBM local Storage
        return [(b"<binary>", "report.pdf")] # Example of return, Must return a list of tuples (file_content, file_name)