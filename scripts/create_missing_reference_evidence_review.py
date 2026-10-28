import csv
from pathlib import Path

root = Path("janvaani_government_schemes_dataset")
issues_path = root / "reports" / "reference-issues.csv"
notes_path = root / "reports" / "official-source-research-notes.csv"
out_path = root / "reports" / "missing-reference-evidence-review.csv"

target_ids = {
    "641bc580d88401653151a051",
    "65d83237938a0b13cc8eaa67",
    "66615c6b6cbcc730048dfba8",
    "641d5375ded5a517c845511d",
    "6421902bb04969635da5eefd",
}

with issues_path.open("r", encoding="utf-8-sig", newline="") as f:
    issues = list(csv.DictReader(f))

with notes_path.open("r", encoding="utf-8-sig", newline="") as f:
    notes = list(csv.DictReader(f))

notes_by_name = {}
for note in notes:
    name = " ".join((note.get("scheme_name") or "").split()).casefold()
    if name:
        notes_by_name.setdefault(name, []).append(note)

fields = [
    "scheme_id", "scheme_name", "state", "department",
    "original_issue", "candidate_evidence_url", "evidence_type",
    "research_decision", "verification_status", "verified_official_url",
    "document_date", "scheme_match_confirmed", "reuse_rights_checked",
    "reviewer_notes",
]

with out_path.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()

    found = set()
    for row in issues:
        scheme_id = (row.get("scheme_id") or "").strip()
        if scheme_id not in target_ids:
            continue

        found.add(scheme_id)
        key = " ".join((row.get("scheme_name") or "").split()).casefold()
        matches = notes_by_name.get(key, [])

        if matches:
            for note in matches:
                writer.writerow({
                    "scheme_id": scheme_id,
                    "scheme_name": row.get("scheme_name", ""),
                    "state": row.get("state", ""),
                    "department": row.get("department", ""),
                    "original_issue": row.get("issue", ""),
                    "candidate_evidence_url": note.get("evidence_url", ""),
                    "evidence_type": note.get("evidence_type", ""),
                    "research_decision": note.get("decision", ""),
                    "verification_status": "Pending manual verification",
                    "verified_official_url": "",
                    "document_date": "",
                    "scheme_match_confirmed": "No",
                    "reuse_rights_checked": "No",
                    "reviewer_notes": note.get("notes", ""),
                })
        else:
            writer.writerow({
                "scheme_id": scheme_id,
                "scheme_name": row.get("scheme_name", ""),
                "state": row.get("state", ""),
                "department": row.get("department", ""),
                "original_issue": row.get("issue", ""),
                "candidate_evidence_url": "",
                "evidence_type": "",
                "research_decision": "No matching research note",
                "verification_status": "Research required",
                "verified_official_url": "",
                "document_date": "",
                "scheme_match_confirmed": "No",
                "reuse_rights_checked": "No",
                "reviewer_notes": "Find an authoritative source; do not infer or fabricate a URL.",
            })

missing_ids = target_ids - found

print(f"Target scheme IDs: {len(target_ids)}")
print(f"Found in reference-issues report: {len(found)}")
print(f"Not found in report: {len(missing_ids)}")
if missing_ids:
    print("Missing IDs:", ", ".join(sorted(missing_ids)))
print(f"Evidence-review rows: {sum(1 for _ in csv.DictReader(out_path.open(encoding='utf-8-sig', newline='')))}")
print(f"Saved: {out_path}")
print("Candidate URLs remain unverified; source dataset unchanged.")
