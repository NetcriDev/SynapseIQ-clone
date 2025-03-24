from connectors.base import BaseConnector
from processors.factory import get_processor
from metadata.extractor import extract_metadata
from metadata.hashing import calculate_hash
from metadata.renamer import rename_file
from repository.cloudant_repository import CloudantRepository
from repository.milvus_repository import MilvusRepository

class IngestionPipeline:
    def __init__(self, connector: BaseConnector):
        self.connector = connector
        self.repo_cloudant = CloudantRepository()
        self.repo_vector = MilvusRepository()  # opcional

    def run(self):
        files = self.connector.fetch_files()
        for file_bytes, filename in files:
            metadata = extract_metadata(file_bytes, filename, source=self.connector.__class__.__name__)
            metadata["hash"] = calculate_hash(file_bytes)
            
            if self.repo_cloudant.exists(metadata["hash"]):
                print(f"[SKIP] Archivo ya procesado: {filename}")
                continue

            metadata["renamed"] = rename_file(filename, metadata)
            processor = get_processor(metadata["extension"])
            structured_json = processor.process(file_bytes, filename)
            structured_json["hash"] = metadata["hash"]

            # Almacenar
            self.repo_cloudant.save_metadata(metadata)
            self.repo_cloudant.save_json(structured_json)

            # Opcional: almacenar en sistema de búsqueda vectorial
            self.repo_vector.save_json(structured_json)

            print(f"[OK] Procesado y almacenado: {metadata['renamed']}")
