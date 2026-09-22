import logging
from typing import List, Dict, Any, AsyncGenerator, Optional
from openai import AsyncOpenAI, APIError
from app.core.config import settings
from app.services.llm.base import BaseLLMClient

logger = logging.getLogger("ai_journal.llm")


class OpenAICompatibleLLMClient(BaseLLMClient):
    """
    Concrete LLM Client implementing the OpenAI-compatible API standard.
    This seamlessly unifies:
    1. OpenRouter (Cloud-hosted routing to Claude, GPT-4, Llama 3, DeepSeek, etc.)
    2. Ollama (Local, private models like Llama 3, Mistral, Qwen, etc.)
    """

    def __init__(
        self,
        provider: str,
        base_url: str,
        api_key: str,
        model: str,
        default_headers: Optional[Dict[str, str]] = None
    ):
        self._provider = provider
        self._base_url = base_url
        self._model = model
        
        # OpenRouter recommends HTTP-Referer and X-Title for app rankings/monitoring
        headers = default_headers or {}
        if provider == "openrouter":
            headers.setdefault("HTTP-Referer", "https://github.com/codeacious/ai-journal-rag")
            headers.setdefault("X-Title", "Personalized AI Journal RAG")

        self.client = AsyncOpenAI(
            base_url=self._base_url,
            api_key=api_key or "not-needed",
            default_headers=headers if headers else None,
            timeout=60.0
        )
        logger.info(f"Initialized LLM client [{self._provider.upper()}] targeting model: {self._model} via {self._base_url}")

    @property
    def provider_name(self) -> str:
        return self._provider

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """Executes non-streaming completion."""
        try:
            logger.info(f"Generating LLM response using [{self._provider}] / model [{self._model}]...")
            response = await self.client.chat.completions.create(
                model=self._model,
                messages=messages,
                stream=False,
                temperature=kwargs.get("temperature", 0.3),
                max_tokens=kwargs.get("max_tokens", 800)
            )
            return response.choices[0].message.content or ""
        except APIError as e:
            logger.error(f"Error calling {self._provider} LLM API: {e}")
            raise RuntimeError(f"{self._provider.capitalize()} LLM Error: {str(e)}")

    async def generate_stream(self, messages: List[Dict[str, str]], **kwargs: Any) -> AsyncGenerator[str, None]:
        """Streams completion tokens sequentially as they are generated."""
        try:
            logger.info(f"Streaming LLM response using [{self._provider}] / model [{self._model}]...")
            stream = await self.client.chat.completions.create(
                model=self._model,
                messages=messages,
                stream=True,
                temperature=kwargs.get("temperature", 0.3),
                max_tokens=kwargs.get("max_tokens", 800)
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except APIError as e:
            logger.error(f"Error streaming from {self._provider} LLM API: {e}")
            yield f"\n[LLM Generation Error: {str(e)}]"


def get_llm_client() -> BaseLLMClient:
    """
    Factory function producing the active LLM client based on environment configuration.
    Demonstrates true provider abstraction and zero vendor lock-in.
    """
    provider = settings.LLM_PROVIDER.lower()
    base_url = settings.active_llm_base_url
    api_key = settings.active_llm_api_key
    model = settings.active_llm_model

    return OpenAICompatibleLLMClient(
        provider=provider,
        base_url=base_url,
        api_key=api_key,
        model=model
    )
