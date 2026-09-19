from fastapi import Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import settings
from .errors import error_body

limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.rate_limit_enabled,
    key_style="endpoint",
)


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=error_body("rate_limited", "Muitas tentativas. Aguarde um momento e tente novamente."),
        headers={"Retry-After": "60"},
    )


def reset() -> None:
    limiter.reset()
