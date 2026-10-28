import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from pydantic import ValidationError

from app.ingestion.schemas import SchemeIngestionInput

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "janvaani_government_schemes_dataset" / "staging" / "structured.cleaned.csv"
REPORT = ROOT / "janvaani_government_schemes_dataset" / "reports" / "dry-run-import-report.json"

URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
TRAILING_URL_PUNCTUATION = ".,;:!?)\"]}"

def text(value):
    return (value or "").strip()

def extract_urls(value):
    urls = []
    for match in URL_RE.findall(value or ""):
        url = match.rstrip(TRAILING_URL_PUNCTUATION)
        if url and url not in urls:
            urls.append(url)
    return urls

def paragraphs(value):
    return [
        line.strip(" \t-*•")
        for line in (value or "").splitlines()
        if line.strip(" \t-*•")
    ]

def normalize_level(value):
    value = text(value).casefold()
    mapping = {
        "central": "central",
        "state": "state",
        "state/ ut": "state",
    }
    return mapping.get(value)

def main():
    if not SOURCE.exists():
        raise SystemExit(f"Cleaned CSV not found: {SOURCE}")

    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()

    with SOURCE.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": str(SOURCE.relative_to(ROOT)),
        "source_sha256": source_hash,
        "database_connection_opened": False,
        "rows_total": len(rows),
        "schema_valid_count": 0,
        "schema_invalid_count": 0,
        "pending_provenance_review_count": 0,
        "eligibility_review_required_count": len(rows),
        "counts_by_level": {},
        "issues": Counter(),
        "examples": [],
        "limitations": [
            "No database connection or writes were performed.",
            "Schema validation does not verify factual accuracy or reuse permissions.",
            "The validation timestamp is generated only to exercise the Pydantic contract; it is NOT evidence of when the official source was retrieved.",
            "Eligibility text is deliberately not converted into approved structured rules.",
            "External CSV scheme IDs, state, category, tags, FAQs and beneficiaries are not persisted by the current ingestion contract.",
            "A valid HTTPS URL does not establish that the source is official or that its contents are licensed for reuse."
        ],
    }

    issues = Counter()
    levels = Counter()
    examples = []

    for row_number, row in enumerate(rows, start=2):
        scheme_id = text(row.get("scheme_id"))
        slug = text(row.get("slug"))
        title = text(row.get("scheme_name"))
        raw_level = text(row.get("level"))
        level = normalize_level(raw_level)
        state = text(row.get("state"))
        refs = text(row.get("references"))
        urls = extract_urls(refs)

        row_issues = []

        if not scheme_id:
            row_issues.append("missing_external_scheme_id")
        if not title:
            row_issues.append("missing_title")
        if not slug:
            row_issues.append("missing_slug")
        elif len(slug) > 180:
            row_issues.append("slug_too_long")
        if title and len(title) > 300:
            row_issues.append("title_too_long")
        if not level:
            row_issues.append("unrecognized_government_level")
        if not state and level == "state":
            row_issues.append("state_level_without_state_name")
        if not urls:
            row_issues.append("no_reference_url")
        elif not any(
            urlparse(url).scheme == "https" and urlparse(url).netloc
            for url in urls
        ):
            row_issues.append("no_valid_https_reference")

        https_urls = [
            url for url in urls
            if urlparse(url).scheme == "https" and urlparse(url).netloc
        ]

        schema_valid = False
        if not row_issues and https_urls:
            # This timestamp is for contract validation only.
            # It must NOT be reused as an official-source retrieval timestamp.
            validation_payload = {
                "slug": slug,
                "title": title,
                "administering_authority": text(row.get("department")) or None,
                "government_level": level,
                "language": "en",
                "description": text(row.get("description")) or None,
                "benefits": paragraphs(row.get("benefits")),
                # Do not turn natural-language text into eligibility rules.
                "eligibility_criteria": None,
                "required_documents": paragraphs(row.get("documents")),
                "application_process": paragraphs(row.get("application_process")),
                "source_url": https_urls[0],
                "publisher": None,
                "retrieved_at": datetime.now(timezone.utc),
                "content_hash": hashlib.sha256(
                    json.dumps(row, sort_keys=True, ensure_ascii=False).encode("utf-8")
                ).hexdigest(),
            }
            try:
                SchemeIngestionInput.model_validate(validation_payload)
                schema_valid = True
            except ValidationError as exc:
                row_issues.append("ingestion_schema_validation_failed")
                for error in exc.errors():
                    issues[f"schema:{error['loc'][0]}"] += 1

        if schema_valid:
            report["schema_valid_count"] += 1
        else:
            report["schema_invalid_count"] += 1

        # Even structurally valid records remain blocked from real import until
        # provenance/licensing, source accuracy and duplicate review are complete.
        report["pending_provenance_review_count"] += 1
        levels[level or f"unmapped:{raw_level or '(blank)'}"] += 1

        for issue in row_issues:
            issues[issue] += 1

        if row_issues and len(examples) < 30:
            examples.append({
                "csv_row": row_number,
                "external_scheme_id": scheme_id,
                "slug": slug,
                "title": title[:180],
                "issues": row_issues,
                "reference_urls_found": urls[:3],
            })

    report["counts_by_level"] = dict(levels)
    report["issues"] = dict(issues)
    report["examples"] = examples
    report["ready_for_real_import_count"] = 0

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Rows examined: {report['rows_total']}")
    print(f"Schema-valid rows: {report['schema_valid_count']}")
    print(f"Schema-invalid rows: {report['schema_invalid_count']}")
    print(f"Pending provenance review: {report['pending_provenance_review_count']}")
    print(f"Ready for real import: {report['ready_for_real_import_count']}")
    print("\nIssues:")
    print(json.dumps(report["issues"], ensure_ascii=False, indent=2))
    print("\nCounts by normalized level:")
    print(json.dumps(report["counts_by_level"], ensure_ascii=False, indent=2))
    print(f"\nFull report: {REPORT}")

if __name__ == "__main__":
    main()
