
"""Run the offline retrieval benchmark against a JSON dataset."""

import argparse
import json
from pathlib import Path

from app.retrieval.benchmark import EvaluationCase, evaluate_retriever
from app.retrieval.service import TextChunk


def load_dataset(path: Path):
    """Load and validate the basic structure of a benchmark dataset."""
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if data.get("dataset_type") != "synthetic_test_fixture":
        raise ValueError(
            "This runner currently accepts only explicitly synthetic datasets."
        )

    if not isinstance(data.get("cases"), list):
        raise ValueError("'cases' must be a JSON array")
    if not isinstance(data.get("chunks"), list):
        raise ValueError("'chunks' must be a JSON array")

    chunks = [
        TextChunk(
            chunk_id=item["chunk_id"],
            text=item["text"],
            start_offset=0,
            end_offset=len(item["text"]),
        )
        for item in data["chunks"]
    ]

    cases = [
        EvaluationCase(
            query=item["query"],
            relevant_chunk_ids=frozenset(item["relevant_chunk_ids"]),
        )
        for item in data["cases"]
    ]

    return data, cases, chunks


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the offline synthetic retrieval benchmark."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("backend/evaluation/retrieval_cases.json"),
        help="Path to the synthetic evaluation dataset.",
    )
    parser.add_argument("--k", type=int, default=2)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    data, cases, chunks = load_dataset(args.dataset)
    report = evaluate_retriever(cases, chunks, k=args.k, limit=args.limit)

    print(f"Dataset: {args.dataset}")
    print(f"Type: {data['dataset_type']}")
    print(f"Description: {data.get('description', '')}")
    print(f"Queries: {report.query_count}")
    print(f"Recall@{report.k}: {report.recall_at_k:.3f}")
    print(f"MRR: {report.mean_reciprocal_rank:.3f}")
    print("\nPer-query results:")

    for result in report.results:
        print(f"- Query: {result.query}")
        print(f"  Retrieved IDs: {list(result.retrieved_chunk_ids)}")
        print(f"  Recall@{report.k}: {result.recall:.3f}")
        print(f"  Reciprocal rank: {result.reciprocal_rank:.3f}")


if __name__ == "__main__":
    main()
