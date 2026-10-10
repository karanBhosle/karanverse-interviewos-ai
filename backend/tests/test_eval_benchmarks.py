import json
from pathlib import Path

from app.evaluation.scoring import deterministic_evaluation
from app.interview.bank import get_question

GOLDEN = json.loads(Path(__file__).parent.joinpath("eval_benchmarks/goldenset.json").read_text())


def test_golden_set_score_direction_and_missing_concepts():
    for item in GOLDEN:
        question = get_question(item["question_key"])
        result = deterministic_evaluation(question, item["answer"])
        if item["human_score"] >= 70:
            assert result["weighted_score"] >= 50
        else:
            assert result["weighted_score"] < 70
        for concept in item["expected_missing"]:
            assert concept in result["payload"].missing_concepts
