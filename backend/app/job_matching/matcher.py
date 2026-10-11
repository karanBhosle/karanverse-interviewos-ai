from __future__ import annotations

import re
from typing import Any

from app.retrieval.embeddings import EmbeddingEncoder, cosine
from app.resume.ontology import SKILL_ALIASES, evidence_kind, normalize_skill

TOKEN = re.compile(r"[a-z0-9+#]+")

STRENGTH_SCORES = {
    "demonstrated": 1.0,
    "keyword_presence": 0.72,
    "similar": 0.68,
    "missing": 0.12,
}

STATUS_FROM_STRENGTH = {
    "demonstrated": "strong",
    "keyword_presence": "partial",
    "similar": "partial",
    "missing": "missing",
}


def _tokens(text: str) -> list[str]:
    return TOKEN.findall((text or "").lower().replace("-", " ").replace("_", " "))


def _expand(tokens: list[str]) -> list[str]:
    extra: list[str] = []
    joined = " ".join(tokens)
    for width in (3, 2, 1):
        for index in range(len(tokens) - width + 1):
            phrase = " ".join(tokens[index : index + width])
            if phrase in SKILL_ALIASES:
                extra.extend(_tokens(SKILL_ALIASES[phrase]))
    for alias, canon in SKILL_ALIASES.items():
        if canon in joined or alias in joined:
            extra.extend(_tokens(alias))
            extra.extend(_tokens(canon))
    seen: list[str] = []
    for token in tokens + extra:
        if token not in seen:
            seen.append(token)
    return seen


def _alias_terms(skill: str) -> set[str]:
    canon = normalize_skill(skill)
    terms = {skill.lower(), canon}
    for alias, target in SKILL_ALIASES.items():
        if target == canon or alias == skill.lower() or target == skill.lower():
            terms.add(alias)
            terms.add(target)
    return {item for item in terms if item}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _passages(
    evidence_rows: list[dict[str, Any]],
    resume_summary: dict[str, Any] | None,
    resume_text: str | None,
) -> list[dict[str, Any]]:
    passages: list[dict[str, Any]] = []

    def add(text: str, source: str, kind: str | None = None) -> None:
        cleaned = " ".join((text or "").split())
        if len(cleaned) < 3:
            return
        passages.append(
            {
                "id": f"p{len(passages)}",
                "text": cleaned,
                "source": source,
                "kind": kind or evidence_kind(cleaned),
                "tokens": _expand(_tokens(cleaned)),
            }
        )

    for row in evidence_rows:
        add(
            f"{row.get('skill_normalized', '')}. {row.get('evidence_text', '')}",
            f"{row.get('source_section') or 'resume'} p.{row.get('source_page') or '?'}",
            row.get("evidence_kind"),
        )
    summary = resume_summary or {}
    for skill in summary.get("skills") or []:
        add(
            f"{skill.get('skill_normalized') or skill.get('skill_raw')}. {skill.get('evidence_text', '')}",
            f"{skill.get('source_section') or 'skills'} p.{skill.get('source_page') or '?'}",
            skill.get("evidence_kind"),
        )
    for project in summary.get("projects") or []:
        details = " ".join(str(item) for item in (project.get("details") or []))
        add(f"{project.get('name', '')}. {details}", "projects")
    for achievement in summary.get("achievements") or []:
        add(str(achievement.get("text") or ""), "achievements")
    for role in summary.get("roles") or []:
        add(f"{role.get('title', '')} {role.get('organization', '')}", "experience")
    if resume_text:
        for block in re.split(r"\n{2,}", resume_text):
            add(block, "resume_text")
    return [item for item in passages if item["tokens"]]


def _similarity_hit(query: str, passages: list[dict[str, Any]], encoder: EmbeddingEncoder) -> dict[str, Any] | None:
    if not passages or not query.strip():
        return None
    query_tokens = set(_expand(_tokens(query)))
    query_vec = encoder.encode([" ".join(sorted(query_tokens)) or query])[0]
    passage_vecs = encoder.encode([" ".join(item["tokens"]) for item in passages])
    best: dict[str, Any] | None = None
    for index, passage in enumerate(passages):
        dense = max(0.0, cosine(query_vec, passage_vecs[index]))
        overlap = _jaccard(query_tokens, set(passage["tokens"]))
        score = max(dense, overlap)
        if best is None or score > best["similarity_score"]:
            best = {
                **passage,
                "lexical_score": None,
                "similarity_score": round(score, 3),
            }
    return best


def _contains_skill(text: str, skill: str) -> bool:
    haystack = (text or "").lower()
    return any(re.search(rf"\b{re.escape(term)}\b", haystack) for term in _alias_terms(skill) if len(term) > 1)


def match_requirements(
    requirements: list[dict[str, Any]],
    evidence_rows: list[dict[str, Any]],
    resume_summary: dict[str, Any] | None = None,
    resume_text: str | None = None,
) -> dict[str, Any]:
    passages = _passages(evidence_rows, resume_summary, resume_text)
    encoder = EmbeddingEncoder()
    items: list[dict[str, Any]] = []
    weighted_total = 0.0
    weighted_earned = 0.0
    counts = {"strong": 0, "partial": 0, "missing": 0}

    for requirement in requirements:
        skill = requirement["skill"]
        query = f"{skill} {requirement.get('description') or ''} {' '.join(_alias_terms(skill))}"
        hit = _similarity_hit(query, passages, encoder)
        exact = next(
            (
                row
                for row in evidence_rows
                if normalize_skill(row.get("skill_normalized") or "") == normalize_skill(skill)
                or _contains_skill(row.get("skill_normalized") or "", skill)
            ),
            None,
        )
        similar = float((hit or {}).get("similarity_score") or 0.0)
        mentioned = bool(hit and _contains_skill(hit["text"], skill)) or exact is not None
        kind = (exact or hit or {}).get("kind") or "missing"
        if exact:
            kind = exact.get("evidence_kind") or kind
        if mentioned and kind == "demonstrated":
            strength, status = "demonstrated", "strong"
        elif similar >= 0.36 and kind == "demonstrated":
            strength, status = "demonstrated", "strong"
        elif mentioned or similar >= 0.18:
            strength, status = ("keyword_presence" if mentioned else "similar"), "partial"
        else:
            strength, status = "missing", "missing"
        weight = float(requirement.get("weight") or 1.0)
        item_score = STRENGTH_SCORES[strength]
        if status != "missing":
            item_score = max(item_score, min(1.0, 0.48 + similar))
        weighted_total += weight
        weighted_earned += weight * item_score
        counts[status] += 1
        evidence_text = (exact or {}).get("evidence_text") or (hit or {}).get("text")
        evidence_source = None
        if exact:
            evidence_source = f"{exact.get('source_section')} p.{exact.get('source_page')}"
        elif hit:
            evidence_source = hit.get("source")
        if evidence_source and status != "missing":
            evidence_source = f"{evidence_source} · similarity {similar:.2f}"
        items.append(
            {
                "requirement_key": requirement["requirement_key"],
                "skill": skill,
                "description": requirement["description"],
                "importance": requirement["importance"],
                "weight": weight,
                "evidence_found": evidence_text if status != "missing" else None,
                "evidence_source": evidence_source if status != "missing" else None,
                "evidence_strength": strength,
                "matching_status": status,
                "lexical_score": None,
                "similarity_score": similar,
                "match_method": "similarity_search",
                "follow_up_questions": _follow_ups(skill, status),
            }
        )

    score = round((weighted_earned / weighted_total) * 100, 1) if weighted_total else 0.0
    explanation = (
        "This score measures documented alignment between resume evidence and the selected "
        "job description using similarity search: embedding cosine plus token-set similarity "
        "over alias-expanded skills (for example RAG ↔ retrieval augmented generation). "
        "It is not a probability of being hired. Demonstrated project or outcome evidence "
        "is weighted more heavily than keyword presence."
    )
    return {
        "alignment_score": score,
        "score_explanation": explanation,
        "strong_count": counts["strong"],
        "partial_count": counts["partial"],
        "missing_count": counts["missing"],
        "items": items,
    }


def _follow_ups(skill: str, status: str) -> list[str]:
    if status == "missing":
        return [f"Describe a project where you would apply {skill} if you have not used it yet."]
    if status == "partial":
        return [f"Walk through a concrete implementation decision you made with {skill}."]
    return [f"What trade-offs did you accept when using {skill} in production?"]
