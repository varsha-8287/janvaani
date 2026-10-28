import csv
import json
import re
from pathlib import Path
from html.parser import HTMLParser

root = Path(__file__).resolve().parents[1]
original = root / "janvaani_government_schemes_dataset/incoming/kaggle_structured/structured.csv"
cleaned = root / "janvaani_government_schemes_dataset/staging/structured.cleaned.csv"
output = root / "janvaani_government_schemes_dataset/reports/cleaning-audit.json"

def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

before = read_csv(original)
after = read_csv(cleaned)

if len(before) != len(after):
    raise SystemExit(f"Row-count mismatch: original={len(before)}, cleaned={len(after)}")

changed_to_empty = []
html_link_examples = []
for i, (a, b) in enumerate(zip(before, after), start=2):
    for col, old in a.items():
        old = old or ""
        new = b.get(col, "") or ""
        if old.strip() and not new.strip():
            changed_to_empty.append({
                "csv_row": i,
                "scheme_id": a.get("scheme_id", ""),
                "column": col,
                "original_excerpt": old[:300]
            })
        if "<a " in old.lower() and len(html_link_examples) < 20:
            hrefs = re.findall(
                r'''href\s*=\s*["']([^"']+)["']''',
                old,
                flags=re.IGNORECASE
            )
            if hrefs:
                html_link_examples.append({
                    "csv_row": i,
                    "scheme_id": a.get("scheme_id", ""),
                    "column": col,
                    "href_examples": hrefs[:5],
                    "original_excerpt": old[:300],
                    "cleaned_excerpt": new[:300]
                })

report = {
    "original_rows": len(before),
    "cleaned_rows": len(after),
    "nonempty_values_changed_to_empty_count": len(changed_to_empty),
    "changed_to_empty_examples": changed_to_empty[:50],
    "html_link_examples": html_link_examples,
    "note": "Audit only. Neither CSV was modified."
}
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({
    "original_rows": len(before),
    "cleaned_rows": len(after),
    "nonempty_values_changed_to_empty_count": len(changed_to_empty),
    "changed_to_empty_examples": changed_to_empty[:10],
    "html_link_examples": html_link_examples[:5],
    "report": str(output)
}, ensure_ascii=False, indent=2))
