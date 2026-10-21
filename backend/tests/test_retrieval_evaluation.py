
import pytest

from app.retrieval.evaluation import recall_at_k, mean_reciprocal_rank


def test_recall_at_k_finds_all_relevant_items():
    assert recall_at_k(
        {"a", "b"},
        ["a", "x", "b"],
        k=3,
    ) == 1.0


def test_recall_at_k_counts_only_top_k():
    assert recall_at_k(
        {"a", "b"},
        ["x", "a", "y", "b"],
        k=2,
    ) == 0.5


def test_recall_at_k_returns_zero_when_none_are_relevant():
    assert recall_at_k(
        {"a", "b"},
        ["x", "y"],
        k=2,
    ) == 0.0


def test_recall_at_k_does_not_double_count_duplicate_results():
    assert recall_at_k(
        {"a", "b"},
        ["a", "a", "x"],
        k=3,
    ) == 0.5


def test_recall_at_k_rejects_invalid_k():
    with pytest.raises(ValueError, match="k must be at least 1"):
        recall_at_k({"a"}, ["a"], k=0)


def test_recall_at_k_rejects_empty_relevance_judgments():
    with pytest.raises(ValueError, match="must not be empty"):
        recall_at_k(set(), ["a"], k=5)


def test_mrr_is_one_when_first_result_is_relevant():
    assert mean_reciprocal_rank(
        [{"a"}],
        [["a", "b", "c"]],
    ) == 1.0


def test_mrr_uses_rank_of_first_relevant_result():
    assert mean_reciprocal_rank(
        [{"a"}],
        [["x", "y", "a"]],
    ) == pytest.approx(1 / 3)


def test_mrr_averages_across_queries():
    assert mean_reciprocal_rank(
        [{"a"}, {"b"}, {"c"}],
        [
            ["a", "x"],
            ["x", "b"],
            ["x", "y"],
        ],
    ) == pytest.approx((1.0 + 0.5 + 0.0) / 3)


def test_mrr_returns_zero_for_empty_relevance_judgment():
    assert mean_reciprocal_rank(
        [set()],
        [["a", "b"]],
    ) == 0.0


def test_mrr_returns_zero_for_empty_query_collection():
    assert mean_reciprocal_rank([], []) == 0.0


def test_mrr_rejects_mismatched_query_counts():
    with pytest.raises(ValueError, match="equal lengths"):
        mean_reciprocal_rank(
            [{"a"}],
            [],
        )
