from app.loaders.docx_loader import *
from app.loaders.pdf_loader import *
from app.loaders.txt_loader import *

from app.utils.file_type import detect_file_type
from app.services.upload_services.chunking_service import chunk_text
from app.services.upload_services.embedding_service import embed

async def main_upload_service(file_bytes: bytes, file_name: str, file_id: str):
    
    # check file type
    file_type = detect_file_type(file_name)
    
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
    chunk_text = chunk_text(text)

    # embed save
    results = []

    for i, chunk in enumerate(chunk_text):
        vector = embed(chunk)

        item = {
            "id": f"{file_id}-{i}",
            "text": chunk,
            "vector": vector,
            "file_id": file_id,
            "filename": file_name
        }

        await save_vector(item)
        results.append(item)


    return { "file_id": file_id, "chunks": len(results) }
