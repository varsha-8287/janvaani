# Mapping to current Janvaani PostgreSQL schema

The current schema (`schemes`, `scheme_versions`, `source_documents`, `profiles`) is enough for a first reviewed release, but it does not yet persist all desired metadata.

## Existing mapping
- `schemes`: stable slug/title/administering_authority/government_level/status.
- `scheme_versions`: version_number/language/description/benefits/eligibility_criteria/required_documents/application_process/validity/review_status.
- `source_documents`: version_id/source_url/publisher/retrieved_at/content_hash/language/review_status.
- `profiles`: user-specific profile, not scheme corpus metadata.

## Important gaps for the full dataset
1. `schemes.government_level` currently supports `central`, `state`, `local`, `other`, but not `union_territory`. Represent UT-level schemes using `state` plus a canonical UT applicability code until the enum/check constraint is deliberately migrated; do not silently add a value the database rejects.
2. `source_documents` has no license/reuse basis, document title, acquisition method, source section/page, source language provenance, reviewer ID, or reviewed timestamp.
3. `scheme_versions` has no explicit translation review metadata or structured category/applicability columns; keep those in version JSON until a planned migration.
4. No dedicated audit log, alias/external-ID table, deduplication decision table, or translation table exists.
5. `source_documents.content_hash` currently hashes canonical scheme content in the ingestion service, not necessarily the actual downloaded source bytes. Do not label it a raw-document hash unless ingestion is updated to hash retained source bytes.

## Recommended later migration
Add `scheme_aliases` / `scheme_external_ids`, `scheme_review_events`, `source_document_metadata` (or extend source_documents), and translation status/reviewer metadata. Make schema changes through Alembic and test against `janvaani_dev` first, then `janvaani_test` with the approved migration process.

## API contract
The current ingestion API stores one version and one source document. The full dataset pipeline should stage/validate records before invoking ingestion. It should preserve the actual source retrieval timestamp and exact source document UUID when building Eligibility Contract v1. Do not submit criteria with placeholder source IDs.
