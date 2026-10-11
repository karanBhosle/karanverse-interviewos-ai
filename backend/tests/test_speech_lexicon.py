from app.interview.speech_lexicon import apply_confident_replacements, build_speech_lexicon, correct_transcript


def test_rak_becomes_rag_from_resume_terms():
    terms = build_speech_lexicon(
        resume_summary={"technologies": ["retrieval augmented generation", "python", "langgraph"]},
        job_alignment={"title": "ML Engineer", "requirements": [{"skill": "RAG", "status": "strong"}]},
    )
    assert "RAG" in terms
    assert correct_transcript("I used Rak for retrieval in the research lab", terms) == (
        "I used RAG for retrieval in the research lab"
    )


def test_lang_graph_and_fast_api_are_corrected():
    terms = build_speech_lexicon(
        resume_summary={"technologies": ["LangGraph", "FastAPI"]},
        job_alignment={},
    )
    heard = "I wired lang graph behind a fast api service"
    assert correct_transcript(heard, terms) == "I wired LangGraph behind a FastAPI service"


def test_common_words_are_not_rewritten():
    terms = build_speech_lexicon(resume_summary={"technologies": ["python", "sql"]}, job_alignment={})
    spoken = "I can use Python and SQL when the team needs it"
    assert correct_transcript(spoken, terms) == spoken


def test_nlp_fixes_wrong_word_in_domain_context():
    terms = ["RAG", "Python"]
    assert correct_transcript("I used rack for retrieval", terms) == "I used RAG for retrieval"
    assert correct_transcript("The retrival pipeline improved recall", terms) == (
        "The retrieval pipeline improved recall"
    )


def test_nlp_leaves_plausible_english_alone():
    terms = ["RAG", "Python"]
    spoken = "I sat on a rock by the table"
    assert correct_transcript(spoken, terms) == spoken
    assert correct_transcript("I bought a rack yesterday", terms) == "I bought a rack yesterday"


def test_confident_replacements_ignore_weak_guesses():
    text = "I shared knowlege with the team"
    assert (
        apply_confident_replacements(
            text,
            [
                {"from": "knowlege", "to": "knowledge", "confidence": 0.94},
                {"from": "team", "to": "squad", "confidence": 0.4},
            ],
        )
        == "I shared knowledge with the team"
    )


def test_lexicon_includes_resume_and_job_skills():
    terms = build_speech_lexicon(
        resume_summary={"technologies": ["bm25", "hybrid search"], "projects": [{"name": "InterviewOS"}]},
        job_alignment={"title": "AI Engineer", "requirements": [{"skill": "LangGraph", "status": "missing"}]},
    )
    joined = " ".join(terms).lower()
    assert "rag" in joined or "bm25" in joined
    assert "langgraph" in joined
    assert "interviewos" in joined
