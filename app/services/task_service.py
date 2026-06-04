from openai import OpenAI
import os
from dotenv import load_dotenv
import json
import redis
import hashlib


load_dotenv()

llm_client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)

async def task_generate_service(req):
    # cache key
    cache_key = "task" + hashlib.md5(req.encode()).hexdigest()
    cached = redis_client.get(cache_key)

    if cached:
        print("CACHED")
        return json.loads(cached)
    
    print("CACHE MISS")

    prompt = f"""
    Break this description into tasks:
    only one task,
    do not include "\n" between sentences,
    max number of task 1, 2, .. on tasks <= 4 
    Return ONLY valid JSON in this format:
    {{
      "tasks": [
        "task 1",
        "task 2",
        "task 3"
      ]
    }}
    No explanation, no markdown.
    Description:
    {req}
    """
    try:
        response = llm_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that breaks descriptions into structured tasks."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        raw = response.choices[0].message.content

        redis_client.setex(cache_key, 3600, json.dumps(raw))

        return json.loads(raw)
    except Exception as e:
        return {
            "error": f"Groq API error: {str(e)}"
        }