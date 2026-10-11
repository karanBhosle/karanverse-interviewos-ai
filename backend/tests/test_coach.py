from app.services.coach import fallback_bridge, looks_unsure


def test_looks_unsure_detects_i_dont_know():
    assert looks_unsure("I don't know")
    assert looks_unsure("I do not know that")
    assert looks_unsure("no idea")
    assert looks_unsure("skip")
    assert not looks_unsure("I used LangGraph with a typed state and retry limits.")


def test_fallback_bridge_moves_on():
    unsure = fallback_bridge(candidate="Karan", unsure=True, score=0.4, has_next=True)
    assert "next question" in unsure.lower()
    strong = fallback_bridge(
        candidate="Karan",
        unsure=False,
        score=4.2,
        has_next=True,
        next_prompt="Walk me through how you would evaluate a RAG system.",
    )
    assert "great to hear" in strong.lower()
    assert "RAG" in strong
    done = fallback_bridge(candidate="Karan", unsure=False, score=3.0, has_next=False)
    assert "wrap" in done.lower()
