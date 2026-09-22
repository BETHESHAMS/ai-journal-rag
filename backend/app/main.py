import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import auth, notes, chat
from app.models.schemas import HealthResponse

# Configure structured logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ai_journal.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup diagnostics
    print("\n" + "=" * 60)
    print(" 🚀 Codeacious AI Journal (RAG MVP) - Backend Initialized")
    print("=" * 60)
    print(f" • Active LLM Provider: {settings.LLM_PROVIDER.upper()}")
    print(f" • Active Model:        {settings.active_llm_model}")
    print(f" • Active Base URL:     {settings.active_llm_base_url}")
    print(f" • Embedding Engine:    {settings.EMBEDDING_PROVIDER} ({settings.EMBEDDING_MODEL_NAME})")
    print(f" • Supabase DB Config:  {'Configured' if settings.SUPABASE_URL else 'NOT CONFIGURED (Check .env)'}")
    print("=" * 60 + "\n")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Full-stack multi-tenant AI Journal with pgvector RAG and OpenRouter/Ollama provider abstraction.",
    lifespan=lifespan
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers under /api
app.include_router(auth.router, prefix="/api")
app.include_router(notes.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.get("/api/health", response_model=HealthResponse, tags=["Diagnostics"])
async def health_check():
    """Returns backend health status, active provider toggle, and model info."""
    return HealthResponse(
        status="healthy",
        version=settings.VERSION,
        llm_provider=settings.LLM_PROVIDER,
        llm_model=settings.active_llm_model,
        database_configured=bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY)
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
