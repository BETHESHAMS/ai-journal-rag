import os
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings loaded from environment variables and .env file.
    Follows Pydantic v2 BaseSettings pattern for type safety and validation.
    """
    # Server metadata
    PROJECT_NAME: str = "Personalized AI Journal RAG"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # JWT Authentication
    JWT_SECRET: str = "super_secret_jwt_key_change_me_in_production_12345"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Supabase (PostgreSQL + pgvector)
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    # AI Provider Toggle: "openrouter" or "ollama"
    LLM_PROVIDER: Literal["openrouter", "ollama"] = "openrouter"

    # OpenRouter Config
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "meta-llama/llama-3.3-70b-instruct"

    # Ollama Config (Local execution)
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    OLLAMA_API_KEY: str = "ollama"
    OLLAMA_MODEL: str = "llama3.2"

    # Embedding Config
    EMBEDDING_PROVIDER: Literal["fastembed", "openai"] = "fastembed"
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIMENSION: int = 384
    OPENAI_API_KEY: str = ""

    @property
    def active_llm_base_url(self) -> str:
        if self.LLM_PROVIDER == "ollama":
            return self.OLLAMA_BASE_URL
        return self.OPENROUTER_BASE_URL

    @property
    def active_llm_api_key(self) -> str:
        if self.LLM_PROVIDER == "ollama":
            return self.OLLAMA_API_KEY or "ollama"
        return self.OPENROUTER_API_KEY

    @property
    def active_llm_model(self) -> str:
        if self.LLM_PROVIDER == "ollama":
            return self.OLLAMA_MODEL
        return self.OPENROUTER_MODEL

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()
