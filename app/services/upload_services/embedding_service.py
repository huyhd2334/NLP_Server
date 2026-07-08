import asyncio
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

async def embed(text: str):

    loop = asyncio.get_running_loop()
    
    vector = await loop.run_in_executor(
        None,                
        model.encode,         
        text                  
    )
    
    return vector.tolist()