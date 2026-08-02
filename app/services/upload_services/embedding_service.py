import asyncio
from sentence_transformers import SentenceTransformer
# all-MiniLM-L6-v2
model = SentenceTransformer("BAAI/bge-base-en-v1.5")

async def embed(text: str, is_query: bool = False):

    if is_query:
        text = "Represent this sentence for searching relevant passages: " + text
        
    loop = asyncio.get_running_loop()
    
    vector = await loop.run_in_executor(
        None,                
        model.encode,         
        text                  
    )
    
    return vector.tolist()