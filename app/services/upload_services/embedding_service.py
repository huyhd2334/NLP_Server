import asyncio
# from sentence_transformers import SentenceTransformer

# model = SentenceTransformer("all-MiniLM-L6-v2")

# async def embed(text: str):

#     loop = asyncio.get_running_loop()
    
#     vector = await loop.run_in_executor(
#         None,                
#         model.encode,         
#         text                  
#     )
    
#     return vector.tolist()

from google import genai
import os

client = genai.Client(
    api_key=os.getenv("GOOGLE_API_KEY")
)

async def embed(text: str):
    response = client.models.embed_content(
        model="text-embedding-004",
        contents=text,
    )

    return response.embeddings[0].values