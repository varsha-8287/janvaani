
import json

import pytest

from app.retrieval.run_benchmark import load_dataset


def write_dataset(tmp_path, data):
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def valid_dataset():
    return {
        "dataset_type": "synthetic_test_fixture",
        "description": "Test fixture",
        "cases": [
            {
                "query": "college scholarship",
                "relevant_chunk_ids": [1],
            }
        ],
        "chunks": [
            {
                "chunk_id": 1,
                "text": "Scholarship support for college students",
            }
        ],
    }


def test_load_dataset_accepts_valid_synthetic_fixture(tmp_path):
    path = write_dataset(tmp_path, valid_dataset())

    data, cases, chunks = load_dataset(path)

    assert data["dataset_type"] == "synthetic_test_fixture"
    assert len(cases) == 1
    assert cases[0].query == "college scholarship"
    assert cases[0].relevant_chunk_ids == frozenset({1})
    assert len(chunks) == 1
    assert chunks[0].chunk_id == 1


def test_load_dataset_rejects_non_synthetic_dataset(tmp_path):
    data = valid_dataset()
    data["dataset_type"] = "production"

    with pytest.raises(ValueError, match="synthetic"):
        load_dataset(write_dataset(tmp_path, data))


@pytest.mark.parametrize("field", ["cases", "chunks"])
def test_load_dataset_rejects_non_array_cases_or_chunks(tmp_path, field):
    data = valid_dataset()
    data[field] = {}

    with pytest.raises(ValueError, match=field):
        load_dataset(write_dataset(tmp_path, data))


def test_load_dataset_rejects_missing_case_fields(tmp_path):
    data = valid_dataset()
    data["cases"] = [{"query": "college scholarship"}]

    with pytest.raises((KeyError, TypeError, ValueError)):
        load_dataset(write_dataset(tmp_path, data))


def test_load_dataset_rejects_missing_chunk_fields(tmp_path):
    data = valid_dataset()
    data["chunks"] = [{"chunk_id": 1}]

    with pytest.raises((KeyError, TypeError, ValueError)):
        load_dataset(write_dataset(tmp_path, data))


def test_load_dataset_rejects_invalid_json(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text("{ invalid json", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        load_dataset(path)
