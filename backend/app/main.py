from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError

from .config import settings
from .db import init_db
from .errors import error_body
from .ratelimit import limiter, rate_limit_handler
from .routers import auth, catalog, groups, imports, matchdays, public, stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Peladex API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=error_body("integrity_conflict", "Operação conflita com dados existentes."),
    )


app.include_router(auth.router)
app.include_router(groups.router)
app.include_router(catalog.router)
app.include_router(matchdays.router)
app.include_router(imports.router)
app.include_router(stats.router)
app.include_router(public.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
