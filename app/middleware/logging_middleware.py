import time
from starlette.middleware.base import BaseHTTPMiddleware
from core.logger import logger

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()
        request_id = request.state.request_id

        user_name = request.headers.get(
            "x-user-name",
            "anonymous"
        )
        
        logger.info(
            "incoming_request",
            extra={
                "request_id": request_id,
                "user": user_name,
                "path": request.url.path,
                "method": request.method,
            }
        )

        response = await call_next(request)
        duration = round(time.time() - start, 2)
        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "duration": duration,
            }
        )
        return response