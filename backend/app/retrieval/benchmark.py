
"""Offline benchmark for keyword-based scheme retrieval."""

from dataclasses import dataclass
from collections.abc import Sequence

from app.retrieval.evaluation import recall_at_k, mean_reciprocal_rank
from app.retrieval.service import TextChunk, retrieve_chunks


@dataclass(frozen=True)
class EvaluationCase:
    """A query and its manually judged relevant chunk IDs."""

    query: str
    relevant_chunk_ids: frozenset[int]


@dataclass(frozen=True)
class QueryEvaluation:
    """Evaluation details for one query."""

    query: str
    retrieved_chunk_ids: tuple[int, ...]
    recall: float
    reciprocal_rank: float


@dataclass(frozen=True)
class BenchmarkReport:
    """Aggregate metrics and per-query benchmark results."""

    recall_at_k: float
    mean_reciprocal_rank: float
    k: int
    query_count: int
    results: tuple[QueryEvaluation, ...]



def evaluate_retriever(
    cases: Sequence[EvaluationCase],
    chunks: list[TextChunk],
    *,
    k: int = 5,
    limit: int = 10,
) -> BenchmarkReport:
    """Evaluate keyword retrieval against manually judged relevant IDs.

    This function is offline: it does not access a database or call an API.
    """
    if k < 1:
        raise ValueError("k must be at least 1")
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if not cases:
        raise ValueError("at least one evaluation case is required")

    available_chunk_ids = {chunk.chunk_id for chunk in chunks}

    for case in cases:
        unknown_ids = case.relevant_chunk_ids - available_chunk_ids
        if unknown_ids:
            raise ValueError(
                f"query {case.query!r} references unknown chunk IDs: "
                f"{sorted(unknown_ids)}"
            )

    query_results: list[QueryEvaluation] = []

    for case in cases:
        retrieved = retrieve_chunks(case.query, chunks, limit=limit)
        retrieved_ids = tuple(item.chunk.chunk_id for item in retrieved)

        query_results.append(
            QueryEvaluation(
                query=case.query,
                retrieved_chunk_ids=retrieved_ids,
                recall=(
                    recall_at_k(set(case.relevant_chunk_ids), retrieved_ids, k=k)
                    if case.relevant_chunk_ids
                    else 0.0
                ),
                reciprocal_rank=_reciprocal_rank(
                    case.relevant_chunk_ids,
                    retrieved_ids,
                ),
            )
        )

    return BenchmarkReport(
        recall_at_k=sum(item.recall for item in query_results)
        / len(query_results),
        mean_reciprocal_rank=mean_reciprocal_rank(
            [set(case.relevant_chunk_ids) for case in cases],
            [item.retrieved_chunk_ids for item in query_results],
        ),
        k=k,
        query_count=len(query_results),
        results=tuple(query_results),
    )



def _reciprocal_rank(
    relevant_ids: frozenset[int],
    retrieved_ids: Sequence[int],
) -> float:
    """Return the reciprocal rank of the first relevant result."""
    for rank, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in relevant_ids:
            return 1.0 / rank
    return 0.0
