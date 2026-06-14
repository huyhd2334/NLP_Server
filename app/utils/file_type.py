def detect_file_type(filename: str):
    if filename.endswith(".docx"):
        return "docx"
    if filename.endswith(".pdf"):
        return "pdf"
    if filename.endswith(".txt"):
        return "txt"
    else:
        return "Unsupported file type"