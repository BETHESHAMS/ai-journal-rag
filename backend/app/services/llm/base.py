from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator


class BaseLLMClient(ABC):
    """
    Abstract Base Class for LLM Clients.
    Enforces a strict, provider-agnostic interface across all models (Ollama, OpenRouter, etc.).
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the identifier of the active provider (e.g. 'openrouter', 'ollama')."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Returns the specific model identifier currently targeted."""
        pass

    @abstractmethod
    async def generate(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """
        Executes a non-streaming chat completion request.
        :param messages: Standard list of message dicts: [{'role': 'user', 'content': '...'}]
        :return: Assistant completion string
        """
        pass

    @abstractmethod
    async def generate_stream(self, messages: List[Dict[str, str]], **kwargs: Any) -> AsyncGenerator[str, None]:
        """
        Executes a token-by-token streaming chat completion request.
        :param messages: Standard list of message dicts: [{'role': 'user', 'content': '...'}]
        :return: AsyncGenerator yielding token strings as they arrive
        """
        pass
