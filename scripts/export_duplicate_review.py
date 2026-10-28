import csv
from pathlib import Path

root = Path("janvaani_government_schemes_dataset")
source = root / "incoming/kaggle_structured/structured.csv"
output = root / "reports/duplicate-review.csv"

target_ids = {
    "685008fcdf7f9910b3b9ecfb",
    "6854ec019649a9b4a6c489da",
}

with source.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

fields = [
    "scheme_id", "slug", "scheme_name", "state", "department",
    "brief_description", "eligibility", "benefits", "references",
]

output.parent.mkdir(parents=True, exist_ok=True)
with output.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=fields + ["review_status", "review_notes"],
        extrasaction="ignore",
    )
    writer.writeheader()
    for row in rows:
        if row.get("scheme_id") in target_ids:
            record = {key: row.get(key, "") for key in fields}
            record["review_status"] = "possible_duplicate_pending_verification"
            record["review_notes"] = (
                "Same state, department, university, eligibility and reference URL; "
                "verify official guideline before merging."
            )
            writer.writerow(record)

print(f"Saved duplicate review to: {output.resolve()}")
