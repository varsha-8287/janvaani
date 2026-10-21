
"""Offline evaluation metrics for information retrieval."""

from collections.abc import Hashable, Sequence


def recall_at_k(
    relevant_ids: set[Hashable],
    retrieved_ids: Sequence[Hashable],
    *,
    k: int = 5,
) -> float:
    """Return the fraction of relevant items found in the top k results.

    Duplicate retrieved IDs count only once. Relevant IDs must be non-empty
    so the metric has a meaningful denominator.
    """
    if k < 1:
        raise ValueError("k must be at least 1")
    if not relevant_ids:
        raise ValueError("relevant_ids must not be empty")

    retrieved_top_k = set(retrieved_ids[:k])
    found = relevant_ids.intersection(retrieved_top_k)

    return len(found) / len(relevant_ids)


def mean_reciprocal_rank(
    relevant_ids_by_query: Sequence[set[Hashable]],
    retrieved_ids_by_query: Sequence[Sequence[Hashable]],
) -> float:
    """Return mean reciprocal rank across queries.

    A query contributes 1/rank for its first relevant result, or zero if
    no relevant result is retrieved. Empty relevance sets contribute zero.
    An empty collection of queries returns 0.0.
    """
    if len(relevant_ids_by_query) != len(retrieved_ids_by_query):
        raise ValueError(
            "relevance judgments and retrieved results must have equal lengths"
        )

    if not relevant_ids_by_query:
        return 0.0

    reciprocal_ranks: list[float] = []

    for relevant_ids, retrieved_ids in zip(
        relevant_ids_by_query,
        retrieved_ids_by_query,
    ):
        reciprocal_rank = 0.0

        for rank, item_id in enumerate(retrieved_ids, start=1):
            if item_id in relevant_ids:
                reciprocal_rank = 1.0 / rank
                break

        reciprocal_ranks.append(reciprocal_rank)

    return sum(reciprocal_ranks) / len(reciprocal_ranks)
