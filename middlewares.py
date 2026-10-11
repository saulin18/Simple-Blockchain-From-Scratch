

import logging
from fastapi.responses import JSONResponse
from contextvars import ContextVar
from uuid import uuid4
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request

logger = logging.getLogger(__name__)


async def blockchain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.warning("Blockchain rule rejected path=%s detail=%s", request.url.path, exc)
    return JSONResponse(status_code=400, content={"detail": str(exc)})


CORRELATION_ID_CTX_KEY = 'correlation_id'
REQUEST_ID_CTX_KEY = 'request_id'

_correlation_id_ctx_var: ContextVar[str] = ContextVar(CORRELATION_ID_CTX_KEY, default="-")
_request_id_ctx_var: ContextVar[str] = ContextVar(REQUEST_ID_CTX_KEY, default="-")


def get_correlation_id() -> str:
    return _correlation_id_ctx_var.get()


def get_request_id() -> str:
    return _request_id_ctx_var.get()


class RequestContextFilter(logging.Filter):
    """Copy the current request ids onto each log record so formatters can print them."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        record.correlation_id = get_correlation_id()
        return True


class RequestContextLogMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        correlation_token = _correlation_id_ctx_var.set(
            request.headers.get("X-Correlation-ID", str(uuid4()))
        )
        request_token = _request_id_ctx_var.set(str(uuid4()))
        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = get_correlation_id()
            response.headers["X-Request-ID"] = get_request_id()
            return response
        finally:
            _request_id_ctx_var.reset(request_token)
            _correlation_id_ctx_var.reset(correlation_token)