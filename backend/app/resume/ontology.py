"""Canonical skill names and aliases for DS/ML/AI interview prep."""

from __future__ import annotations

SKILL_ALIASES: dict[str, str] = {
    "python3": "python",
    "py": "python",
    "sklearn": "scikit-learn",
    "scikit learn": "scikit-learn",
    "tf": "tensorflow",
    "pytorch lightning": "pytorch",
    "torch": "pytorch",
    "np": "numpy",
    "pd": "pandas",
    "js": "javascript",
    "ts": "typescript",
    "postgres": "postgresql",
    "pg": "postgresql",
    "k8s": "kubernetes",
    "llm": "large language models",
    "llms": "large language models",
    "genai": "generative ai",
    "generative ai": "generative ai",
    "rag": "retrieval augmented generation",
    "retrieval-augmented generation": "retrieval augmented generation",
    "lang graph": "langgraph",
    "langchain": "langchain",
    "vector db": "vector databases",
    "vector database": "vector databases",
    "faiss": "vector databases",
    "pgvector": "vector databases",
    "pinecone": "vector databases",
    "mlops": "mlops",
    "ci/cd": "ci/cd",
    "cicd": "ci/cd",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "opencv": "computer vision",
    "xgboost": "gradient boosting",
    "lightgbm": "gradient boosting",
    "catboost": "gradient boosting",
    "sql": "sql",
    "rest": "rest apis",
    "fastapi": "fastapi",
    "django": "django",
    "flask": "flask",
    "aws": "aws",
    "gcp": "gcp",
    "azure": "azure",
    "docker": "docker",
    "airflow": "workflow orchestration",
    "prefect": "workflow orchestration",
    "spark": "apache spark",
    "pyspark": "apache spark",
    "dbt": "dbt",
    "feature store": "feature stores",
    "a/b testing": "experimentation",
    "ab testing": "experimentation",
    "statistics": "statistics",
    "bayesian": "bayesian methods",
    "deep learning": "deep learning",
    "transformers": "transformers",
    "huggingface": "transformers",
    "prompt engineering": "prompt engineering",
    "agents": "agentic ai",
    "agentic": "agentic ai",
    "system design": "system design",
    "microservices": "system design",
}

CANONICAL_SKILLS = sorted(set(SKILL_ALIASES.values()) | set(SKILL_ALIASES.keys()))

DEMONSTRATION_CUES = (
    "built",
    "implemented",
    "designed",
    "deployed",
    "reduced",
    "improved",
    "increased",
    "led",
    "owned",
    "migrated",
    "trained",
    "evaluated",
    "production",
    "latency",
    "accuracy",
    "recall",
    "precision",
    "auc",
    "f1",
    "%",
)

SECTION_HEADERS = {
    "experience": ("experience", "work experience", "employment", "professional experience"),
    "projects": ("projects", "selected projects", "personal projects"),
    "skills": ("skills", "technical skills", "technologies", "tech stack"),
    "education": ("education", "academic"),
    "achievements": ("achievements", "awards", "honors"),
}


def normalize_skill(raw: str) -> str:
    key = " ".join(raw.lower().replace("_", " ").replace("/", " ").split())
    key = key.replace(".", "")
    return SKILL_ALIASES.get(key, key)


def evidence_kind(text: str) -> str:
    lowered = text.lower()
    if any(cue in lowered for cue in DEMONSTRATION_CUES):
        return "demonstrated"
    return "keyword_presence"
