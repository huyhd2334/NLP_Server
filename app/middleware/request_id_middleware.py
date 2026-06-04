import uuid 
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get(
            "x-request_id",
            str(uuid.uuid4)
        )

        request.state.resquest_id = request_id

        res = await call_next(request)

        res.headers["x-request-id"] = request_id

        return res


