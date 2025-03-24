from .base import BaseConnector

class FTPConnector(BaseConnector):
    def fetch_files(self):
        # logic for connecting and downloading from FTP
        return [(b"<binary>", "report.xml")] # Example of return, Must return a list of tuples (file_content, file_name)
