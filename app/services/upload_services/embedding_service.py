import asyncio
import os
from google import genai

client = genai.Client(
    api_key=os.getenv("GOOGLE_API_KEY")
)

async def embed(text: str):
    loop = asyncio.get_running_loop()

    response = await loop.run_in_executor(
        None,
        lambda: client.models.embed_content(
            model="gemini-embedding-2",
            contents=text,
        )
    )

    return response.embeddings[0].values