"""ID generation helpers."""

from hashlib import sha1


def build_doc_id(file_name: str, file_hash: str) -> str:
    digest = sha1(f"{file_name}:{file_hash}".encode("utf-8")).hexdigest()[:12]
    return f"doc_{digest}"


def build_block_id(page_no: int, block_index: int) -> str:
    return f"b_{page_no}_{block_index}"


def build_chunk_id(doc_id: str, page_no: int, chunk_index: int) -> str:
    return f"{doc_id}_p{page_no}_c{chunk_index}"

