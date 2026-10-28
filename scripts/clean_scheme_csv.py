import csv
import json
import re
import hashlib
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "janvaani_government_schemes_dataset" / "incoming" / "kaggle_structured" / "structured.csv"
OUT_DIR = ROOT / "janvaani_government_schemes_dataset" / "staging"
CLEAN_CSV = OUT_DIR / "structured.cleaned.csv"
REPORT = OUT_DIR / "structured.cleaning-report.json"

class TextExtractor(HTMLParser):
    BLOCK_TAGS = {
        "p", "div", "br", "li", "ul", "ol", "tr",
        "h1", "h2", "h3", "h4", "h5", "h6"
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)

    def text(self):
        return "".join(self.parts)

def clean_text(value):
    value = (value or "").replace("\ufeff", "").replace("\xa0", " ")
    if not value.strip():
        return ""

    # Only parse values that appear to contain HTML markup.
    if re.search(r"<\s*/?\s*[a-zA-Z][^>]*>", value):
        parser = TextExtractor()
        try:
            parser.feed(value)
            parser.close()
            value = parser.text()
        except Exception:
            # Preserve the original text if parsing fails.
            return re.sub(r"\s+", " ", value).strip()

    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in value.splitlines()]
    value = "\n".join(line for line in lines if line)
    return value.strip()

def main():
    if not SOURCE.exists():
        raise SystemExit(f"Source CSV not found: {SOURCE}")

    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()

    with SOURCE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames
        if not columns:
            raise SystemExit("CSV has no header row.")
        rows = list(reader)

    cleaned_rows = []
    html_changes = Counter()
    whitespace_changes = Counter()
    missing_before = Counter()
    missing_after = Counter()
    duplicate_names = Counter()
    review_items = []

    for row_number, original in enumerate(rows, start=2):
        cleaned = {}
        for col in columns:
            before = original.get(col, "") or ""
            after = clean_text(before)
            if re.search(r"<\s*/?\s*[a-zA-Z][^>]*>", before):
                html_changes[col] += 1
            if before != after and not re.search(
                r"<\s*/?\s*[a-zA-Z][^>]*>", before
            ):
                whitespace_changes[col] += 1
            if not before.strip():
                missing_before[col] += 1
            if not after.strip():
                missing_after[col] += 1
            cleaned[col] = after

        cleaned_rows.append(cleaned)

        if not cleaned.get("scheme_name", "").strip():
            review_items.append({
                "csv_row": row_number,
                "scheme_id": cleaned.get("scheme_id", ""),
                "issue": "missing_scheme_name"
            })

        if not cleaned.get("references", "").strip():
            review_items.append({
                "csv_row": row_number,
                "scheme_id": cleaned.get("scheme_id", ""),
                "issue": "missing_reference"
            })

        for field in ("benefits", "eligibility", "application_process", "documents"):
            if not cleaned.get(field, "").strip():
                review_items.append({
                    "csv_row": row_number,
                    "scheme_id": cleaned.get("scheme_id", ""),
                    "issue": f"missing_{field}"
                })

        level = cleaned.get("level", "").strip().casefold()
        if level not in {"central", "state", "state/ ut"}:
            review_items.append({
                "csv_row": row_number,
                "scheme_id": cleaned.get("scheme_id", ""),
                "issue": "unrecognized_level",
                "value": cleaned.get("level", "")
            })

        duplicate_names[cleaned.get("scheme_name", "").strip().casefold()] += 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with CLEAN_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(cleaned_rows)

    duplicate_name_groups = [
        {"normalized_name": name, "count": count}
        for name, count in duplicate_names.items()
        if name and count > 1
    ]

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": str(SOURCE.relative_to(ROOT)),
        "source_sha256": source_hash,
        "output_file": str(CLEAN_CSV.relative_to(ROOT)),
        "input_rows": len(rows),
        "output_rows": len(cleaned_rows),
        "columns": columns,
        "html_like_values_changed_by_column": dict(html_changes),
        "non_html_whitespace_changes_by_column": dict(whitespace_changes),
        "missing_values_before_by_column": dict(missing_before),
        "missing_values_after_by_column": dict(missing_after),
        "duplicate_scheme_name_groups": duplicate_name_groups,
        "review_item_count": len(review_items),
        "review_items": review_items,
        "limitations": [
            "This is a formatting cleanup, not factual verification.",
            "HTML tags were converted to readable text; link destinations embedded in HTML may not be preserved.",
            "No records were intentionally removed.",
            "Scheme names and eligibility rules were not rewritten.",
            "Official source authenticity, scheme status, and licence/reuse permissions remain unverified."
        ]
    }

    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Input rows: {len(rows)}")
    print(f"Output rows: {len(cleaned_rows)}")
    print(f"Input SHA-256: {source_hash}")
    print(f"Duplicate name groups: {len(duplicate_name_groups)}")
    print(f"Review items: {len(review_items)}")
    print(f"Cleaned CSV: {CLEAN_CSV}")
    print(f"Report: {REPORT}")

if __name__ == "__main__":
    main()
