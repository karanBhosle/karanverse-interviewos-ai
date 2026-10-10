from __future__ import annotations

import hashlib
import math
from collections.abc import Iterable

import numpy as np

from app.core.config import get_settings


class EmbeddingEncoder:
    def __init__(self, model_name: str | None = None, dim: int = 64):
        settings = get_settings()
        self.model_name = model_name or settings.embedding_model
        self.dim = dim
        self._st_model = None
        if self.model_name not in {"hashing-fallback", "", None}:
            try:
                from sentence_transformers import SentenceTransformer

                self._st_model = SentenceTransformer(self.model_name)
            except Exception:
                self._st_model = None

    def encode(self, texts: Iterable[str]) -> np.ndarray:
        values = list(texts)
        if self._st_model is not None:
            return np.asarray(self._st_model.encode(values), dtype=np.float32)
        return np.vstack([self._hash_embed(text) for text in values])

    def _hash_embed(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dim, dtype=np.float32)
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:2], "little") % self.dim
            sign = 1.0 if digest[2] % 2 == 0 else -1.0
            vector[index] += sign
        norm = np.linalg.norm(vector)
        if norm:
            vector /= norm
        return vector


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def reciprocal_rank_fusion(*ranked_id_lists: list[str], k: int = 60) -> list[str]:
    scores: dict[str, float] = {}
    for ranked in ranked_id_lists:
        for rank, item_id in enumerate(ranked, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return [item for item, _ in sorted(scores.items(), key=lambda pair: pair[1], reverse=True)]
