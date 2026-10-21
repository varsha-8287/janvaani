
import pytest

from app.retrieval.benchmark import EvaluationCase, evaluate_retriever
from app.retrieval.service import TextChunk


@pytest.fixture
def synthetic_chunks():
    """Synthetic test fixtures; not real government scheme information."""
    return [
        TextChunk(
            chunk_id=1,
            text="Scholarship assistance for eligible college students",
            start_offset=0,
            end_offset=52,
        ),
        TextChunk(
            chunk_id=2,
            text="Farmers can apply for agricultural equipment support",
            start_offset=0,
            end_offset=53,
        ),
        TextChunk(
            chunk_id=3,
            text="College scholarship applications require income proof",
            start_offset=0,
            end_offset=54,
        ),
    ]


def test_benchmark_reports_aggregate_and_per_query_metrics(synthetic_chunks):
    cases = [
        EvaluationCase("college scholarship", frozenset({1, 3})),
        EvaluationCase("farmers equipment", frozenset({2})),
    ]

    report = evaluate_retriever(cases, synthetic_chunks, k=2, limit=3)

    assert report.query_count == 2
    assert report.k == 2
    assert report.recall_at_k == pytest.approx(1.0)
    assert report.mean_reciprocal_rank == pytest.approx(1.0)
    assert len(report.results) == 2

    assert report.results[0].retrieved_chunk_ids[0] == 1
    assert report.results[0].recall == pytest.approx(1.0)
    assert report.results[0].reciprocal_rank == pytest.approx(1.0)

    assert report.results[1].retrieved_chunk_ids[0] == 2


def test_benchmark_reports_zero_when_nothing_matches(synthetic_chunks):
    cases = [
        EvaluationCase("unicorn spaceship", frozenset({99})),
    ]

    report = evaluate_retriever(cases, synthetic_chunks)

    assert report.recall_at_k == 0.0
    assert report.mean_reciprocal_rank == 0.0
    assert report.results[0].retrieved_chunk_ids == ()


def test_benchmark_rejects_empty_cases(synthetic_chunks):
    with pytest.raises(ValueError, match="at least one evaluation case"):
        evaluate_retriever([], synthetic_chunks)


def test_benchmark_rejects_empty_relevance_labels(synthetic_chunks):
    cases = [EvaluationCase("scholarship", frozenset())]

    with pytest.raises(ValueError, match="relevant chunk IDs"):
        evaluate_retriever(cases, synthetic_chunks)


@pytest.mark.parametrize(
    ("k", "limit", "message"),
    [
        (0, 5, "k must be at least 1"),
        (5, 0, "limit must be at least 1"),
    ],
)
def test_benchmark_rejects_invalid_limits(
    synthetic_chunks, k, limit, message
):
    cases = [EvaluationCase("scholarship", frozenset({1}))]

    with pytest.raises(ValueError, match=message):
        evaluate_retriever(cases, synthetic_chunks, k=k, limit=limit)
