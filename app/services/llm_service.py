import dotenv
import redis
from openai import OpenAI
import os
import json
import hashlib
import gzip

dotenv.load_dotenv()

llm_client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

redis_client = redis.Redis(
    host="127.0.0.1",
    port=6379,
    decode_responses=False, 
    socket_timeout=10,
    socket_connect_timeout=10,
    retry_on_timeout=True,
    health_check_interval=30
)

def safe_json_loads(text: str):
    try:
        return json.loads(text)
    except Exception:
        text = text.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")
        return json.loads(text)
    
async def llm_responser(query: str, chunks):

    if not chunks:
        return {
            "success": True,
            "response": {
                "answer": "No relevant documents found",
                "sources": []
            }
        }


    context = "\n".join(chunk["text"][:1000] for chunk in chunks[:5])

    cache_key = "rag:" + hashlib.md5(
        f"{query}::{context}".encode()
    ).hexdigest()

    try:
        cached = redis_client.get(cache_key)
        if cached:
            print("\n[DEBUG] CACHE HIT")

            data = json.loads(
                gzip.decompress(cached).decode()
            )

            return {
                "success": True,
                "response": data
            }

    except Exception as e:
        print("[WARN] Redis GET failed:", e)

    print("\n[DEBUG] CACHE MISS")

    prompt = f"""
        You are a professional RAG assistant.

        Question:
        {query}

        Context:
        {context}

        Return STRICT JSON ONLY:
        {{
        "answer": "...",
        "sources": []
        }}
        """

    try:
        response = llm_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0,
            messages=[
                {"role": "system", "content": "Return ONLY valid JSON."},
                {"role": "user", "content": prompt}
            ]
        )

        raw = response.choices[0].message.content
        print("\n[DEBUG] RAW:", raw)

        parsed = safe_json_loads(raw)

        try:
            redis_client.setex(
                cache_key,
                3600,
                gzip.compress(json.dumps(parsed).encode())
            )
        except Exception as e:
            print("[WARN] Redis SET failed:", e)

        return {
            "success": True,
            "response": parsed
        }

    except Exception as e:
        print("[ERROR]", str(e))
        return {
            "success": False,
            "error": str(e)
        }