import csv
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = root / "janvaani_government_schemes_dataset" / "reports" / "https-reference-check.csv"
output = root / "janvaani_government_schemes_dataset" / "reports" / "kerala-403-review.csv"

directory_url = "https://sjd.kerala.gov.in/schemes.php"

with source.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

affected = {}
for row in rows:
    if row.get("http_status") != "403":
        continue

    name = (row.get("scheme_name") or "").strip()
    if not name:
        continue

    item = affected.setdefault(name, {
        "scheme_name": name,
        "original_scheme_ids": set(),
        "blocked_urls": set(),
    })
    if row.get("scheme_id"):
        item["original_scheme_ids"].add(row["scheme_id"])
    if row.get("original_url"):
        item["blocked_urls"].add(row["original_url"])

fields = [
    "scheme_name",
    "scheme_ids",
    "blocked_url_count",
    "blocked_urls",
    "official_discovery_directory",
    "individual_scheme_page_verified",
    "verified_replacement_url",
    "review_status",
    "review_notes",
]

output.parent.mkdir(parents=True, exist_ok=True)
with output.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()

    for name, item in sorted(affected.items()):
        writer.writerow({
            "scheme_name": name,
            "scheme_ids": " | ".join(sorted(item["original_scheme_ids"])),
            "blocked_url_count": len(item["blocked_urls"]),
            "blocked_urls": " | ".join(sorted(item["blocked_urls"])),
            "official_discovery_directory": directory_url,
            "individual_scheme_page_verified": "No",
            "verified_replacement_url": "",
            "review_status": "Needs individual verification",
            "review_notes": "Directory is for discovery only; do not treat as a verified replacement for each blocked URL.",
        })

print(f"Distinct affected scheme names: {len(affected)}")
print(f"Saved: {output}")
print("Original CSV and scheme references were not changed.")
