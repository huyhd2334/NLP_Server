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

def safe_json_parse(data: str):

    print("\n[DEBUG] RAW TYPE:", type(data))
    print("[DEBUG] RAW DATA:", data)

    parsed = data

    for i in range(2): 
        if isinstance(parsed, str):
            try:
                parsed = json.loads(parsed)
                print(f"[DEBUG] AFTER json.loads level {i+1}:", type(parsed))
            except Exception as e:
                print("[DEBUG] JSON PARSE ERROR:", str(e))
                break

    print("[DEBUG] FINAL PARSED TYPE:", type(parsed))
    print("[DEBUG] FINAL PARSED:", parsed)

    return parsed


async def task_generate_service(req):
    cache_key = "task:" + hashlib.md5(req.encode()).hexdigest()
    cached = redis_client.get(cache_key)

    if cached:
        print("\n[DEBUG] CACHE HIT")
        parsed = safe_json_parse(cached)

        return {
            "success": True,
            "tasks": parsed.get("tasks") if isinstance(parsed, dict) else parsed
        }

    print("\n[DEBUG] CACHE MISS")

    prompt = f"""
        Break this description into tasks:
        - only max 4 tasks
        - no newline
        - return ONLY valid JSON:

        {{
        "tasks": [
            "task 1",
            "task 2"
        ]
        }}

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

        parsed = safe_json_parse(raw)

        # validate final
        if not isinstance(parsed, dict):
            raise ValueError(f"Parsed result is not dict: {type(parsed)}")

        if "tasks" not in parsed:
            raise ValueError(f"Missing 'tasks' key: {parsed}")

        # save cache
        redis_client.setex(
            cache_key,
            3600,
            json.dumps(parsed)
        )
        print("Response", {"success": True, "tasks": parsed["tasks"]})
        
        return {
            "success": True,
            "tasks": parsed["tasks"]
        }

    except Exception as e:
        print("\n[ERROR]", str(e))

        return {
            "success": False,
            "error": str(e)
        }