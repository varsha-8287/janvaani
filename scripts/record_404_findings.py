import csv
from pathlib import Path

root = Path(__file__).resolve().parents[1]
output = root / "janvaani_government_schemes_dataset" / "reports" / "http-404-findings.csv"

rows = [
    {
        "scheme_name": "Dulari Kanya",
        "scheme_id": "64114826d58cf01bf7d0ac0d",
        "original_url": "http://health.arunachal.gov.in/wp-content/uploads/2018/08/Dulari-Kanya.pdf",
        "candidate_official_url": "https://health.arunachal.gov.in/Dulari-Kanya.pdf",
        "finding": "Official department PDF found at a different path",
        "decision": "Candidate replacement; verify current scheme status before adoption",
    },
    {
        "scheme_name": "Merit Cum Means Linked Financial Assistance Scheme",
        "scheme_id": "64427e6f642a2a5974373b6f",
        "original_url": "http://higheredn.delhi.gov.in/sites/default/files/McM-LFA-FAQs.pdf",
        "candidate_official_url": "https://higheredn.delhi.gov.in/sites/default/files/generic_multiple_files/2_2.pdf",
        "finding": "Official Directorate FAQ found at a different path",
        "decision": "Candidate replacement for FAQ reference only",
    },
    {
        "scheme_name": "Merit Cum Means Linked Financial Assistance Scheme",
        "scheme_id": "64427e6f642a2a5974373b6f",
        "original_url": "http://higheredn.delhi.gov.in/merit-cum-means-linked-financial-assistance-scheme-pursuing-higher-education-state-universities-",
        "candidate_official_url": "",
        "finding": "Original URL returned 404",
        "decision": "Needs further official-source research",
    },
    {
        "scheme_name": "Merit Cum Means Linked Financial Assistance Scheme",
        "scheme_id": "64427e6f642a2a5974373b6f",
        "original_url": "http://higheredn.delhi.gov.in/sites/default/files/McM-LFA-Approved-Merit-Cum-Means-Scheme.pdf",
        "candidate_official_url": "",
        "finding": "Original PDF URL returned 404",
        "decision": "Needs further official-source research",
    },
]

fields = [
    "scheme_name", "scheme_id", "original_url",
    "candidate_official_url", "finding", "decision"
]
output.parent.mkdir(parents=True, exist_ok=True)
with output.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

print(f"Saved {len(rows)} findings to: {output}")
print("Original dataset and remediation queue remain unchanged.")
