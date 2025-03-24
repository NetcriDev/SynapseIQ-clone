from .base import BaseConnector

class WebServicesConnector(BaseConnector):
    def fetch_files(self):
        # logic for connecting and downloading from WebServicesConnector
        return [(b"<binary>", "report.pdf")] # Example of return, Must return a list of tuples (file_content, file_name)