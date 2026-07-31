import dotenv
import os
import json
import hashlib
import gzip
import re
import asyncio
from openai import AsyncOpenAI 
import redis.asyncio as aioredis  

dotenv.load_dotenv()

stats = {
    "total_errors": 0,
    "connect_errors": 0
}


GROQ_KEYS = [
    os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY"),
    os.getenv("GROQ_API_KEY_2"),
    os.getenv("GROQ_API_KEY_3")
]

GROQ_KEYS = [k for k in GROQ_KEYS if k]

current_key_index = 0

def get_llm_client():
    global current_key_index
    active_key = GROQ_KEYS[current_key_index]
    print(f"[INFO] 🔑 Using Groq API Key: {active_key[:8]}...")
    return AsyncOpenAI(
        api_key=active_key,
        base_url="https://api.groq.com/openai/v1"
    )

llm_client = get_llm_client()

def switch_to_next_key():
    global current_key_index, llm_client
    if len(GROQ_KEYS) <= 1:
        print("[ERROR] Invalid Key ")
        return False
        
    current_key_index = (current_key_index + 1) % len(GROQ_KEYS)
    print(f"\n[🔄 SWITCH KEY] {current_key_index}...")
    llm_client = get_llm_client()
    return True


redis_client = aioredis.Redis(
    host="127.0.0.1",
    port=6379,
    decode_responses=False,  
    socket_timeout=10,
    socket_connect_timeout=10,
    retry_on_timeout=True,
    health_check_interval=30
)


def safe_json_loads(text: str):
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    try:
        return json.loads(text)
    except Exception:
        text = text.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")
        return json.loads(text)


async def llm_responser(query: str, chunks):
    global llm_client
    
    if not chunks:
        return {
            "success": True,
            "response": {
                "answer": "No relevant documents found",
                "sources": []
            }
        }

    context = "\n".join(chunk["text"][:800] for chunk in chunks)

    cache_key = "rag:" + hashlib.md5(
        f"{query}::{context}".encode()
    ).hexdigest()

    try:
        cached = await redis_client.get(cache_key)
        if cached:
            print("\n[DEBUG] CACHE HIT")
            data = json.loads(gzip.decompress(cached).decode())
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

    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = await llm_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "Return ONLY valid JSON structure."},
                    {"role": "user", "content": prompt}
                ]
            )

            raw = response.choices[0].message.content
            print("\n[DEBUG] RAW:", raw)

            parsed = safe_json_loads(raw)

            try:
                await redis_client.setex(
                    cache_key,
                    gzip.compress(json.dumps(parsed).encode())
                )
            except Exception as e:
                print("[WARN] Redis SET failed:", e)

            return {
                "success": True,
                "response": parsed
            }

        except Exception as e:
            err_msg = str(e)
            
            if "429" in err_msg or "rate_limit" in err_msg.lower():
                
                if "limit 500000" in err_msg.lower() or attempt >= 2:
                    print(f"\n[CRITICAL] Reach Limit Quota / Day (Try attempt: {attempt + 1}). Switch Key...")
                    if switch_to_next_key():
                        await asyncio.sleep(2) 
                        continue

                wait_time = 15.0
                match = re.search(r"try again in (\d+\.\d+)s", err_msg)
                if match:
                    wait_time = float(match.group(1)) + 1.0
                
                print(f"\n[RATE LIMIT] Groq. Auto sleep {wait_time}s - (Attempt {attempt + 1}/{max_retries})...")
                await asyncio.sleep(wait_time)
                continue 
            
            print("[ERROR]", err_msg)
            stats["total_errors"] += 1
            
            if "connection" in err_msg.lower() or "timeout" in err_msg.lower():
                stats["connect_errors"] += 1
                
            print(f"-> Number current errors: [Total Errors: {stats['total_errors']}] | [NextWork Errors: {stats['connect_errors']}]")
            
            return {
                "success": False,
                "error": err_msg
            }
            
    return {
        "success": False,
        "error": "Failed after max retries due to rate limits."
    }