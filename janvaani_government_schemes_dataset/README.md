# Janvaani Government Schemes Dataset

## Status
This package is the versioned dataset structure and collection/review workflow for Janvaani. It is **not a complete populated dataset**. It intentionally contains no invented eligibility thresholds, benefits, document lists, translations, or approval claims.

## Scope
- Central schemes, all 28 states, and all 8 Union Territories (validate geography against the current Government of India directory at ingestion time).
- English plus the language codes in Janvaani's canonical app language registry. Import that registry instead of maintaining a second hard-coded language list.
- Full records: catalogue metadata, applicability, benefits, machine-readable eligibility rules, required documents, application steps, official sources, retrieval timestamps, content hashes, translation state, and review state.

## Files
- `manifest.json`: scope, status, policy.
- `schemas/scheme-record.schema.json`: machine-readable record contract.
- `templates/*.csv`: normalized collection templates.
- `sources/source_registry.json`: authorized/official discovery source register and reuse cautions.
- `docs/INGESTION_AND_REVIEW.md`: operational workflow.
- `docs/SCHEMA_MAPPING.md`: mapping to Janvaani's existing SQLAlchemy models.

## Source policy
1. Prefer the administering ministry/department's official scheme guideline/notification page.
2. Use `data.gov.in` only where the specific resource/API license and terms permit the intended reuse.
3. Do not bulk scrape/copy myScheme. Its current Terms of Use prohibit bots/scrapers and automatic copying without express written authorization. Ask the platform owner for written permission or an authorized export/API.
4. National Portal of India can be used for discovery and navigation; its scheme section says content is sourced from myScheme, so it does not bypass myScheme's terms.
5. Secondary datasets and search results are discovery leads only, never the sole basis for high-stakes eligibility rules.
6. Every field that affects eligibility, benefits, documents, deadlines, or application must cite a source reference or be left unknown and sent to review.

## Current counts
The manifest's zero counts are intentional. They must not be replaced with fabricated totals. A complete all-India dataset is a staged data acquisition and review program, not something that can be truthfully represented as finished from a single generated file.

## First implementation task
Read the language registry from the Expo app, create a source acquisition manifest, then populate records only from authorized exports or manually reviewed official primary sources. Never change `record_status` to `approved` automatically.
