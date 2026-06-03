from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

async def task_generate_service(req):

    prompt = f"""
    Break this description into tasks:
    You must return folow this fomat:
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
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
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

        return response.choices[0].message.content

    except Exception as e:
        return {
            "error": f"Groq API error: {str(e)}"
        }