import csv
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = root / "janvaani_government_schemes_dataset" / "reports" / "https-reference-check.csv"
output = root / "janvaani_government_schemes_dataset" / "reports" / "reference-remediation-queue.csv"

with source.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

fields = [
    "csv_row", "scheme_id", "scheme_name", "original_reference_text",
    "original_url", "https_candidate", "status", "http_status", "final_url",
    "review_action", "verified_official_url", "review_notes"
]

queue = []
for row in rows:
    status = row.get("status", "")
    code = row.get("http_status", "")

    if status == "no_url_to_check":
        action = "Find official source"
    elif code == "404":
        action = "Find current official URL"
    elif code == "403":
        action = "Verify manually; 403 is not proof of a broken URL"
    elif status == "https_connection_failed":
        action = "Investigate connection failure"
    elif status == "https_reachable":
        action = "Verify publisher and scheme details"
    else:
        action = "Manual review"

    queue.append({
        "csv_row": row.get("csv_row", ""),
        "scheme_id": row.get("scheme_id", ""),
        "scheme_name": row.get("scheme_name", ""),
        "original_reference_text": row.get("original_reference_text", ""),
        "original_url": row.get("original_url", ""),
        "https_candidate": row.get("https_candidate", ""),
        "status": status,
        "http_status": code,
        "final_url": row.get("final_url", ""),
        "review_action": action,
        "verified_official_url": "",
        "review_notes": "",
    })

output.parent.mkdir(parents=True, exist_ok=True)
with output.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(queue)

print(f"Review rows: {len(queue)}")
print(f"Saved: {output}")
print("Original dataset and references were not modified.")
