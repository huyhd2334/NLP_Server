from app.services.llm_service import llm_responser
from app.services.upload_services.embedding_service import embed
from app.services.upload_services.chunking_service import chunk_text
from app.services.rag_services.vector_service import search
from app.services.rag_services.norm_service import norm_query
from sentence_transformers import CrossEncoder
import asyncio

reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2") 

async def RAG_responses(query: str, documents: list[str], top_k: int, is_rerank: bool=False, top_n=5):

    query_norm = norm_query(query)
    print("[DEBUG] query_norm done", query_norm)
    
    query_embedded = await embed(query_norm, is_query=True)
    print("[DEBUG] query_embedded done", query_embedded)

    chunks = await search(query_embed=query_embedded, file_ids=documents, top_k=top_k)
    if is_rerank:
        pairs = [(query, c["text"]) for c in chunks]
        loop = asyncio.get_running_loop()
        scores = await loop.run_in_executor(None, reranker.predict, pairs)
        ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
        chunks = [c for c, s in ranked[:top_n]]
        print("[DEBUG] chunks reranked", len(chunks))
    else:
        print("[DEBUG] chunks done", chunks)

    llm_res = await llm_responser(query, chunks)
    print("[DEBUG] llm_res done", llm_res)

    return llm_res, chunks
    


# import dotenv
# import os
# import json
# import hashlib
# import gzip
# import re
# import asyncio
# from openai import AsyncOpenAI 
# import redis.asyncio as aioredis  

# dotenv.load_dotenv()

# stats = {
#     "total_errors": 0,
#     "connect_errors": 0
# }

# llm_client = AsyncOpenAI(
#     api_key=os.getenv("GROQ_API_KEY"),
#     base_url="https://api.groq.com/openai/v1"
# )

# redis_client = aioredis.Redis(
#     host="127.0.0.1",
#     port=6379,
#     decode_responses=False, 
#     socket_timeout=10,
#     socket_connect_timeout=10,
#     retry_on_timeout=True,
#     health_check_interval=30
# )

# def safe_json_loads(text: str):
#     text = text.strip()
#     if text.startswith("```json"):
#         text = text[7:]
#     if text.endswith("```"):
#         text = text[:-3]
#     text = text.strip()
    
#     try:
#         return json.loads(text)
#     except Exception:
#         text = text.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")
#         return json.loads(text)


# async def llm_responser(query: str, chunks):
#     if not chunks:
#         return {
#             "success": True,
#             "response": {
#                 "answer": "No relevant documents found",
#                 "sources": []
#             }
#         }

#     context = "\n".join(chunk["text"][:800] for chunk in chunks)

#     cache_key = "rag:" + hashlib.md5(
#         f"{query}::{context}".encode()
#     ).hexdigest()

#     try:
#         cached = await redis_client.get(cache_key)
#         if cached:
#             print("\n[DEBUG] CACHE HIT")
#             data = json.loads(gzip.decompress(cached).decode())
#             return {
#                 "success": True,
#                 "response": data
#             }
#     except Exception as e:
#         print("[WARN] Redis GET failed:", e)

#     print("\n[DEBUG] CACHE MISS")

#     prompt = f"""
#         You are a professional RAG assistant.

#         Question:
#         {query}

#         Context:
#         {context}

#         Return STRICT JSON ONLY:
#         {{
#         "answer": "...",
#         "sources": []
#         }}
#         """

#     # Cơ chế tự động Retry gối đầu khi gặp Rate Limit 429
#     max_retries = 5
#     for attempt in range(max_retries):
#         try:
#             response = await llm_client.chat.completions.create(
#                 model="llama-3.1-8b-instant",
#                 temperature=0,
#                 response_format={"type": "json_object"},
#                 messages=[
#                     {"role": "system", "content": "Return ONLY valid JSON structure."},
#                     {"role": "user", "content": prompt}
#                 ]
#             )

#             raw = response.choices[0].message.content
#             print("\n[DEBUG] RAW:", raw)

#             parsed = safe_json_loads(raw)

#             try:
#                 await redis_client.setex(
#                     cache_key,
#                     3600,
#                     gzip.compress(json.dumps(parsed).encode())
#                 )
#             except Exception as e:
#                 print("[WARN] Redis SET failed:", e)

#             return {
#                 "success": True,
#                 "response": parsed
#             }

#         except Exception as e:
#             err_msg = str(e)
            
#             # XỬ LÝ RIÊNG LỖI 429 RATE LIMIT
#             if "429" in err_msg or "rate_limit" in err_msg.lower():
#                 wait_time = 15.0
#                 # Tự động bóc tách số giây Groq yêu cầu từ log (ví dụ: "try again in 13.17s")
#                 match = re.search(r"try again in (\d+\.\d+)s", err_msg)
#                 if match:
#                     wait_time = float(match.group(1)) + 1.0  # Cộng 1 giây dự phòng trễ mạng
                
#                 print(f"\n[⚠️ RATE LIMIT] Groq nghẽn băng thông. Tự động nghỉ {wait_time} giây rồi thử lại (Lần {attempt + 1}/{max_retries})...")
#                 await asyncio.sleep(wait_time)
#                 continue  # Quay lại đầu vòng lặp để bắn lại request cũ
            
#             # XỬ LÝ CÁC LỖI KHÁC (Báo lỗi chung và lưu thống kê)
#             print("[ERROR]", err_msg)
#             stats["total_errors"] += 1
            
#             if "connection" in err_msg.lower() or "timeout" in err_msg.lower():
#                 stats["connect_errors"] += 1
                
#             print(f"-> Thống kê lỗi hiện tại: [Tổng số lỗi: {stats['total_errors']}] | [Lỗi Kết Nối: {stats['connect_errors']}]")
            
#             return {
#                 "success": False,
#                 "error": err_msg
#             }
            
#     # Trường hợp thử lại hết 5 lần vẫn lỗi
#     return {
#         "success": False,
#         "error": "Failed after max retries due to rate limits."
#     }