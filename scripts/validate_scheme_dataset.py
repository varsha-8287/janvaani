from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError:
    print(
        "Missing dependency: jsonschema. Install it with "
        "'python -m pip install jsonschema'",
        file=sys.stderr,
    )
    raise SystemExit(2)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate Janvaani scheme JSON records locally. "
            "This tool never writes to the database or approves records."
        )
    )
    parser.add_argument("--input", required=True, help="JSON file or directory of JSON files")
    parser.add_argument(
        "--report",
        default="janvaani_government_schemes_dataset/reports/validation-report.json",
        help="Output validation report path",
    )
    args = parser.parse_args()

    root = Path("janvaani_government_schemes_dataset")
    schema_path = root / "schemas" / "scheme-record.schema.json"
    input_path = Path(args.input)
    report_path = Path(args.report)

    if not schema_path.is_file():
        print(f"Schema not found: {schema_path}", file=sys.stderr)
        return 2
    if not input_path.exists():
        print(f"Input path not found: {input_path}", file=sys.stderr)
        return 2

    schema = load_json(schema_path)
    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )

    if input_path.is_file():
        files = [input_path] if input_path.suffix.lower() == ".json" else []
    else:
        files = sorted(input_path.rglob("*.json"))

    if not files:
        print("No JSON input files found.", file=sys.stderr)
        return 2

    results = []
    for file_path in files:
        result = {
            "file": str(file_path),
            "input_sha256": None,
            "valid_against_schema": False,
            "release_blockers": [],
            "schema_errors": [],
        }

        try:
            record = load_json(file_path)
            result["input_sha256"] = sha256_file(file_path)

            errors = sorted(
                validator.iter_errors(record),
                key=lambda error: list(map(str, error.absolute_path)),
            )
            result["schema_errors"] = [
                {
                    "path": "/" + "/".join(map(str, error.absolute_path)),
                    "message": error.message,
                }
                for error in errors
            ]
            result["valid_against_schema"] = not errors

            if not isinstance(record, dict):
                result["release_blockers"].append(
                    "Top-level JSON value must be an object."
                )
            else:
                if record.get("record_status") == "approved":
                    result["release_blockers"].append(
                        "Record claims approved status; approval must be established "
                        "through Janvaani's reviewer workflow."
                    )

                for index, source in enumerate(record.get("source_records", [])):
                    if not isinstance(source, dict):
                        continue
                    if source.get("review_status") != "verified":
                        result["release_blockers"].append(
                            f"source_records[{index}] is not verified."
                        )
                    if not source.get("license_or_reuse_basis"):
                        result["release_blockers"].append(
                            f"source_records[{index}] lacks a reuse basis."
                        )
                    parsed_url = urlparse(source.get("url", ""))
                    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
                        result["release_blockers"].append(
                            f"source_records[{index}] has no valid HTTP(S) source URL."
                        )

                if not record.get("source_records"):
                    result["release_blockers"].append(
                        "At least one source record is required."
                    )

                for index, translation in enumerate(record.get("translations", [])):
                    if isinstance(translation, dict) and translation.get(
                        "translation_status"
                    ) == "approved" and not translation.get("reviewer"):
                        result["release_blockers"].append(
                            f"translations[{index}] is approved but has no reviewer."
                        )

        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            result["schema_errors"].append(
                {"path": "/", "message": f"Cannot parse JSON: {exc}"}
            )
        except OSError as exc:
            result["schema_errors"].append(
                {"path": "/", "message": f"Cannot read file: {exc}"}
            )

        results.append(result)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_file": str(schema_path),
        "input_path": str(input_path),
        "files_checked": len(results),
        "schema_valid_count": sum(r["valid_against_schema"] for r in results),
        "files_with_release_blockers": sum(bool(r["release_blockers"]) for r in results),
        "database_modified": False,
        "records_approved": 0,
        "results": results,
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Files checked: {report['files_checked']}")
    print(f"Schema-valid files: {report['schema_valid_count']}")
    print(f"Files with release blockers: {report['files_with_release_blockers']}")
    print("Database modified: no")
    print("Records approved: 0")
    print(f"Report written to: {report_path}")

    return 0 if all(
        r["valid_against_schema"] and not r["release_blockers"] for r in results
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
