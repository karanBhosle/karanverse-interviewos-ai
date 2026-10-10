from io import BytesIO

import pytest
from docx import Document
from pypdf import PdfWriter

from app.resume.extractor import structure_resume
from app.resume.ontology import evidence_kind, normalize_skill
from app.resume.parser import ExtractedDocument, ExtractedPage, extract_text, sniff_kind
from app.job_matching.extractor import extract_requirements
from app.job_matching.matcher import match_requirements


def _pdf_bytes(text: str) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buffer = BytesIO()
    writer.write(buffer)
    # pypdf blank pages have no text; use extractor fixtures for structured tests
    return buffer.getvalue()


def _docx_bytes(paragraphs: list[str]) -> bytes:
    document = Document()
    for line in paragraphs:
        document.add_paragraph(line)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_normalize_skill_aliases():
    assert normalize_skill("PyTorch") == "pytorch"
    assert normalize_skill("RAG") == "retrieval augmented generation"
    assert normalize_skill("k8s") == "kubernetes"


def test_evidence_kind_distinguishes_keywords_from_demonstration():
    assert evidence_kind("Skills: Python, SQL") == "keyword_presence"
    assert evidence_kind("Built a FastAPI service that reduced latency 30%") == "demonstrated"


def test_sniff_rejects_executables():
    from app.core.errors import ValidationAppError

    with pytest.raises(ValidationAppError):
        sniff_kind("malware.exe", "application/octet-stream")


def test_sniff_accepts_plain_text():
    assert sniff_kind("resume.txt", "text/plain") == "text"


def test_plain_text_extraction():
    extracted = extract_text(b"Karan Bhosle\nSkills\nPython, SQL", "text")
    assert "Python" in extracted.text
    structured = structure_resume(extracted)
    assert "python" in {item["skill_normalized"] for item in structured["skills"]}


def test_docx_extraction_and_missing_sections():
    data = _docx_bytes(
        [
            "Karan Bhosle",
            "Skills",
            "Python, SQL, RAG, LangGraph",
            "Experience",
            "Data Scientist – ExampleCo – 2023-2025",
            "- Implemented a hybrid retrieval service and improved recall 12%",
        ]
    )
    extracted = extract_text(data, "docx")
    structured = structure_resume(extracted)
    skills = {item["skill_normalized"]: item["evidence_kind"] for item in structured["skills"]}
    assert "python" in skills
    assert structured["roles"]
    assert any(item["has_metric"] for item in structured["achievements"])


def test_invalid_pdf_raises():
    from app.core.errors import ValidationAppError

    with pytest.raises(ValidationAppError):
        extract_text(b"not a pdf", "pdf")


def test_job_requirement_mapping():
    jd = """
    Senior ML Engineer
    Requirements:
    - Strong Python experience
    - Must have retrieval augmented generation experience
    - Preferred LangGraph or agentic workflows
    """
    requirements = extract_requirements(jd)
    skills = {item["skill"] for item in requirements}
    assert "python" in skills
    assert "retrieval augmented generation" in skills
    evidence = [
        {
            "skill_normalized": "python",
            "evidence_text": "Implemented a FastAPI scoring service",
            "source_section": "experience",
            "source_page": 1,
            "evidence_kind": "demonstrated",
        }
    ]
    result = match_requirements(requirements, evidence)
    assert 0 <= result["alignment_score"] <= 100
    assert "not a probability" in result["score_explanation"].lower() or "not a probability" in result["score_explanation"]
    statuses = {item["matching_status"] for item in result["items"]}
    assert "strong" in statuses
    assert "missing" in statuses


def test_blank_pdf_is_not_executed_and_has_no_text():
    data = _pdf_bytes("ignored")
    extracted = extract_text(data, "pdf")
    assert extracted.text == ""
