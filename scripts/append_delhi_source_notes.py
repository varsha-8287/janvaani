import csv
from pathlib import Path

path = Path("janvaani_government_schemes_dataset/reports/official-source-research-notes.csv")

new_rows = [
    {
        "domain": "health.delhigovt.nic.in",
        "scheme_name": "Delhi Arogya Kosh",
        "evidence_url": "https://health.delhi.gov.in/health/delhi-arogya-kosh",
        "evidence_type": "Official current scheme page",
        "decision": "Official alternative candidate found",
        "notes": "Use as scheme overview candidate; not a replacement for every legacy PDF."
    },
    {
        "domain": "health.delhigovt.nic.in",
        "scheme_name": "Delhi Arogya Kosh",
        "evidence_url": "https://health.delhi.gov.in/sites/default/files/Health/generic_multiple_files/dak.pdf",
        "evidence_type": "Official scheme guidelines PDF",
        "decision": "Supporting document candidate found",
        "notes": "Review document contents and date before mapping to a specific original reference."
    },
    {
        "domain": "health.delhigovt.nic.in",
        "scheme_name": "Delhi Arogya Kosh",
        "evidence_url": "https://dgehs.delhi.gov.in/dghs/delhi-arogya-kosh",
        "evidence_type": "Official Directorate scheme page",
        "decision": "Official alternative candidate found",
        "notes": "Contains scheme information and links to supporting resources."
    },
    {
        "domain": "health.delhigovt.nic.in",
        "scheme_name": "Delhi Arogya Kosh",
        "evidence_url": "https://dgehs.delhi.gov.in/sites/default/files/inline-files/om_dak.pdf",
        "evidence_type": "Official office memorandum",
        "decision": "Supporting document candidate found",
        "notes": "Specific amendment memorandum; do not substitute for unrelated PDFs."
    },
]

with path.open("a", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "domain", "scheme_name", "evidence_url",
            "evidence_type", "decision", "notes"
        ],
    )
    writer.writerows(new_rows)

print(f"Added {len(new_rows)} research entries to {path}")
