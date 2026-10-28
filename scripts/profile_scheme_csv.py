import csv
import json
import hashlib
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "janvaani_government_schemes_dataset" / "incoming" / "kaggle_structured" / "structured.csv"
REPORT = ROOT / "janvaani_government_schemes_dataset" / "reports" / "structured-profile.json"

def normalize(value):
    return re.sub(r"\s+", " ", (value or "").strip())

def main():
    if not SOURCE.exists():
        raise SystemExit(f"CSV not found: {SOURCE}")

    digest = hashlib.sha256()
    with SOURCE.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)

    with SOURCE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        rows = list(reader)

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": str(SOURCE.relative_to(ROOT)),
        "sha256": digest.hexdigest(),
        "row_count": len(rows),
        "column_count": len(columns),
        "columns": {},
        "exact_duplicate_rows": 0,
        "duplicate_checks": {},
        "review_flags": [],
    }

    for col in columns:
        values = [normalize(row.get(col, "")) for row in rows]
        nonempty = [v for v in values if v]
        counts = Counter(nonempty)
        report["columns"][col] = {
            "missing_count": len(values) - len(nonempty),
            "missing_percent": round(
                100 * (len(values) - len(nonempty)) / len(values), 2
            ) if values else 0,
            "unique_nonempty": len(counts),
            "most_common_values": [
                {"value": value[:180], "count": count}
                for value, count in counts.most_common(5)
            ],
            "placeholder_count": sum(
                v.casefold() in {"-", "--", "n/a", "na", "none", "null", "not available"}
                for v in nonempty
            ),
            "html_like_values": sum(
                bool(re.search(r"<[^>]+>", v)) for v in nonempty
            ),
        }

    seen = set()
    exact_duplicates = 0
    for row in rows:
        key = tuple(normalize(row.get(col, "")) for col in columns)
        if key in seen:
            exact_duplicates += 1
        seen.add(key)
    report["exact_duplicate_rows"] = exact_duplicates

    for col in ("scheme_id", "slug", "scheme_name", "short_title"):
        if col in columns:
            vals = [normalize(r.get(col, "")).casefold() for r in rows]
            nonempty = [v for v in vals if v]
            counts = Counter(nonempty)
            report["duplicate_checks"][col] = {
                "missing_count": len(vals) - len(nonempty),
                "duplicate_value_count": sum(n > 1 for n in counts.values()),
                "rows_in_duplicate_groups": sum(n for n in counts.values() if n > 1),
                "examples": [
                    {"value": v[:160], "count": n}
                    for v, n in counts.most_common()
                    if n > 1
                ][:10],
            }

    for col in ("scheme_name", "eligibility", "benefits", "application_process", "documents", "references"):
        if col not in columns:
            report["review_flags"].append(f"Expected field absent: {col}")

    report["review_flags"].append(
        "This is a structural profile only; it does not verify scheme accuracy, "
        "official URLs, current status, or licence/reuse permissions."
    )

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Rows: {len(rows)}")
    print(f"Columns: {len(columns)}")
    print("Column names:", ", ".join(columns))
    print(f"Exact duplicate rows: {exact_duplicates}")
    print(f"SHA-256: {digest.hexdigest()}")
    print(f"Report saved to: {REPORT}")

if __name__ == "__main__":
    main()
