from __future__ import annotations

import json
import logging
import re

from app.services.llm import CompatibleLLMProvider, LLMError, parse_json_object

logger = logging.getLogger(__name__)

UNSURE_PATTERN = re.compile(
    r"\b(i don'?t know|i do not know|no idea|not sure|no clue|skip(?: this)?|pass|"
    r"next question|i'?m done|i am done|that'?s all|nothing|cannot say)\b",
    re.IGNORECASE,
)


def looks_unsure(answer: str) -> bool:
    text = " ".join((answer or "").lower().split())
    if not text:
        return True
    if UNSURE_PATTERN.search(text):
        return True
    return len(text.split()) <= 3 and any(word in text for word in ("know", "idea", "skip", "pass", "sure"))


def fallback_bridge(*, candidate: str, unsure: bool, score: float, has_next: bool, next_prompt: str | None = None) -> str:
    name = candidate or "there"
    if not has_next:
        return f"Thanks {name}, that gives me enough to work with. Let me wrap the interview here."
    if unsure:
        lead = f"That's completely fine, {name}. We can leave that one."
    elif score >= 3.4:
        lead = f"Great to hear, {name}. That was a solid take."
    elif score >= 2.0:
        lead = f"Thanks {name}, I have that. Let's keep talking."
    else:
        lead = f"Appreciate you sharing that, {name}."
    follow = (next_prompt or "").strip()
    return f"{lead} {follow}".strip() if follow else f"{lead} Let's move to the next question."


async def spoken_bridge(
    *,
    candidate: str,
    question: str,
    answer: str,
    score: float,
    next_prompt: str | None,
    provider: CompatibleLLMProvider | None = None,
) -> dict[str, str]:
    unsure = looks_unsure(answer)
    has_next = bool(next_prompt)
    fallback = fallback_bridge(
        candidate=candidate, unsure=unsure, score=score, has_next=has_next, next_prompt=next_prompt
    )
    llm = provider or CompatibleLLMProvider()
    if not getattr(llm, "available", False):
        return {"spoken": fallback, "tone": "encouraging" if score >= 3.0 or unsure else "neutral"}
    system = (
        "You are Neerja, running a live interactive interview in Indian English. "
        "Reply with JSON only: {\"spoken\": string, \"tone\": \"encouraging\"|\"neutral\"|\"probing\"}. "
        "spoken is the full next thing you say out loud, 3 to 5 short sentences. "
        "React to the candidate's last answer like a real interviewer: name one thing they said, "
        "then naturally ask the next_question in your own spoken words. Keep the technical intent. "
        "If they do not know, be gracious and still ask the next_question. "
        "If there is no next_question, close the conversation warmly. "
        "Do not mention numeric scores, hiring, or personality. Do not say the words question bank."
    )
    user = json.dumps(
        {
            "candidate_name": candidate,
            "asked_question": question,
            "candidate_answer": answer,
            "coaching_score_0_to_5": score,
            "candidate_was_unsure": unsure,
            "next_question": next_prompt,
        }
    )
    try:
        result = await llm.complete_json(system=system, user=user, schema_name="coach_bridge")
        payload = parse_json_object(result.content)
        spoken = str(payload.get("spoken") or "").strip()
        tone = str(payload.get("tone") or "neutral").strip()
        if spoken:
            if next_prompt and next_prompt[:32].lower() not in spoken.lower():
                spoken = f"{spoken} {next_prompt}"
            return {"spoken": spoken, "tone": tone or "neutral"}
    except (LLMError, ValueError, TypeError) as exc:
        logger.warning("Coach bridge fell back: %s", exc)
    return {"spoken": fallback, "tone": "encouraging" if unsure or score >= 3.0 else "neutral"}
