import csv
from pathlib import Path

path = Path(
    "janvaani_government_schemes_dataset/reports/"
    "missing-reference-evidence-review.csv"
)

updates = {
    "641bc580d88401653151a051": {
        "url": "https://www.cmchistn.com/administrators/government-orders",
        "type": "Official Tamil Nadu CMCHIS government-orders directory",
        "notes": "Stronger than the ABDM subsection. Select the applicable current order or guidelines; verify document date and reuse rights."
    },
    "65d83237938a0b13cc8eaa67": {
        "url": "https://msme.maharashtra.gov.in/provider/credit-and-finance/",
        "type": "Official Maharashtra Commissionerate of MSME scheme directory",
        "notes": "Current department directory lists CMEGP. Locate and verify the latest scheme guidelines or government resolution."
    },
    "66615c6b6cbcc730048dfba8": {
        "url": "https://silpasathi.wb.gov.in/msme_Incentives",
        "type": "Official West Bengal MSME incentives directory",
        "notes": "Lists SGST subsidy, but exact applicability to the powerloom scheme remains unconfirmed. Find the relevant textile/powerloom notification."
    },
    "641d5375ded5a517c845511d": {
        "url": "https://epds.hp.gov.in/FormsCenter1.aspx",
        "type": "Official Himachal Pradesh ePDS forms directory",
        "notes": "Scheme is listed in the forms directory. Retrieve the actual form and verify current scheme rules from an official notification."
    },
    "6421902bb04969635da5eefd": {
        "url": "https://sje.gujarat.gov.in/assets/downloads/SCSP_202021_09072021.pdf",
        "type": "Gujarat government-hosted historical supporting document",
        "notes": "Document describes Mahila Utkarsh Yojana but is historical. Find a current scheme-specific Gujarat government notification."
    },
}

with path.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    fields = reader.fieldnames
    rows = list(reader)

if not fields or "scheme_id" not in fields:
    raise SystemExit("Unexpected CSV schema; no changes made.")

updated = 0
for row in rows:
    scheme_id = (row.get("scheme_id") or "").strip()
    if scheme_id not in updates:
        continue

    item = updates[scheme_id]
    row["candidate_evidence_url"] = item["url"]
    row["evidence_type"] = item["type"]
    row["verification_status"] = "Pending manual verification"
    row["verified_official_url"] = ""
    row["document_date"] = ""
    row["scheme_match_confirmed"] = "No"
    row["reuse_rights_checked"] = "No"
    row["reviewer_notes"] = item["notes"]
    updated += 1

if updated != len(updates):
    raise SystemExit(
        f"Expected {len(updates)} scheme rows, found {updated}. "
        "No file written; check the input file."
    )

with path.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

print(f"Updated evidence-review rows: {updated}")
print("All five remain pending manual verification.")
print("Original scheme dataset and source URLs were not modified.")
