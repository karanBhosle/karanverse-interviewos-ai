from app.retrieval.embeddings import reciprocal_rank_fusion
from app.retrieval.hybrid import HybridRetriever


def test_hybrid_search_returns_sources():
    retriever = HybridRetriever()
    results = retriever.search("hybrid BM25 reciprocal rank fusion", limit=3)
    assert results
    assert all(item["evidence_category"] == "retrieved_reference" for item in results)
    assert all(item["id"] for item in results)


def test_rrf_merges_lists():
    fused = reciprocal_rank_fusion(["a", "b", "c"], ["c", "a", "d"])
    assert fused[0] in {"a", "c"}
