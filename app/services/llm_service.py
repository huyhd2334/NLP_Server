import redis
from openai import OpenAI
import os
import json 
import hashlib

llm_client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)

async def llm_responser(query: str, chunks):
    
    if not chunks:
        return {
            "success": False,
            "message": "No relevant documents found"
        }
    context = "\n".join(chunk["text"] for chunk in chunks)

    cache_key = "rag:" + hashlib.md5(f'{query} + {context}'.encode()).hexdigest()
    cached = redis_client.get(cache_key)
    if cached:
        print("\n[DEBUG] CACHE HIT")
        return {
            "success": True,
            "response": json.loads(cached)
        }    

    print("\n[DEBUG] CACHE MISS")


    prompt = f"""
        You are a professional RAG assistant.

        Question:
        {query}

        Context:
        {context}

        Instructions:
        - Answer length must not too short and not too long
        - Answer only using the provided context.
        - If the context is insufficient, say so.
        - Cite which context chunks support the answer.
        - Return JSON:
        {{
            "answer": "...",
            "sources": [...]
        }}
        """

    try:
        response = llm_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "You return ONLY valid JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

        raw = response.choices[0].message.content

        print("\n[DEBUG] GROQ RAW RESPONSE:", raw)

        redis_client.setex(
            cache_key,
            3600,
            raw)
        
        parsed = json.loads(raw)

        print("Response", {"success": True, "response": parsed})
    
        return {
            "success": True,
            "response": parsed
        }           
    
    except Exception as e:
        print("\n[ERROR]", str(e))
        return {"success": False, "error": str(e)}