import pytest
from app.services.rag_service import rag_service
from app.services.llm.client import OpenAICompatibleLLMClient


def test_chunking_short_text():
    text = "Today was a quiet day. I read a book."
    chunks = rag_service.chunk_text(text, max_chunk_size=100)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunking_long_text_preserves_sentences():
    text = (
        "On Monday morning I had blueberry pancakes for breakfast. "
        "Then I went to the library to study distributed systems. "
        "In the afternoon I attended a team meeting about vector embeddings and pgvector. "
        "For dinner I cooked pasta with homemade garlic tomato sauce. "
        "Before going to bed I planned my schedule for the rest of the week."
    )
    chunks = rag_service.chunk_text(text, max_chunk_size=120, overlap=30)
    assert len(chunks) > 1
    # Ensure every chunk is non-empty
    for c in chunks:
        assert len(c.strip()) > 0


def test_prompt_messages_construction_with_citations():
    query = "What did I eat on Tuesday?"
    context_chunks = [
        {
            "entry_id": "note-1",
            "entry_date": "2026-09-20",
            "chunk_text": "On Tuesday I ate avocado toast and poached eggs.",
            "similarity": 0.88
        }
    ]
    messages, citations = rag_service.build_prompt_messages(query, context_chunks)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "2026-09-20" in messages[0]["content"]
    assert "avocado toast" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == query

    assert len(citations) == 1
    assert citations[0].entry_id == "note-1"
    assert citations[0].entry_date == "2026-09-20"
    assert citations[0].similarity == 0.88


def test_llm_abstraction_parameters():
    # Test OpenRouter mapping
    client_cloud = OpenAICompatibleLLMClient(
        provider="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key="test-key",
        model="meta-llama/llama-3.3-70b-instruct"
    )
    assert client_cloud.provider_name == "openrouter"
    assert client_cloud.model_name == "meta-llama/llama-3.3-70b-instruct"

    # Test Ollama mapping
    client_local = OpenAICompatibleLLMClient(
        provider="ollama",
        base_url="http://localhost:11434/v1",
        api_key="ollama",
        model="llama3.2"
    )
    assert client_local.provider_name == "ollama"
    assert client_local.model_name == "llama3.2"
