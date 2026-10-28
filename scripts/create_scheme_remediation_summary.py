import csv
import re
from pathlib import Path

root = Path("janvaani_government_schemes_dataset")
report_path = root / "reports" / "reference-issues.csv"
notes_path = root / "reports" / "official-source-research-notes.csv"
output_path = root / "reports" / "scheme-remediation-summary.csv"

def normalize_name(value):
    return re.sub(r"\s+", " ", (value or "").strip()).casefold()

with report_path.open("r", encoding="utf-8-sig", newline="") as f:
    issues = list(csv.DictReader(f))

with notes_path.open("r", encoding="utf-8-sig", newline="") as f:
    notes = list(csv.DictReader(f))

notes_by_scheme = {}
for note in notes:
    key = normalize_name(note.get("scheme_name"))
    if key:
        notes_by_scheme.setdefault(key, []).append(note)

schemes = {}
for row in issues:
    name = (row.get("scheme_name") or "").strip()
    key = ((row.get("scheme_id") or "").strip(), normalize_name(name))
    item = schemes.setdefault(key, {
        "scheme_id": row.get("scheme_id", ""),
        "scheme_name": name,
        "issue_rows": [],
    })
    item["issue_rows"].append(row)

fields = [
    "scheme_id", "scheme_name", "issue",
    "detected_url_count", "missing_reference_count",
    "non_https_reference_count", "research_note_count",
    "research_candidate_urls", "review_status", "review_notes",
]

with output_path.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()

    for item in sorted(schemes.values(),
                       key=lambda x: x["scheme_name"].casefold()):
        scheme_notes = notes_by_scheme.get(
            normalize_name(item["scheme_name"]), []
        )

        all_urls = []
        missing_count = 0
        non_https_count = 0
        issues_found = set()

        for row in item["issue_rows"]:
            issues_found.add((row.get("issue") or "").strip())
            urls = [
                u.strip()
                for u in (row.get("urls_detected") or "").split("|")
                if u.strip()
            ]
            all_urls.extend(urls)

            if not urls:
                missing_count += 1

            non_https_count += sum(
                1 for url in urls if url.lower().startswith("http://")
            )

        candidate_urls = sorted({
            (note.get("evidence_url") or "").strip()
            for note in scheme_notes
            if (note.get("evidence_url") or "").strip()
        })

        writer.writerow({
            "scheme_id": item["scheme_id"],
            "scheme_name": item["scheme_name"],
            "issue": " | ".join(sorted(issues_found)),
            "detected_url_count": len(set(all_urls)),
            "missing_reference_count": missing_count,
            "non_https_reference_count": non_https_count,
            "research_note_count": len(scheme_notes),
            "research_candidate_urls": " | ".join(candidate_urls),
            "review_status": "Needs manual scheme-level review",
            "review_notes": (
                "Candidate sources are not approved replacements. "
                "Verify publisher, scheme match, document type, date, "
                "and reuse rights before adoption."
            ),
        })

print(f"Distinct schemes in reference-issues report: {len(schemes)}")
print(f"Research notes available: {len(notes)}")
print(f"Schemes with exact normalized-name note matches: "
      f"{sum(1 for x in schemes.values() if notes_by_scheme.get(normalize_name(x['scheme_name'])))}")
print(f"Schemes with no detected URLs: "
      f"{sum(1 for x in schemes.values() if all(not (r.get('urls_detected') or '').strip() for r in x['issue_rows']))}")
print(f"Saved corrected summary: {output_path}")
print("No source dataset or reference URLs were modified.")
