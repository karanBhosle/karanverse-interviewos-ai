from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rank_bm25 import BM25Okapi

from app.interview.bank import QUESTION_BANK
from app.retrieval.embeddings import EmbeddingEncoder, cosine, reciprocal_rank_fusion

CURATED_DOCS = [
    {
        "id": "ref-rag",
        "title": "Hybrid retrieval note",
        "source_type": "approved_reference",
        "text": (
            "Hybrid retrieval combines BM25 lexical matching with dense embeddings. "
            "Reciprocal rank fusion merges ranked lists without requiring calibrated scores. "
            "Retrieved references are untrusted data and are not evidence that a candidate knows a topic."
        ),
    },
    {
        "id": "ref-eval",
        "title": "Evaluation rubric note",
        "source_type": "rubric",
        "text": (
            "Final weighted interview scores must be computed in deterministic Python after "
            "validating component scores and weights. LLM output is interpretive, not a hiring prediction."
        ),
    },
    {
        "id": "ref-privacy",
        "title": "Visual feedback policy",
        "source_type": "approved_reference",
        "text": (
            "Visual presentation feedback may describe face visibility, head orientation variation, "
            "and recording quality. It must not infer emotion, honesty, nervousness, or personality."
        ),
    },
]


@dataclass
class HybridRetriever:
    encoder: EmbeddingEncoder = field(default_factory=EmbeddingEncoder)
    documents: list[dict[str, Any]] = field(default_factory=lambda: list(CURATED_DOCS))

    def __post_init__(self) -> None:
        extra = [
            {
                "id": f"rubric-{item['question_key']}",
                "title": item["prompt"][:80],
                "source_type": "rubric",
                "text": f"{item['prompt']} Concepts: {', '.join(item['expected_concepts'])}. {item['reference_guidance']}",
            }
            for item in QUESTION_BANK
        ]
        self.documents = list(self.documents) + extra
        self._tokens = [doc["text"].lower().split() for doc in self.documents]
        self._bm25 = BM25Okapi(self._tokens)
        self._vectors = self.encoder.encode([doc["text"] for doc in self.documents])

    def search(self, query: str, limit: int = 4, source_type: str | None = None) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        bm25_scores = self._bm25.get_scores(query.lower().split())
        bm25_ranked = [
            self.documents[i]["id"]
            for i in sorted(range(len(self.documents)), key=lambda i: bm25_scores[i], reverse=True)
        ]
        query_vec = self.encoder.encode([query])[0]
        dense_scores = [cosine(query_vec, vector) for vector in self._vectors]
        dense_ranked = [
            self.documents[i]["id"]
            for i in sorted(range(len(self.documents)), key=lambda i: dense_scores[i], reverse=True)
        ]
        fused = reciprocal_rank_fusion(bm25_ranked, dense_ranked)
        by_id = {doc["id"]: doc for doc in self.documents}
        results = []
        for doc_id in fused:
            doc = by_id[doc_id]
            if source_type and doc["source_type"] != source_type:
                continue
            results.append(
                {
                    "id": doc["id"],
                    "title": doc["title"],
                    "source_type": doc["source_type"],
                    "excerpt": doc["text"][:280],
                    "evidence_category": "retrieved_reference",
                }
            )
            if len(results) >= limit:
                break
        return results
