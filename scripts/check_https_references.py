import csv
import json
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlunparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "janvaani_government_schemes_dataset" / "reports" / "reference-issues.csv"
OUT_CSV = ROOT / "janvaani_government_schemes_dataset" / "reports" / "https-reference-check.csv"
OUT_JSON = ROOT / "janvaani_government_schemes_dataset" / "reports" / "https-reference-check-summary.json"

def candidate_https(url):
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() != "http" or not parsed.netloc:
        return None
    return urlunparse(("https", parsed.netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))

def check_url(url):
    result = {
        "original_url": url,
        "https_candidate": candidate_https(url),
        "status": "not_checked",
        "http_status": "",
        "final_url": "",
        "error": "",
    }
    candidate = result["https_candidate"]
    if not candidate:
        result["status"] = "not_http_candidate"
        return result

    # Try HEAD first; fall back to a small GET if the server rejects HEAD.
    for method in ("HEAD", "GET"):
        try:
            req = Request(
                candidate,
                method=method,
                headers={"User-Agent": "JanvaaniSourceReview/0.1 (manual verification workflow)"},
            )
            with urlopen(req, timeout=8) as response:
                result["http_status"] = response.status
                result["final_url"] = response.geturl()
                result["status"] = "https_reachable" if 200 <= response.status < 400 else "https_http_error"
                return result
        except HTTPError as exc:
            if method == "HEAD" and exc.code in (400, 403, 405, 501):
                continue
            result["http_status"] = exc.code
            result["final_url"] = exc.geturl() or candidate
            result["status"] = "https_http_error"
            result["error"] = f"HTTP {exc.code}"
            return result
        except (URLError, TimeoutError, OSError) as exc:
            if method == "HEAD":
                # Some servers handle GET but not HEAD; try GET once.
                result["error"] = str(exc)[:240]
                continue
            result["status"] = "https_connection_failed"
            result["error"] = str(exc)[:240]
            return result
    result["status"] = "https_connection_failed"
    return result

def main():
    if not INPUT.exists():
        raise SystemExit(f"Input report not found: {INPUT}")

    with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    jobs = []
    seen = set()
    for row in rows:
        raw_urls = (row.get("urls_detected") or "").split("|")
        for raw in raw_urls:
            url = raw.strip()
            if url.startswith("http://") and url not in seen:
                seen.add(url)
                jobs.append(url)

    results = {}
    # Modest concurrency; this checks candidates only and does not download page bodies intentionally.
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(check_url, url): url for url in jobs}
        for future in as_completed(futures):
            url = futures[future]
            try:
                results[url] = future.result()
            except Exception as exc:
                results[url] = {
                    "original_url": url,
                    "https_candidate": candidate_https(url),
                    "status": "checker_error",
                    "http_status": "",
                    "final_url": "",
                    "error": str(exc)[:240],
                }
            time.sleep(0.02)

    fields = [
        "csv_row", "scheme_id", "scheme_name", "issue",
        "original_reference_text", "original_url", "https_candidate",
        "status", "http_status", "final_url", "error",
    ]
    output_rows = []
    for row in rows:
        urls = [u.strip() for u in (row.get("urls_detected") or "").split("|") if u.strip()]
        if not urls:
            output_rows.append({
                "csv_row": row.get("csv_row", ""),
                "scheme_id": row.get("scheme_id", ""),
                "scheme_name": row.get("scheme_name", ""),
                "issue": row.get("issue", ""),
                "original_reference_text": row.get("references_original", ""),
                "original_url": "",
                "https_candidate": "",
                "status": "no_url_to_check",
                "http_status": "",
                "final_url": "",
                "error": "Reference field is empty or no URL was detected",
            })
        else:
            for url in urls:
                item = results.get(url, {
                    "https_candidate": candidate_https(url),
                    "status": "not_checked",
                    "http_status": "",
                    "final_url": "",
                    "error": "",
                })
                output_rows.append({
                    "csv_row": row.get("csv_row", ""),
                    "scheme_id": row.get("scheme_id", ""),
                    "scheme_name": row.get("scheme_name", ""),
                    "issue": row.get("issue", ""),
                    "original_reference_text": row.get("references_original", ""),
                    "original_url": url,
                    "https_candidate": item.get("https_candidate", ""),
                    "status": item.get("status", ""),
                    "http_status": item.get("http_status", ""),
                    "final_url": item.get("final_url", ""),
                    "error": item.get("error", ""),
                })

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output_rows)

    counts = Counter(item.get("status", "unknown") for item in results.values())
    counts["no_url_to_check"] = sum(1 for r in output_rows if r["status"] == "no_url_to_check")
    summary = {
        "input_records": len(rows),
        "unique_http_urls_tested": len(jobs),
        "candidate_status_counts": dict(counts),
        "outputs": {
            "csv": str(OUT_CSV),
            "summary_json": str(OUT_JSON),
        },
        "caveats": [
            "HTTPS candidates are generated by changing only the URL scheme for testing; this does not prove the HTTPS URL is canonical or official.",
            "No original CSV or reference field was changed.",
            "Reachability does not prove source authority, accuracy, freshness, or reuse permission.",
            "Empty reference records need manual source research.",
        ],
    }
    OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
