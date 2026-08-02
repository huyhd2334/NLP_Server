from app.loaders.docx_loader import *
from app.loaders.pdf_loader import *
from app.loaders.txt_loader import *

from app.utils.file_type import detect_file_type
from app.services.upload_services.chunking_service import chunk_text
from app.services.upload_services.embedding_service import embed

from qdrant_client.models import PointStruct
from app.core.qdrant import client

import uuid

import os 
async def main_upload_service(file_path: str, file_id: str, is_query: bool = False):

    try:
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
  
    except Exception as e:
        raise ValueError(f"Cannot load file from Local: {e}")

    # check file type
    object_name = os.path.basename(file_path)
    file_type = detect_file_type(object_name)
    
    # load text
    if file_type == "docx":
        text = load_docx(file_bytes)
    elif file_type == "pdf":
        text = load_pdf(file_bytes)
    elif file_type == "txt":
        text = load_txt(file_bytes)
    else:
        raise ValueError("Unsupport file type")
    
    # chunk
    chunks = chunk_text(text)

    # embed save
    points = []
    for i, chunk in enumerate(chunks):
        vector = await embed(chunk, is_query)

        seed_string = f"{file_id}_{i}"
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, seed_string))

        points.append(PointStruct(
            id=point_id,
            vector=vector,
            payload={
                "file_id": file_id,
                "chunk_id": i,
                "file_name": object_name,
                "text": chunk
            }
        ))

    client.upsert(
        collection_name = "documents-rag-BAAI",
        points = points
    )
    return { "success": True, "file_id": file_id, "chunks": len(points) }
