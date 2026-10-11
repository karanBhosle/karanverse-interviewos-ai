import pytest

from app.services.coach import fallback_bridge, looks_closing, looks_unsure, refine_spoken_transcript
from app.services.llm import MockLLMProvider


def test_looks_unsure_detects_i_dont_know():
    assert looks_unsure("I don't know")
    assert looks_unsure("I do not know that")
    assert looks_unsure("no idea")
    assert looks_unsure("skip")
    assert looks_unsure("I said can we skip the question")
    assert looks_unsure("Can you skip that question")
    assert looks_unsure("I can't answer that")
    assert looks_unsure("not familiar with that")
    assert not looks_unsure("I used LangGraph with a typed state and retry limits.")
    assert looks_closing("Thank you")
    assert looks_closing("thanks")
    assert not looks_closing("Thank you for asking about LangGraph, I used it on the coach graph.")


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


@pytest.mark.asyncio
async def test_refine_spoken_transcript_regenerates_the_sentence():
    provider = MockLLMProvider({"sentence": "I worked at CRISIL last year."})
    text = await refine_spoken_transcript(
        "I worked at Crystal last year",
        terms=["CRISIL", "Python"],
        provider=provider,
    )
    assert text == "I worked at CRISIL last year."


@pytest.mark.asyncio
async def test_refine_spoken_transcript_rejects_invented_facts():
    provider = MockLLMProvider(
        {"sentence": "I built a production RAG system at Google with 40 percent recall gains."}
    )
    exact = "I used pdfs for the resume"
    text = await refine_spoken_transcript(exact, terms=["PDFs", "RAG"], provider=provider)
    assert "Google" not in text
    assert "pdfs" in text.lower() or "PDFs" in text
