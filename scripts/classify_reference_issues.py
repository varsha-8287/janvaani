import csv
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

root = Path(__file__).resolve().parents[1]
path = root / "janvaani_government_schemes_dataset" / "reports" / "reference-issues.csv"

with path.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

def classify(row):
    refs = (row.get("references_original") or "").strip()
    urls = (row.get("urls_detected") or "").strip()

    if not refs:
        return "empty_reference_field"
    if urls and not any(
        urlparse(u.strip()).scheme == "https" and urlparse(u.strip()).netloc
        for u in urls.split("|")
    ):
        return "detected_url_not_https"
    if not urls:
        if "www." in refs.lower() or "http" in refs.lower():
            return "possible_malformed_url"
        return "text_or_nonstandard_reference"
    return "other"

counts = Counter(classify(row) for row in rows)
print("Reference issue categories:")
for category, count in counts.most_common():
    print(f"{category}: {count}")

print("\nFirst 20 records with original references:")
for row in rows[:20]:
    print("-" * 70)
    print("CSV row:", row["csv_row"])
    print("Scheme:", row["scheme_name"])
    print("Issue:", row["issue"])
    print("References:", row["references_original"] or "(empty)")
    print("Detected URLs:", row["urls_detected"] or "(none)")
