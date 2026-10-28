import csv
from pathlib import Path

path = Path(
    "janvaani_government_schemes_dataset/reports/"
    "official-source-research-notes.csv"
)

rows = [
    {
        "domain": "scholarshipportal.mp.nic.in",
        "scheme_name": "Madhya Pradesh State Scholarship Portal",
        "evidence_url": "https://www.india.gov.in/category/benefits-social-development/subcategory/benefits-grants-subsidies/details/website-of-state-scholarship-portal-madhya-pradesh",
        "evidence_type": "National Portal of India directory entry",
        "decision": "Official discovery source found",
        "notes": "Confirms the state scholarship portal; does not replace individual scheme documents."
    },
    {
        "domain": "scholarshipportal.mp.nic.in",
        "scheme_name": "Mukhyamantri Jankalyan (Shiksha Protsahan Yojna)",
        "evidence_url": "https://mptechedu.org/files/phases_mmjky.pdf",
        "evidence_type": "Scheme process chart",
        "decision": "Supporting document candidate found",
        "notes": "Describes registration, application, verification and sanction; verify currency before adoption."
    },
    {
        "domain": "handicrafts.nic.in",
        "scheme_name": "National Handicrafts Development Programme: Infrastructure and Technology Support: EMPORIA; URBAN HAAT",
        "evidence_url": "https://handicrafts.nic.in/images/schemes/NHDP_Guidlines.pdf",
        "evidence_type": "Official NHDP scheme guidelines",
        "decision": "Potential replacement for general scheme guidelines",
        "notes": "Covers Emporia and Urban Haat; compare version and scope against original Scheme.pdf."
    },
    {
        "domain": "handicrafts.nic.in",
        "scheme_name": "National Handicrafts Development Programme",
        "evidence_url": "https://handicrafts.nic.in/schemes.aspx",
        "evidence_type": "Official scheme directory",
        "decision": "Official discovery source found",
        "notes": "Use to locate current component-specific information; not a replacement for individual PDFs."
    },
    {
        "domain": "coirboard.gov.in",
        "scheme_name": "Coir Vikas Yojana; Coir Industry Technology Upgradation Scheme; Export Market Promotion Scheme",
        "evidence_url": "https://coirboard.gov.in/?page_id=221",
        "evidence_type": "Official Coir Board schemes directory",
        "decision": "Official discovery source found",
        "notes": "Lists relevant schemes and guideline links; map each legacy PDF individually."
    },
]

fields = [
    "domain", "scheme_name", "evidence_url",
    "evidence_type", "decision", "notes"
]

with path.open("a", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writerows(rows)

print(f"Added {len(rows)} entries to {path}")
print("Original scheme dataset and reference URLs remain unchanged.")
