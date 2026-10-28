import csv
from pathlib import Path

path = Path(
    "janvaani_government_schemes_dataset/reports/"
    "official-source-research-notes.csv"
)

new_notes = [
    {
        "scheme_name": "Financial Assistance for Education of Children of Beneficiary",
        "evidence_url": "https://manipurbcwb.in/SchemeDetails?title=financial+assistance+for+education+of+children+of+beneficiary",
        "evidence_type": "Official Government of Manipur BOCW Welfare Board scheme page",
        "decision": "Strong candidate - verify current scheme terms",
        "notes": "Exact scheme page found on the official Manipur Building and Other Construction Workers Welfare Board website. Confirm current rates and any latest notification before adoption."
    },
    {
        "scheme_name": "Immediate Assistance in Case of Accident to the Beneficiary",
        "evidence_url": "https://manipurbcwb.in/SchemeDetails?title=immediate+assistance+in+case+of+accident+to+the+beneficiary",
        "evidence_type": "Official Government of Manipur BOCW Welfare Board scheme page",
        "decision": "Strong candidate - verify current scheme terms",
        "notes": "Exact scheme page found on the official board website. Verify current benefit amounts and any superseding notification."
    },
    {
        "scheme_name": "Personal Interest Subsidy Scheme",
        "evidence_url": "https://www.ukvib.org/personal-interest-factor-plan",
        "evidence_type": "Official Uttarakhand Khadi and Village Industries Board scheme page",
        "decision": "Strong candidate - verify current scheme terms",
        "notes": "Exact scheme page found on the board website. Confirm current government orders and eligibility terms before adoption."
    },
    {
        "scheme_name": "Self-Employment Scheme for Scheduled Castes and Tribes",
        "evidence_url": "https://www.ukbvvn.org.in/frmSCSTSelfEmployment.html",
        "evidence_type": "Official Uttarakhand Multipurpose Finance and Development Corporation scheme page",
        "decision": "Strong candidate - verify current scheme terms",
        "notes": "Exact scheme page found on the state corporation website. Verify current financial terms and relevant government orders."
    },
]

with path.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    fields = reader.fieldnames
    rows = list(reader)

required = {"scheme_name", "evidence_url", "evidence_type", "decision", "notes"}
if not fields or not required.issubset(fields):
    raise SystemExit(
        f"Unexpected research-notes CSV columns. Required: {sorted(required)}. "
        "No changes made."
    )

existing = {
    (
        (r.get("scheme_name") or "").strip().casefold(),
        (r.get("evidence_url") or "").strip().casefold(),
    )
    for r in rows
}

added = 0
for note in new_notes:
    key = (note["scheme_name"].strip().casefold(), note["evidence_url"].strip().casefold())
    if key in existing:
        continue
    rows.append({field: note.get(field, "") for field in fields})
    existing.add(key)
    added += 1

with path.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

print(f"Research notes appended: {added}")
print(f"Total research-note rows: {len(rows)}")
print("All findings remain candidates; original scheme dataset and URLs unchanged.")
