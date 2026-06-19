from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

async def embed(text: str):
    return model.encode(text).tolist()