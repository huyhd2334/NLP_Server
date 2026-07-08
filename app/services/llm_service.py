import dotenv
import os
import json
import hashlib
import gzip
import re
import asyncio
from openai import AsyncOpenAI 
import redis.asyncio as aioredis  

# Tải các biến môi trường từ file .env
dotenv.load_dotenv()

# Sử dụng một dict toàn cục để theo dõi các số liệu thống kê một cách an toàn
stats = {
    "total_errors": 0,
    "connect_errors": 0
}

# =====================================================================
# 1. CẤU HÌNH HỆ THỐNG TỰ ĐỘNG XOAY VÒNG API KEY (GROQ ROTATION)
# =====================================================================
# Hệ thống sẽ tự động quét qua các Key này trong file .env của bạn
GROQ_KEYS = [
    os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY"),  # Thử lấy Key 1 hoặc Key mặc định
    os.getenv("GROQ_API_KEY_2"),
    os.getenv("GROQ_API_KEY_3")
]

# Lọc bỏ các phần tử trống (None) nếu bạn điền ít hơn 3 Key trong file .env
GROQ_KEYS = [k for k in GROQ_KEYS if k]

# Biến toàn cục theo dõi vị trí Key đang hoạt động
current_key_index = 0

def get_llm_client():
    """Khởi tạo OpenAI Client bất đồng bộ dựa trên API Key đang kích hoạt."""
    global current_key_index
    active_key = GROQ_KEYS[current_key_index]
    # In ra 8 ký tự đầu để bạn dễ theo dõi tiến trình đổi Key trong Terminal
    print(f"[INFO] 🔑 Đang sử dụng Groq API Key: {active_key[:8]}...")
    return AsyncOpenAI(
        api_key=active_key,
        base_url="https://api.groq.com/openai/v1"
    )

# Khởi tạo instance client đầu tiên khi ứng dụng nạp file
llm_client = get_llm_client()

def switch_to_next_key():
    """Tự động chuyển đổi sang API Key tiếp theo khi Key hiện tại cạn hạn mức ngày."""
    global current_key_index, llm_client
    if len(GROQ_KEYS) <= 1:
        print("[ERROR] Không tìm thấy bất kỳ API Key dự phòng nào khác trong file .env!")
        return False
        
    current_key_index = (current_key_index + 1) % len(GROQ_KEYS)
    print(f"\n[🔄 SWITCH KEY] Phát hiện cạn hạn mức NGÀY. Tự động đổi sang API Key dự phòng vị trí số {current_key_index}...")
    llm_client = get_llm_client()
    return True


# =====================================================================
# 2. KHỞI TẠO KẾT NỐI REDIS CACHE
# =====================================================================
redis_client = aioredis.Redis(
    host="127.0.0.1",
    port=6379,
    decode_responses=False,  # Bắt buộc để False để đọc ghi dữ liệu nén dạng bytes (gzip)
    socket_timeout=10,
    socket_connect_timeout=10,
    retry_on_timeout=True,
    health_check_interval=30
)


# =====================================================================
# 3. HÀM CHUẨN HÓA VÀ ÉP KIỂU JSON (PARSER)
# =====================================================================
def safe_json_loads(text: str):
    """Bóc tách cấu trúc JSON từ phản hồi thô của LLM, tránh lỗi định dạng markdown."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    try:
        return json.loads(text)
    except Exception:
        # Xử lý các ký tự xuống dòng hoặc tab bị lỗi trong chuỗi string của LLM
        text = text.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")
        return json.loads(text)


# =====================================================================
# 4. HÀM XỬ LÝ CHÍNH TRẢ LỜI CÂU HỎI (LLM RESPONSER)
# =====================================================================
async def llm_responser(query: str, chunks):
    global llm_client
    
    # Trường hợp Qdrant không tìm thấy tài liệu liên quan nào
    if not chunks:
        return {
            "success": True,
            "response": {
                "answer": "No relevant documents found",
                "sources": []
            }
        }

    # GIỮ NGUYÊN DANH SÁCH CHUNKS: Lấy toàn bộ chunks truyền vào từ tầng ngoài
    # Phục vụ chính xác cho việc so sánh hiệu năng của top_k = 5 và top_k = 10
    # Cắt nhẹ ký tự xuống 800 để tối ưu dung lượng token gửi đi
    context = "\n".join(chunk["text"][:800] for chunk in chunks)

    # Tạo mã băm MD5 duy nhất làm Key cho Cache Redis
    cache_key = "rag:" + hashlib.md5(
        f"{query}::{context}".encode()
    ).hexdigest()

    # Thử lấy dữ liệu từ Redis Cache trước
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

    # Xây dựng Prompt RAG chuẩn hóa bắt buộc trả về định dạng JSON
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

    # Vòng lặp tự động thử lại (Retry Logic) tối đa 5 lần cho mỗi câu hỏi
    max_retries = 5
    for attempt in range(max_retries):
        try:
            # Luôn gọi thông qua llm_client toàn cục để bắt kịp API Key vừa đổi nếu có biến cố
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

            # Ghi đè câu trả lời mới vào Redis Cache và nén lại để tiết kiệm RAM cho Redis
            try:
                await redis_client.setex(
                    cache_key,
                    3600,  # Thời gian hết hạn cache: 1 tiếng (3600 giây)
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
            
            # XỬ LÝ RIÊNG BIỆT CÁC TRƯỜNG HỢP LỖI RATE LIMIT (429)
            if "429" in err_msg or "rate_limit" in err_msg.lower():
                
                # Kịch bản 1: Nếu dính lỗi cạn kiệt Quota NGÀY (Limit 500,000 tokens) hoặc thử lại 3 lần vẫn nghẽn
                if "limit 500000" in err_msg.lower() or attempt >= 2:
                    print(f"\n[🚨 CRITICAL] Key hiện tại đã chạm trần Quota NGÀY (Lần thử {attempt + 1}). Tiến hành xoay Key...")
                    if switch_to_next_key():
                        await asyncio.sleep(2)  # Tạm nghỉ 2 giây làm sạch kết nối mạng cũ
                        continue  # Đổi Key thành công, lập tức gửi lại câu hỏi này với Key mới ngay

                # Kịch bản 2: Nếu chỉ bị nghẽn băng thông PHÚT (TPM) thông thường từ Groq
                wait_time = 15.0
                match = re.search(r"try again in (\d+\.\d+)s", err_msg)
                if match:
                    # Trích xuất số giây chính xác Groq yêu cầu từ Exception Log và cộng thêm 1 giây dự phòng trễ mạng
                    wait_time = float(match.group(1)) + 1.0
                
                print(f"\n[⚠️ RATE LIMIT] Groq nghẽn phút. Tự động nghỉ {wait_time} giây rồi thử lại (Lần {attempt + 1}/{max_retries})...")
                await asyncio.sleep(wait_time)
                continue  # Quay lại đầu luồng vòng lặp bắn lại request cũ
            
            # XỬ LÝ CÁC LOẠI LỖI KHÁC (Lỗi mạng, timeout, đứt kết nối...)
            print("[ERROR]", err_msg)
            stats["total_errors"] += 1
            
            if "connection" in err_msg.lower() or "timeout" in err_msg.lower():
                stats["connect_errors"] += 1
                
            print(f"-> Thống kê lỗi hiện tại: [Tổng số lỗi: {stats['total_errors']}] | [Lỗi Kết Nối: {stats['connect_errors']}]")
            
            return {
                "success": False,
                "error": err_msg
            }
            
    # Kết thúc 5 lần thử lại mà vẫn không thành công
    return {
        "success": False,
        "error": "Failed after max retries due to rate limits."
    }