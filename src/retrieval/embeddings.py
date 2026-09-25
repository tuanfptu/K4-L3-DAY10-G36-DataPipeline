from __future__ import annotations

from functools import lru_cache
import os
import hashlib
import math

from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=4)
def _load_model(model_name: str) -> SentenceTransformer:
    offline = os.getenv("HF_HUB_OFFLINE", "").lower() in {"1", "true", "yes"}
    return SentenceTransformer(model_name, local_files_only=offline)


class MiniLMEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        try:
            self.model = _load_model(model_name)
            self.backend = model_name
        except (OSError, ValueError):
            self.model = None
            self.backend = 'offline hashing fallback'

    @staticmethod
    def _hash(text: str) -> list[float]:
        vector = [0.0] * 384
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode('utf-8')).digest()
            index = int.from_bytes(digest[:4], 'big') % len(vector)
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.model is None:
            return [self._hash(text) for text in texts]
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        if self.model is None:
            return self._hash(text)
        embedding = self.model.encode([text], normalize_embeddings=True)
        return embedding[0].tolist()
