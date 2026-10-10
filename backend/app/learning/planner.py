from __future__ import annotations

from typing import Any

VERIFIED_RESOURCES: dict[str, dict[str, str]] = {
    "python": {
        "url": "https://docs.python.org/3/tutorial/",
        "label": "Python tutorial (docs.python.org)",
    },
    "sql": {
        "url": "https://www.postgresql.org/docs/current/tutorial.html",
        "label": "PostgreSQL tutorial",
    },
    "supervised_learning": {
        "url": "https://scikit-learn.org/stable/supervised_learning.html",
        "label": "scikit-learn supervised learning guide",
    },
    "transformers": {
        "url": "https://huggingface.co/docs/transformers/index",
        "label": "Hugging Face Transformers documentation",
    },
    "retrieval augmented generation": {
        "url": "https://arxiv.org/abs/2005.11401",
        "label": "Lewis et al., Retrieval-Augmented Generation (arXiv:2005.11401)",
    },
    "hybrid_search": {
        "url": "https://arxiv.org/abs/2005.11401",
        "label": "RAG paper plus BM25/RRF implementation notes",
    },
    "langgraph": {
        "url": "https://langchain-ai.github.io/langgraph/",
        "label": "LangGraph documentation",
    },
    "state_machines": {
        "url": "https://langchain-ai.github.io/langgraph/",
        "label": "LangGraph documentation",
    },
}


def plan_from_gaps(gaps: list[dict[str, Any]], *, target_role: str) -> dict[str, Any]:
    tasks: list[dict[str, Any]] = []
    for gap in gaps:
        skill = gap["skill"]
        resource = VERIFIED_RESOURCES.get(skill)
        search = None if resource else f"site:docs.python.org OR site:scikit-learn.org {skill} {target_role}"
        priority = "high" if gap.get("severity") == "high" or gap.get("job_relevance") == "high" else "medium"
        tasks.append(
            {
                "skill": skill,
                "why_it_matters": (
                    f"{skill} appeared as a gap for a {target_role} interview. "
                    f"Evidence: {gap.get('evidence')}"
                ),
                "priority": priority,
                "recommended_reading": resource["url"] if resource else None,
                "search_suggestion": search,
                "practice_question": f"Teach {skill} as if you were answering a mid-level interview, with one production example.",
                "coding_exercise": f"Write a small, tested example that demonstrates {skill}.",
                "expected_outcome": f"Reassess by answering a fresh {skill} question with explicit concepts and a limitation.",
                "reassessment_criteria": "Cover previously missing concepts and include one concrete constraint or metric.",
                "status": "unresolved",
            }
        )
    tasks.sort(key=lambda item: 0 if item["priority"] == "high" else 1)
    return {
        "summary": f"{len(tasks)} prioritized tasks generated from current gaps.",
        "tasks": tasks,
    }
