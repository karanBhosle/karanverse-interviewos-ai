from __future__ import annotations

import re
from typing import Any

from app.interview.context import job_touchpoints, resume_touchpoints
from app.resume.ontology import SKILL_ALIASES

WORD = re.compile(r"[A-Za-z][A-Za-z0-9+.#/-]*")

PROPER_CASE = {
    "python": "Python",
    "sql": "SQL",
    "pandas": "pandas",
    "docker": "Docker",
    "aws": "AWS",
    "gcp": "GCP",
    "azure": "Azure",
}

SHORT_FORMS = {
    "retrieval augmented generation": "RAG",
    "large language models": "LLMs",
    "generative ai": "GenAI",
    "natural language processing": "NLP",
    "langgraph": "LangGraph",
    "langchain": "LangChain",
    "langsmith": "LangSmith",
    "fastapi": "FastAPI",
    "postgresql": "PostgreSQL",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "numpy": "NumPy",
    "scikit-learn": "scikit-learn",
    "huggingface": "Hugging Face",
    "hugging face": "Hugging Face",
    "openai": "OpenAI",
    "pinecone": "Pinecone",
    "elasticsearch": "Elasticsearch",
    "kubernetes": "Kubernetes",
    "mongodb": "MongoDB",
    "ci/cd": "CI/CD",
    "mlops": "MLOps",
    "bm25": "BM25",
    "pgvector": "pgvector",
}

STT_ALIASES = {
    "rak": "RAG",
    "ragg": "RAG",
    "wrag": "RAG",
    "are ag": "RAG",
    "ar ag": "RAG",
    "rag": "RAG",
    "lang graph": "LangGraph",
    "langraft": "LangGraph",
    "land graph": "LangGraph",
    "lang grap": "LangGraph",
    "lang chain": "LangChain",
    "long chain": "LangChain",
    "pine cone": "Pinecone",
    "bm 25": "BM25",
    "bm twenty five": "BM25",
    "pie torch": "PyTorch",
    "py torch": "PyTorch",
    "tensor flow": "TensorFlow",
    "fast api": "FastAPI",
    "open ai": "OpenAI",
    "hugging face": "Hugging Face",
    "vector db": "vector database",
    "pg vector": "pgvector",
    "num pie": "NumPy",
    "num py": "NumPy",
    "numpi": "NumPy",
    "pan does": "pandas",
    "sci kit": "scikit-learn",
    "sci kit learn": "scikit-learn",
    "skill learn": "scikit-learn",
    "kube netes": "Kubernetes",
    "kubernettes": "Kubernetes",
    "post gre sql": "PostgreSQL",
    "post gres": "PostgreSQL",
    "mongo db": "MongoDB",
    "ml ops": "MLOps",
    "jen ai": "GenAI",
    "gen ai": "GenAI",
    "el el em": "LLM",
    "l l m": "LLM",
    "l l ms": "LLMs",
    "pdfs": "PDFs",
    "pdf": "PDF",
}

COMMON = {
    "the",
    "and",
    "for",
    "was",
    "with",
    "that",
    "this",
    "from",
    "have",
    "been",
    "they",
    "them",
    "then",
    "when",
    "what",
    "your",
    "our",
    "can",
    "will",
    "just",
    "like",
    "also",
    "used",
    "use",
    "using",
    "built",
    "build",
    "work",
    "worked",
    "project",
    "system",
    "data",
    "model",
    "models",
    "train",
    "training",
    "test",
    "team",
    "role",
    "job",
    "did",
    "had",
    "has",
    "are",
    "you",
    "she",
    "his",
    "her",
    "not",
    "but",
    "all",
    "any",
    "out",
    "how",
    "why",
    "who",
}

DOMAIN_CUES = {
    "retrieval",
    "retriever",
    "search",
    "generation",
    "embedding",
    "embeddings",
    "vector",
    "pipeline",
    "index",
    "chunk",
    "chunks",
    "prompt",
    "token",
    "tokens",
    "context",
    "augmented",
    "hybrid",
    "semantic",
    "similarity",
    "transformer",
    "inference",
    "dataset",
    "accuracy",
    "recall",
    "precision",
    "latency",
    "api",
    "model",
    "models",
    "fine",
    "tuning",
    "rerank",
    "database",
}

ENGLISH_FIXES = {
    "retrival": "retrieval",
    "retrievel": "retrieval",
    "retreival": "retrieval",
    "embedings": "embeddings",
    "embeding": "embedding",
    "embeded": "embedded",
    "pipelne": "pipeline",
    "pipelin": "pipeline",
    "databse": "database",
    "datbase": "database",
    "langauge": "language",
    "langugae": "language",
    "algoritm": "algorithm",
    "algorithim": "algorithm",
    "accuray": "accuracy",
    "accuarcy": "accuracy",
    "precison": "precision",
    "inferance": "inference",
    "deployement": "deployment",
    "architecure": "architecture",
    "architechture": "architecture",
    "knowlege": "knowledge",
    "knowldge": "knowledge",
    "experiance": "experience",
    "expereince": "experience",
    "performace": "performance",
    "optimizaton": "optimization",
    "evalution": "evaluation",
    "evaluaton": "evaluation",
    "orcestration": "orchestration",
    "orchesteration": "orchestration",
}

ENGLISH = COMMON | {
    "i",
    "me",
    "my",
    "we",
    "it",
    "its",
    "in",
    "on",
    "to",
    "of",
    "as",
    "if",
    "or",
    "so",
    "at",
    "by",
    "an",
    "be",
    "is",
    "am",
    "do",
    "up",
    "one",
    "two",
    "about",
    "after",
    "again",
    "already",
    "because",
    "before",
    "between",
    "both",
    "could",
    "each",
    "first",
    "here",
    "into",
    "more",
    "most",
    "next",
    "only",
    "other",
    "over",
    "same",
    "some",
    "such",
    "than",
    "their",
    "there",
    "these",
    "those",
    "through",
    "time",
    "under",
    "very",
    "where",
    "which",
    "while",
    "would",
    "answer",
    "asked",
    "baseline",
    "better",
    "change",
    "changed",
    "choice",
    "chose",
    "clear",
    "close",
    "company",
    "constraint",
    "could",
    "decided",
    "decision",
    "designed",
    "deployed",
    "during",
    "enough",
    "example",
    "experience",
    "first",
    "follow",
    "give",
    "given",
    "going",
    "good",
    "great",
    "help",
    "here",
    "implemented",
    "improved",
    "know",
    "later",
    "made",
    "make",
    "measure",
    "need",
    "needed",
    "owned",
    "part",
    "problem",
    "really",
    "reduced",
    "result",
    "same",
    "should",
    "something",
    "started",
    "still",
    "sure",
    "talk",
    "thing",
    "think",
    "tried",
    "want",
    "way",
    "well",
    "went",
    "worked",
    "would",
    "year",
    "years",
    "retrieval",
    "pipeline",
    "database",
    "language",
    "algorithm",
    "accuracy",
    "precision",
    "inference",
    "deployment",
    "architecture",
    "knowledge",
    "experience",
    "performance",
    "optimization",
    "evaluation",
    "orchestration",
    "embedding",
    "embeddings",
    "vector",
    "search",
    "generation",
    "context",
    "prompt",
    "index",
    "chunk",
    "hybrid",
    "semantic",
    "similarity",
    "transformer",
    "dataset",
    "recall",
    "latency",
    "service",
    "api",
    "rock",
    "rack",
    "table",
    "sat",
}

CORE_TERMS = (
    "RAG",
    "LangGraph",
    "LangChain",
    "FastAPI",
    "PyTorch",
    "TensorFlow",
    "NumPy",
    "pandas",
    "LLM",
    "LLMs",
    "GenAI",
    "Python",
    "SQL",
    "BM25",
    "OpenAI",
    "Hugging Face",
)


def _fold(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9+.#/\s]", " ", (value or "").lower()).split())


def _levenshtein(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    for i, a in enumerate(left, start=1):
        current = [i]
        for j, b in enumerate(right, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (a != b)))
        previous = current
    return previous[-1]


def _display(term: str) -> str:
    folded = _fold(term)
    if folded in SHORT_FORMS:
        return SHORT_FORMS[folded]
    if folded in PROPER_CASE:
        return PROPER_CASE[folded]
    if term.isupper() or any(ch.isupper() for ch in term[1:]):
        return term.strip()
    return term.strip()


def _add(bucket: dict[str, str], term: str) -> None:
    cleaned = " ".join((term or "").split())
    if len(cleaned) < 2 or len(cleaned) > 48:
        return
    if " " in cleaned and len(cleaned.split()) > 4:
        return
    display = _display(cleaned)
    key = _fold(display)
    current = bucket.get(key)
    if current is None or (current.islower() and not display.islower()):
        bucket[key] = display
    bucket[_fold(cleaned)] = bucket[key]


def build_speech_lexicon(
    resume_summary: dict[str, Any] | None = None,
    job_alignment: dict[str, Any] | None = None,
    extra: list[str] | None = None,
) -> list[str]:
    terms: dict[str, str] = {}
    for core in CORE_TERMS:
        _add(terms, core)
    resume = resume_touchpoints(resume_summary)
    job = job_touchpoints(job_alignment)
    for skill in resume.get("skills") or []:
        _add(terms, skill)
    for project in resume.get("projects") or []:
        name = str(project).split("—")[0].split("-")[0].strip()
        if 2 <= len(name) <= 40:
            _add(terms, name)
    for role in resume.get("roles") or []:
        for piece in re.split(r"\s+at\s+", str(role)):
            if 2 <= len(piece) <= 32:
                _add(terms, piece)
    for item in job.get("requirements") or []:
        _add(terms, str(item.get("skill") or ""))
    for skill in (job.get("overlap") or []) + (job.get("missing") or []):
        _add(terms, skill)
    if job.get("title") and job["title"] != "this role":
        _add(terms, str(job["title"]))
    for skill in (resume_summary or {}).get("technologies") or []:
        _add(terms, str(skill))
    for row in (resume_summary or {}).get("skills") or []:
        _add(terms, str(row.get("skill_normalized") or row.get("skill") or ""))
    for blob in extra or []:
        for match in WORD.finditer(str(blob)):
            token = match.group()
            if token.lower() in SKILL_ALIASES or token.lower() in SHORT_FORMS:
                _add(terms, token)
            elif token.isupper() and 2 <= len(token) <= 8:
                _add(terms, token)
    for alias, canon in SKILL_ALIASES.items():
        if _fold(canon) in terms or _fold(alias) in terms:
            _add(terms, SHORT_FORMS.get(canon, canon))
    seen: list[str] = []
    for display in terms.values():
        if display not in seen:
            seen.append(display)
    return seen[:80]


def _catalog(terms: list[str]) -> dict[str, str]:
    catalog: dict[str, str] = {}
    allowed = {_fold(term) for term in terms}
    for term in terms:
        catalog[_fold(term)] = term
    for alias, display in STT_ALIASES.items():
        if _fold(display) in allowed or display in terms:
            catalog[alias] = display
    for alias, canon in SKILL_ALIASES.items():
        target = SHORT_FORMS.get(canon) or catalog.get(_fold(canon))
        if target:
            catalog[_fold(alias)] = target
    return catalog


def _soundex(value: str) -> str:
    letters = re.sub(r"[^a-z]", "", (value or "").lower())
    if not letters:
        return ""
    codes = {
        "bfpv": "1",
        "cgjkqsxz": "2",
        "dt": "3",
        "l": "4",
        "mn": "5",
        "r": "6",
    }
    def code(char: str) -> str:
        for group, digit in codes.items():
            if char in group:
                return digit
        return ""

    key = letters[0].upper()
    previous = code(letters[0])
    for char in letters[1:]:
        digit = code(char)
        if digit and digit != previous:
            key += digit
        previous = digit
        if len(key) == 4:
            break
    return key.ljust(4, "0")


def _is_word(token: str, catalog: dict[str, str]) -> bool:
    folded = _fold(token)
    if folded in ENGLISH or folded in COMMON or folded in catalog:
        return True
    if folded.endswith("s") and folded[:-1] in ENGLISH:
        return True
    if folded.endswith("ed") and folded[:-2] in ENGLISH:
        return True
    if folded.endswith("ing") and folded[:-3] in ENGLISH:
        return True
    return False


def _unique_close(heard: str, options: list[str], limit: int) -> str | None:
    folded = _fold(heard)
    hits = [item for item in options if 0 < _levenshtein(folded, _fold(item)) <= limit]
    unique = list(dict.fromkeys(hits))
    return unique[0] if len(unique) == 1 else None


def _fuzzy(heard: str, catalog: dict[str, str]) -> str | None:
    folded = _fold(heard)
    if folded in catalog:
        return catalog[folded]
    if folded in COMMON or len(folded) < 3:
        return None
    best: tuple[int, str] | None = None
    for key, display in catalog.items():
        if " " in key or len(key) < 3:
            continue
        if key in COMMON:
            continue
        distance = _levenshtein(folded, key)
        limit = 1 if min(len(folded), len(key)) <= 5 else 2
        if 0 < distance <= limit and (best is None or distance < best[0]):
            best = (distance, display)
    return best[1] if best else None


def _neighbors(matches: list[re.Match[str]], index: int) -> set[str]:
    nearby: set[str] = set()
    for offset in (-2, -1, 1, 2):
        other = index + offset
        if 0 <= other < len(matches):
            nearby.add(_fold(matches[other].group()))
    return nearby


def _nlp_guess(phrase: str, catalog: dict[str, str], nearby: set[str]) -> str | None:
    folded = _fold(phrase)
    if folded in ENGLISH_FIXES:
        return ENGLISH_FIXES[folded]
    if folded in catalog:
        return catalog[folded]
    known = _is_word(phrase, catalog)
    domain = bool(nearby & DOMAIN_CUES)
    if known and not domain and folded in COMMON:
        return None
    sound = _soundex(folded)
    sound_hits = [
        display
        for key, display in catalog.items()
        if " " not in key and _soundex(key) == sound and _fold(display) != folded
    ]
    unique_sound = list(dict.fromkeys(sound_hits))
    if unique_sound and (not known or domain) and len(unique_sound) == 1:
        return unique_sound[0]
    if not known:
        close_term = _unique_close(phrase, list(catalog.values()), 1 if len(folded) <= 6 else 2)
        if close_term:
            return close_term
        if len(folded) >= 6:
            english_hit = _unique_close(phrase, list(ENGLISH | set(ENGLISH_FIXES.values())), 1)
            if english_hit:
                return english_hit
    if domain:
        close_term = _unique_close(phrase, list(catalog.values()), 1 if len(folded) <= 5 else 2)
        if close_term:
            return close_term
        return _fuzzy(phrase, catalog)
    if not known:
        return _fuzzy(phrase, catalog)
    return None


def correct_transcript(text: str, terms: list[str]) -> str:
    source = text or ""
    if not source.strip():
        return source
    catalog = _catalog(terms or list(CORE_TERMS))
    matches = list(WORD.finditer(source))
    if not matches:
        return source
    used: set[int] = set()
    swaps: list[tuple[int, int, str]] = []
    for width in (3, 2, 1):
        for index in range(len(matches) - width + 1):
            if any(item in used for item in range(index, index + width)):
                continue
            phrase = " ".join(matches[item].group() for item in range(index, index + width))
            display = catalog.get(_fold(phrase))
            if display is None and width == 1:
                display = _nlp_guess(phrase, catalog, _neighbors(matches, index))
            elif display is None:
                display = STT_ALIASES.get(_fold(phrase))
            if not display or display == phrase:
                continue
            swaps.append((matches[index].start(), matches[index + width - 1].end(), display))
            used.update(range(index, index + width))
    if not swaps:
        return source
    pieces: list[str] = []
    cursor = 0
    for start, end, display in sorted(swaps):
        pieces.append(source[cursor:start])
        pieces.append(display)
        cursor = end
    pieces.append(source[cursor:])
    return "".join(pieces)


def apply_confident_replacements(text: str, replacements: list[dict[str, Any]], minimum: float = 0.86) -> str:
    refined = text or ""
    for item in replacements or []:
        try:
            confidence = float(item.get("confidence") or 0)
        except (TypeError, ValueError):
            continue
        if confidence < minimum:
            continue
        source = str(item.get("from") or "").strip()
        target = str(item.get("to") or "").strip()
        if not source or not target or source == target:
            continue
        if len(target.split()) > len(source.split()) + 2:
            continue
        pattern = re.compile(rf"\b{re.escape(source)}\b", re.IGNORECASE)
        if not pattern.search(refined):
            continue
        refined = pattern.sub(target, refined, count=1)
    return refined
