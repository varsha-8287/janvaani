
import pytest

from app.retrieval.service import chunk_text, retrieve_chunks, retrieve_trusted_chunks

def test_chunk_text_returns_empty_for_blank_text():
    assert chunk_text("   ") == []


def test_chunk_text_preserves_all_text_content():
    text = "Janvaani helps people discover government schemes."
    chunks = chunk_text(text, chunk_size=20, overlap=5)

    assert chunks
    assert chunks[0].text.startswith("Janvaani")
    assert chunks[-1].text.endswith("schemes.")


def test_chunk_text_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_text("some text", chunk_size=10, overlap=10)


def test_retrieve_chunks_ranks_matching_text_first():
    chunks = chunk_text(
        "Education scholarship for eligible students. "
        "Agriculture support for farmers. "
        "Scholarship assistance for college students.",
        chunk_size=80,
        overlap=0,
    )

    results = retrieve_chunks("scholarship students", chunks)

    assert results
    assert "scholarship" in results[0].chunk.text.casefold()


def test_retrieve_chunks_returns_empty_for_unrelated_query():
    chunks = chunk_text("Scholarship support for students.")

    assert retrieve_chunks("spacecraft astronomy", chunks) == []

def test_trusted_retrieval_excludes_pending_sources():
    chunks = chunk_text(
        "Scholarship for eligible students.",
        source_url="https://example.gov.in/scholarship",
        source_review_status="pending",
        scheme_review_status="approved",
    )

    assert retrieve_trusted_chunks("scholarship", chunks) == []


def test_trusted_retrieval_excludes_unapproved_scheme_versions():
    chunks = chunk_text(
        "Scholarship for eligible students.",
        source_url="https://example.gov.in/scholarship",
        source_review_status="verified",
        scheme_review_status="pending_review",
    )

    assert retrieve_trusted_chunks("scholarship", chunks) == []


def test_trusted_retrieval_returns_verified_approved_evidence():
    chunks = chunk_text(
        "Scholarship for eligible students.",
        source_url="https://example.gov.in/scholarship",
        source_review_status="verified",
        scheme_review_status="approved",
    )

    results = retrieve_trusted_chunks("scholarship", chunks)

    assert len(results) == 1
    assert results[0].chunk.source_url == (
        "https://example.gov.in/scholarship"
    )


def test_trusted_retrieval_excludes_missing_source_url():
    chunks = chunk_text(
        "Scholarship for eligible students.",
        source_review_status="verified",
        scheme_review_status="approved",
    )

    assert retrieve_trusted_chunks("scholarship", chunks) == []


def test_trusted_retrieval_excludes_invalid_url_scheme():
    chunks = chunk_text(
        "Scholarship for eligible students.",
        source_url="javascript:alert(1)",
        source_review_status="verified",
        scheme_review_status="approved",
    )

    assert retrieve_trusted_chunks("scholarship", chunks) == []


def test_retrieve_chunks_rejects_invalid_limit():
    chunks = chunk_text("Scholarship support for students.")

    with pytest.raises(ValueError):
        retrieve_chunks("scholarship", chunks, limit=0)
