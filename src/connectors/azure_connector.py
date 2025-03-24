from .base import BaseConnector

class AzureConnector(BaseConnector):
    def fetch_files(self):
        # logic for connecting and downloading from Azure Storage Blob
        return [(b"<binary>", "report.pdf")] # Example of return, Must return a list of tuples (file_content, file_name)
