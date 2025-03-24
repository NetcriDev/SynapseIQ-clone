def rename_file(original_filename: str, metadata: dict) -> str:
    prefix = f"{metadata['source']}_{metadata['timestamp'].replace(':','-')}"
    hash_segment = metadata.get("hash", "")[:8]
    extension = metadata['extension']
    return f"{prefix}_{hash_segment}{extension}"