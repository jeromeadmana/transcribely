from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import async_engine, Base
from app.api.routes import auth, videos, transcripts, billing

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create database tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await async_engine.dispose()


app = FastAPI(
    title="Transcribely API",
    description="Video transcription SaaS API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - allow all origins for development
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(videos.router, prefix="/api")
app.include_router(transcripts.router, prefix="/api")
app.include_router(billing.router, prefix="/api")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/")
async def root():
    return {
        "name": "Transcribely API",
        "version": "1.0.0",
        "docs": "/docs",
    }
