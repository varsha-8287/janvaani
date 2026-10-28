import csv
import re
from pathlib import Path
from urllib.parse import urlparse

root = Path(__file__).resolve().parents[1]
source = root / "janvaani_government_schemes_dataset" / "staging" / "structured.cleaned.csv"
output = root / "janvaani_government_schemes_dataset" / "reports" / "reference-issues.csv"

url_re = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
trailing = ".,;:!?)\"]}"

with source.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

problems = []
for row_number, row in enumerate(rows, start=2):
    references = (row.get("references") or "").strip()
    urls = [u.rstrip(trailing) for u in url_re.findall(references)]
    valid_https = [
        u for u in urls
        if urlparse(u).scheme == "https" and urlparse(u).netloc
    ]

    if not valid_https:
        problems.append({
            "csv_row": row_number,
            "scheme_id": row.get("scheme_id", ""),
            "scheme_name": row.get("scheme_name", ""),
            "state": row.get("state", ""),
            "level": row.get("level", ""),
            "department": row.get("department", ""),
            "references_original": references,
            "urls_detected": " | ".join(urls),
            "issue": "no_reference_url" if not urls else "no_valid_https_reference",
        })

output.parent.mkdir(parents=True, exist_ok=True)
with output.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "csv_row", "scheme_id", "scheme_name", "state", "level",
        "department", "references_original", "urls_detected", "issue"
    ])
    writer.writeheader()
    writer.writerows(problems)

print(f"Records needing reference review: {len(problems)}")
print(f"Saved: {output}")
for row in problems[:10]:
    print(f"{row['csv_row']}: {row['scheme_name']} — {row['issue']}")
