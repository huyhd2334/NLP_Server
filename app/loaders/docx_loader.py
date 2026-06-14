import docx
import io

def load_docx(file_bytes: bytes) -> str:
    doc = docx.Document(io.BytesIO(file_bytes))

    text = []
    for para in doc.paragraphs:
        text.append(para.text)

    return "\n".join(text)