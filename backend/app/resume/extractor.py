from __future__ import annotations

import re
from typing import Any

from app.resume.ontology import SECTION_HEADERS, evidence_kind, normalize_skill
from app.resume.parser import ExtractedDocument

SKILL_SPLIT = re.compile(r"[,;/|•·\n]+")
ROLE_LINE = re.compile(
    r"^(?P<title>[A-Z][\w /&-]{2,80})\s+[–\-—@]\s+(?P<org>.+?)(?:\s+[–\-—]\s+(?P<dates>.+))?$",
    re.M,
)
METRIC_LINE = re.compile(r"(\d+(?:\.\d+)?\s?%|\b(?:auc|f1|recall|precision|latency|throughput)\b)", re.I)
BULLET = re.compile(r"^\s*(?:[-*•]|\d+\.)\s+(?P<text>.+)$", re.M)


def _detect_section(line: str) -> str | None:
    cleaned = line.strip().lower().rstrip(":")
    for section, aliases in SECTION_HEADERS.items():
        if cleaned in aliases:
            return section
    return None


def split_sections(text: str) -> dict[str, list[tuple[int, str]]]:
    sections: dict[str, list[tuple[int, str]]] = {"preamble": []}
    current = "preamble"
    page = 1
    for raw_line in text.splitlines():
        if raw_line.strip().startswith("--- page "):
            try:
                page = int(raw_line.split()[2])
            except (IndexError, ValueError):
                page = page
            continue
        section = _detect_section(raw_line)
        if section:
            current = section
            sections.setdefault(current, [])
            continue
        if raw_line.strip():
            sections.setdefault(current, []).append((page, raw_line.strip()))
    return sections


def extract_skills(sections: dict[str, list[tuple[int, str]]]) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    skill_lines = sections.get("skills", [])
    other_lines = [item for key, rows in sections.items() if key != "skills" for item in rows]
    for page, line in skill_lines:
        for token in SKILL_SPLIT.split(line):
            token = token.strip(" -•*")
            if 1 < len(token) < 40 and not token.isdigit():
                normalized = normalize_skill(token)
                found.setdefault(
                    normalized,
                    {
                        "skill_raw": token,
                        "skill_normalized": normalized,
                        "evidence_text": line,
                        "source_section": "skills",
                        "source_page": page,
                        "evidence_kind": "keyword_presence",
                    },
                )
    for page, line in other_lines:
        kind = evidence_kind(line)
        if kind != "demonstrated":
            continue
        for token in SKILL_SPLIT.split(line):
            token = token.strip()
            if not token or len(token) > 32:
                continue
            normalized = normalize_skill(token)
            if normalized in found and found[normalized]["evidence_kind"] == "keyword_presence":
                found[normalized] = {
                    **found[normalized],
                    "evidence_text": line,
                    "source_section": "experience",
                    "source_page": page,
                    "evidence_kind": "demonstrated",
                }
        # also attach demonstration to any already-known skill mentioned in the line
        lowered = line.lower()
        for skill, record in list(found.items()):
            if skill in lowered and record["evidence_kind"] == "keyword_presence":
                found[skill] = {
                    **record,
                    "evidence_text": line,
                    "source_section": "experience",
                    "source_page": page,
                    "evidence_kind": "demonstrated",
                }
    return list(found.values())


def extract_roles(sections: dict[str, list[tuple[int, str]]]) -> list[dict[str, Any]]:
    roles: list[dict[str, Any]] = []
    for page, line in sections.get("experience", []):
        match = ROLE_LINE.match(line)
        if match:
            roles.append(
                {
                    "title": match.group("title").strip(),
                    "organization": match.group("org").strip(),
                    "dates": (match.group("dates") or "").strip(),
                    "source_section": "experience",
                    "source_page": page,
                    "provenance": "resume_fact",
                }
            )
    return roles


def extract_projects(sections: dict[str, list[tuple[int, str]]]) -> list[dict[str, Any]]:
    projects: list[dict[str, Any]] = []
    buffer: dict[str, Any] | None = None
    for page, line in sections.get("projects", []):
        if not line.startswith(("-", "*", "•")) and len(line) < 120:
            if buffer:
                projects.append(buffer)
            buffer = {
                "name": line,
                "details": [],
                "source_section": "projects",
                "source_page": page,
                "provenance": "resume_fact",
            }
        elif buffer:
            buffer["details"].append(line.lstrip("-*• ").strip())
    if buffer:
        projects.append(buffer)
    return projects


def extract_achievements(sections: dict[str, list[tuple[int, str]]]) -> list[dict[str, Any]]:
    achievements: list[dict[str, Any]] = []
    sources = sections.get("achievements", []) + sections.get("experience", [])
    for page, line in sources:
        if METRIC_LINE.search(line) or evidence_kind(line) == "demonstrated":
            achievements.append(
                {
                    "text": line.lstrip("-*• ").strip(),
                    "has_metric": bool(METRIC_LINE.search(line)),
                    "source_section": "experience",
                    "source_page": page,
                    "provenance": "resume_fact",
                }
            )
    return achievements[:20]


def structure_resume(document: ExtractedDocument) -> dict[str, Any]:
    page_prefixed = []
    for page in document.pages:
        page_prefixed.append(f"--- page {page.page}")
        page_prefixed.append(page.text)
    text = "\n".join(page_prefixed) if document.pages else document.text
    sections = split_sections(text)
    skills = extract_skills(sections)
    return {
        "provenance": "deterministic_extraction",
        "extraction_method": document.method,
        "ocr_used": document.ocr_used,
        "skills": skills,
        "roles": extract_roles(sections),
        "projects": extract_projects(sections),
        "achievements": extract_achievements(sections),
        "technologies": sorted({item["skill_normalized"] for item in skills}),
        "section_coverage": {key: bool(value) for key, value in sections.items()},
        "warnings": _warnings(sections, skills),
    }


def _warnings(sections: dict[str, list[tuple[int, str]]], skills: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    if not sections.get("experience"):
        warnings.append("No experience section was detected.")
    if not sections.get("skills") and not skills:
        warnings.append("No skills section was detected.")
    keyword_only = [s for s in skills if s["evidence_kind"] == "keyword_presence"]
    if keyword_only:
        warnings.append(
            f"{len(keyword_only)} skills appear only as keywords and are not treated as demonstrated evidence."
        )
    return warnings
