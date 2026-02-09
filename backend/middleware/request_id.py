"""
Request ID Middleware

Adds a unique X-Request-ID header to every request/response for tracing.
If the client sends an X-Request-ID, it is reused; otherwise a new UUID is generated.
The request ID is stored in request.state for use in logging.
"""
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

HEADER_NAME = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Reuse client-provided ID or generate a new one
        request_id = request.headers.get(HEADER_NAME) or str(uuid.uuid4())
        request.state.request_id = request_id

        response: Response = await call_next(request)
        response.headers[HEADER_NAME] = request_id
        return response
