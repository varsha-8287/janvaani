import csv
from pathlib import Path

path = Path(
    "janvaani_government_schemes_dataset/reports/"
    "official-source-research-notes.csv"
)

rows = [
    {
        "domain": "assamtourismonline.com",
        "scheme_name": "Promotion and Development of Tea Tourism Infrastructure in Assam",
        "evidence_url": "https://www.assamtourismonline.com/pdf/tea_tourism_brochure.pdf",
        "evidence_type": "Official scheme brochure",
        "decision": "Strong replacement candidate",
        "notes": "Brochure names the scheme, Tourism Department and implementing agency; confirm the document version before adoption."
    },
    {
        "domain": "nhm.gov.in",
        "scheme_name": "Janani Shishu Suraksha Karyakram",
        "evidence_url": "https://www.nhm.gov.in/index4.php?lang=1&level=0&lid=171&linkid=150",
        "evidence_type": "Official National Health Mission programme page",
        "decision": "Official scheme page candidate",
        "notes": "Current programme information; match the old reference's intended content before replacing."
    },
    {
        "domain": "nhm.gov.in",
        "scheme_name": "Janani Shishu Suraksha Karyakram",
        "evidence_url": "https://nhm.gov.in/images/pdf/programmes/jssk/guidelines/guidelines_for_jssk.pdf",
        "evidence_type": "Official scheme guidelines PDF",
        "decision": "Supporting document candidate",
        "notes": "Official JSSK guidelines; verify document version and applicability."
    },
]

fields = [
    "domain", "scheme_name", "evidence_url",
    "evidence_type", "decision", "notes"
]

with path.open("a", encoding="utf-8-sig", newline="") as f:
    csv.DictWriter(f, fieldnames=fields).writerows(rows)

print(f"Added {len(rows)} entries to {path}")
