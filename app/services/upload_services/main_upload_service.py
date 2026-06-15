from app.loaders.docx_loader import *
from app.loaders.pdf_loader import *
from app.loaders.txt_loader import *

from app.utils.file_type import detect_file_type
from app.services.upload_services.chunking_service import chunk_text
from app.services.upload_services.embedding_service import embed

from app.core.minio import minio_client
from qdrant_client.models import PointStruct
from app.core.qdrant import client

async def main_upload_service(bucker_name: str, object_name: str, file_id: str):

    try:
        response = minio_client.get_object(
           bucket_name = bucker_name,
           object_name = object_name
        )
        file_bytes  = response.read()
        
        response.close()
        response.release_conn()

    except Exception as e:
        raise ValueError(f"Cannot load file from MinIO: {e}")

    # check file type
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
        vector = embed(chunk)

        points.append(PointStruct(
            id=f"{file_id}_{i}",
            vector=vector,
            payload={
                "file_id": file_id,
                "chunk_id": i,
                "file_name": object_name,
                "text": chunk
            }
        ))

        client.upsert(
            collection_name = "documents-rag",
            points = points
        )
        
        count_vector += 1

    return { "file_id": file_id, "chunks": len(points) }
