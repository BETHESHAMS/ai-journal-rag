import logging
from typing import List
from app.core.config import settings

logger = logging.getLogger("ai_journal.embeddings")

_embedding_model = None


class EmbeddingService:
    """
    High-performance, modular embedding generator.
    By default uses FastEmbed (ONNX runtime) to generate 384-dim dense embeddings locally
    without GPU requirements, external API costs, or network bottlenecks.
    """

    def __init__(self):
        self.provider = settings.EMBEDDING_PROVIDER
        self.dimension = settings.EMBEDDING_DIMENSION
        self.model_name = settings.EMBEDDING_MODEL_NAME

    def _get_fastembed_model(self):
        global _embedding_model
        if _embedding_model is None:
            try:
                from fastembed import TextEmbedding
                logger.info(f"Loading local FastEmbed model [{self.model_name}] on CPU...")
                _embedding_model = TextEmbedding(model_name=self.model_name)
            except Exception as e:
                logger.warning(f"FastEmbed failed to initialize ({e}). Falling back to lightweight hash-embedding for testing.")
                _embedding_model = "fallback"
        return _embedding_model

    def embed_text(self, text: str) -> List[float]:
        """Embeds a single string into a dense vector."""
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embeds a batch of strings into a list of dense vectors."""
        if not texts:
            return []

        if self.provider == "fastembed":
            model = self._get_fastembed_model()
            if model != "fallback":
                try:
                    embeddings_gen = model.embed(texts)
                    return [list(vec.tolist() if hasattr(vec, "tolist") else vec) for vec in embeddings_gen]
                except Exception as e:
                    logger.error(f"Error during FastEmbed inference: {e}. Using fallback.")

        # Resilient fallback: normalized deterministic vector for sandbox/test environments
        logger.warning("Generating deterministic normalized vector fallback.")
        return [self._generate_fallback_vector(t) for t in texts]

    def _generate_fallback_vector(self, text: str) -> List[float]:
        """Generates a normalized float vector based on text hash for testing without internet."""
        import hashlib
        import math
        vec = []
        for i in range(self.dimension):
            h = hashlib.sha256(f"{text}_{i}".encode("utf-8")).hexdigest()
            val = (int(h[:8], 16) / 0xFFFFFFFF) * 2.0 - 1.0
            vec.append(val)
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


embedding_service = EmbeddingService()
