from .base import BaseConnector

class EmailConnector(BaseConnector):
    def fetch_files(self):
        # Example of return
        return [(b"%PDF_binary_content", "report.pdf")]
