from __future__ import annotations

import json
import logging
import re

from app.interview.context import job_touchpoints, resume_touchpoints
from app.interview.speech_lexicon import correct_transcript
from app.services.llm import CompatibleLLMProvider, LLMError, parse_json_object

logger = logging.getLogger(__name__)

UNSURE_PATTERN = re.compile(
    r"\b("
    r"i don'?t know|i do not know|no idea|not sure|no clue|"
    r"can'?t answer|cannot answer|don'?t remember|do not remember|"
    r"not familiar|never (?:done|used|worked|built)|no experience|"
    r"skip(?: the| this| that)?(?: question)?|pass|"
    r"next (?:question|one)|move on|let'?s skip|can we skip|"
    r"i'?m done|i am done|that'?s all|nothing|cannot say"
    r")\b",
    re.IGNORECASE,
)


CLOSING_PATTERN = re.compile(
    r"^(thanks|thank you|thanks a lot|thank you so much|bye|goodbye|that's it|thats it)[.! ]*$",
    re.IGNORECASE,
)


def looks_closing(answer: str) -> bool:
    text = " ".join((answer or "").lower().split())
    return bool(text) and bool(CLOSING_PATTERN.match(text))


def looks_unsure(answer: str) -> bool:
    text = " ".join((answer or "").lower().split())
    if not text:
        return True
    if UNSURE_PATTERN.search(text):
        return True
    words = text.split()
    if len(words) <= 4 and any(
        word in text for word in ("know", "idea", "skip", "pass", "sure", "next", "idk")
    ):
        return True
    return False


def fallback_bridge(
    *,
    candidate: str,
    unsure: bool,
    score: float,
    has_next: bool,
    next_prompt: str | None = None,
) -> str:
    name = candidate or "there"
    if not has_next:
        return f"Thanks {name}, that gives me enough to work with. Let me wrap the interview here."
    follow = (next_prompt or "").strip()
    if unsure:
        lead = f"That's completely fine, {name}. We can leave that one and keep talking."
    elif score >= 3.4:
        lead = f"Great to hear, {name}. I like how you put that."
    elif score >= 2.0:
        lead = f"Thanks {name}, I have that. Let's keep this as a conversation."
    else:
        lead = f"Appreciate you sharing that, {name}."
    return f"{lead} {follow}".strip() if follow else f"{lead} Let's move to the next question."


def _context_brief(resume_summary: dict | None, job_alignment: dict | None, target_role: str) -> dict:
    resume = resume_touchpoints(resume_summary)
    job = job_touchpoints(job_alignment)
    return {
        "resume_skills": resume["skills"][:6],
        "resume_projects": resume["projects"][:3],
        "job_title": job["title"] if job["title"] != "this role" else target_role,
        "job_needs": [item["skill"] for item in job["requirements"][:6]] or job["missing"][:6],
    }


async def spoken_bridge(
    *,
    candidate: str,
    question: str,
    answer: str,
    score: float,
    next_prompt: str | None,
    resume_summary: dict | None = None,
    job_alignment: dict | None = None,
    target_role: str = "",
    provider: CompatibleLLMProvider | None = None,
) -> dict[str, str]:
    unsure = looks_unsure(answer)
    has_next = bool(next_prompt)
    fallback = fallback_bridge(
        candidate=candidate, unsure=unsure, score=score, has_next=has_next, next_prompt=next_prompt
    )
    if next_prompt:
        return {"spoken": fallback, "tone": "encouraging" if score >= 3.0 or unsure else "neutral"}
    llm = provider or CompatibleLLMProvider()
    if not getattr(llm, "available", False):
        return {"spoken": fallback, "tone": "encouraging" if score >= 3.0 or unsure else "neutral"}
    brief = _context_brief(resume_summary, job_alignment, target_role)
    system = (
        "You are Neerja, running a live two-way interview in Indian English. "
        "Reply with JSON only: {\"spoken\": string, \"tone\": \"encouraging\"|\"neutral\"|\"probing\"}. "
        "spoken is the next thing you say out loud, 3 to 5 short sentences. "
        "This is a conversation, not a quiz: quote or paraphrase one thing they just said, "
        "then ask exactly one next question. "
        "Ground that next question in their resume or the job description when you can. "
        "If they cannot answer, do not probe, do not teach, and do not stay on the same topic — "
        "acknowledge it warmly and ask the next_question. "
        "If they answered, react, then move to next_question in your own words. "
        "Ask only one question. Do not stack a follow-up and a new question. "
        "If there is no next_question, close warmly. "
        "Do not mention numeric scores, hiring, or personality. Do not say question bank."
    )
    user = json.dumps(
        {
            "candidate_name": candidate,
            "asked_question": question,
            "candidate_answer": answer,
            "coaching_score_0_to_5": score,
            "candidate_was_unsure": unsure,
            "next_question": next_prompt,
            "resume_and_job": brief,
        }
    )
    try:
        result = await llm.complete_json(system=system, user=user, schema_name="coach_bridge")
        payload = parse_json_object(result.content)
        spoken = str(payload.get("spoken") or "").strip()
        tone = str(payload.get("tone") or "neutral").strip()
        if spoken:
            if unsure and next_prompt and "?" not in spoken and next_prompt[:24].lower() not in spoken.lower():
                spoken = f"{spoken} {next_prompt}"
            elif next_prompt and "?" not in spoken and next_prompt[:32].lower() not in spoken.lower():
                spoken = f"{spoken} {next_prompt}"
            return {"spoken": spoken, "tone": tone or "neutral"}
    except (LLMError, ValueError, TypeError) as exc:
        logger.warning("Coach bridge fell back: %s", exc)
    return {"spoken": fallback, "tone": "encouraging" if unsure or score >= 3.0 else "neutral"}


_STOP = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "have",
    "been",
    "used",
    "use",
    "using",
    "was",
    "were",
    "are",
    "had",
    "has",
    "last",
    "year",
    "into",
    "then",
}


def _same_meaning(exact: str, sentence: str) -> bool:
    left = {item for item in re.findall(r"[a-z0-9]+", exact.lower()) if len(item) > 2} - _STOP
    right = {item for item in re.findall(r"[a-z0-9]+", sentence.lower()) if len(item) > 2} - _STOP
    if not left or not right:
        return False
    if len(right) > len(left) * 2 + 3:
        return False
    overlap = len(left & right)
    return overlap / len(left) >= 0.4


async def refine_spoken_transcript(
    text: str,
    *,
    terms: list[str],
    question: str = "",
    resume_summary: dict | None = None,
    job_alignment: dict | None = None,
    provider: CompatibleLLMProvider | None = None,
) -> str:
    exact = (text or "").strip()
    if not exact:
        return exact
    fallback = correct_transcript(exact, terms)
    llm = provider or CompatibleLLMProvider()
    if provider is None and not getattr(llm, "available", False):
        return fallback
    brief = _context_brief(resume_summary, job_alignment, "")
    system = (
        "The user already captured an exact speech transcript. "
        "Regenerate that transcript into a clean spoken answer. "
        "Reply with JSON only: {\"sentence\": string}. "
        "Keep the same meaning and the same claims. "
        "Fix speech-to-text slips using known terms (for example Rak/rack -> RAG, pdfs -> PDFs). "
        "Do not add projects, skills, numbers, or facts that are not in the transcript. "
        "Do not answer the interview question for them. "
        "If they said they do not know, keep that. "
        "If you cannot improve it, return the exact transcript."
    )
    user = json.dumps(
        {
            "exact_transcript": exact,
            "known_terms": terms[:40],
            "asked_question": question,
            "resume_and_job": brief,
        }
    )
    try:
        result = await llm.complete_json(system=system, user=user, schema_name="speech_sentence_regen")
        payload = parse_json_object(result.content)
        sentence = str((payload or {}).get("sentence") or "").strip()
        if sentence and _same_meaning(exact, sentence):
            return sentence
    except (LLMError, ValueError, TypeError) as exc:
        logger.warning("Speech sentence regen fell back: %s", exc)
    return fallback
