import csv
from pathlib import Path

path = Path("janvaani_government_schemes_dataset/reports/official-source-research-notes.csv")

new_notes = [
    {
        "scheme_name": "Chief Minister's Comprehensive Health Insurance Scheme",
        "evidence_url": "https://www.cmchistn.com/abdm",
        "evidence_type": "Official Tamil Nadu scheme portal",
        "decision": "Candidate - verify current scheme documents",
        "notes": "Exact scheme portal identified; verify current guidelines and document-specific URLs before adoption."
    },
    {
        "scheme_name": "CHIEF MINISTER EMPLOYMENT GENERATION PROGRAMME (CMEGP)",
        "evidence_url": "https://msme.maharashtra.gov.in/scheme/chief-minister-employment-generation-programme-cmegp/",
        "evidence_type": "Official Maharashtra Commissionerate of MSME scheme page",
        "decision": "Candidate - verify current validity",
        "notes": "Exact scheme page found. Page displays programme period ending 2024-03-31; confirm current notification or extension."
    },
    {
        "scheme_name": "Incentive Scheme for MSMEs in Powerloom Sector: Subsidy for State Goods and Services Tax (SGST)",
        "evidence_url": "https://silpasathi.wb.gov.in/msme_Incentives",
        "evidence_type": "Official West Bengal MSME incentives directory",
        "decision": "Partial evidence - exact notification needed",
        "notes": "Directory lists Subsidy on SGST but does not by itself verify the exact powerloom scheme or its current rules. Do not substitute the standard quality compliance sub-scheme."
    },
    {
        "scheme_name": "Mukhya Mantri Grihini Suvidha Yojana",
        "evidence_url": "https://epds.hp.gov.in/FormsCenter1.aspx",
        "evidence_type": "Official Himachal Pradesh ePDS forms directory",
        "decision": "Candidate - guidelines needed",
        "notes": "Official forms directory lists Mukhya Mantri Grihini Suvidha Yojna. Locate current scheme guidelines or notification before adoption."
    },
    {
        "scheme_name": "Mukhyamantri Mahila Utkarsh Yojana",
        "evidence_url": "https://www.myscheme.gov.in/search?tag=Mukhyamantri",
        "evidence_type": "Government of India myScheme discovery listing",
        "decision": "Discovery candidate - Gujarat primary source needed",
        "notes": "Search results list the Gujarat scheme. Locate its exact scheme page and verify against a current Gujarat government source."
    },
]

with path.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    fields = reader.fieldnames
    rows = list(reader)

if not fields:
    raise SystemExit("Research notes CSV has no header; no changes made.")

required = {"scheme_name", "evidence_url", "evidence_type", "decision", "notes"}
missing = required - set(fields)
if missing:
    raise SystemExit(
        f"CSV is missing expected columns {sorted(missing)}. "
        "No changes made; inspect the header first."
    )

existing = {
    ((row.get("scheme_name") or "").strip().casefold(),
     (row.get("evidence_url") or "").strip().casefold())
    for row in rows
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

print(f"New research notes appended: {added}")
print(f"Total research-note rows: {len(rows)}")
print("Only the research-notes file was updated; source dataset and URLs remain unchanged.")
