# Ingestion, deduplication, verification and review workflow

## 1. Acquisition
For every source batch, retain:
- acquisition method (`manual`, `authorized_api`, `authorized_export`, `data.gov.in_resource`)
- permission/terms reference and date checked
- source publisher, URL/resource ID, retrieval timestamp in UTC
- original file/document checksum (SHA-256), language and parser version
- batch ID, operator and error report

Do not use myScheme bots/scrapers or automated copying unless written authorization expressly permits it. A public URL is not itself a reuse license.

## 2. Normalize to a staging area
Never ingest raw data directly into published tables. Normalize to the CSV templates/JSON schema and validate:
- required title, stable slug, government level and applicability
- URL uses HTTP(S); retrieval timestamps are timezone-aware
- dates and amounts preserve units/currency/frequency
- eligibility values are typed and use only supported operators
- each rule's `source_ref` resolves to an in-batch or existing source
- each translation carries language code and review state
- unknown values remain null/unknown rather than inferred

## 3. Deduplication
Use a candidate-generation pass followed by a human decision:
1. Exact external ID match (department portal ID / authorized source ID).
2. Normalized official title + administering authority + government level.
3. Canonical URL match after safe normalization (lowercase host, remove fragments and known tracking params; preserve meaningful query parameters).
4. Fuzzy title similarity only to create a review candidate; never auto-merge on fuzzy score alone.
5. Compare scope and policy lineage: a central umbrella scheme and a state implementation/component may be related but not duplicates.
6. Record decisions in `deduplication_queue.csv`: `same_scheme`, `version_or_renaming`, `related_component`, `distinct`, `needs_human_review`.
7. Preserve all source references and aliases on a merged record. Never delete provenance during merge.
8. Slug collision resolution: deterministic slug + short stable source identifier; do not change slugs after publication without alias mapping.

## 4. Provenance and source verification
A reviewer should verify:
- publisher is the administering government department or an authorized official portal
- source URL resolves and identifies the scheme/document
- content is current, with effective dates/expiry noted
- captured text/hash matches the retained document or permitted extract
- eligibility, benefit amounts, required documents, application steps and deadline are directly supported
- eligibility contract source IDs, URL and retrieval timestamp match database SourceDocument records exactly
- source licensing/reuse basis is documented

`source_status=verified` means reviewer verified the provenance and content, not that a URL merely exists. A placeholder URL such as example.gov.in must never be approved as real evidence.

## 5. Eligibility contract conversion
For each rule store:
- stable rule_id
- profile_field and operator from Janvaani's supported operator list
- typed expected_value
- human-readable explanation
- required flag
- exact source document reference and source location/page/section in staging metadata

If source text is ambiguous or rules require exceptions/complex formulae unsupported by the evaluator, mark the rule unsupported and route to manual review; do not simplify silently. Use `all`/`any` only when source wording supports it.

## 6. Translation
- Keep the official original text separate from translated text.
- Use machine translation only as a draft.
- Preserve legal/program names, amounts, units, dates and qualification terms.
- Require a fluent human review for eligibility, benefits, documents and application instructions before marking translation approved.
- Never treat a translation as a second independent source of truth.
- Load the canonical language codes from the Expo app's language registry; do not guess the supported list.

## 7. Review state machine
`discovered -> draft -> pending_review -> approved` (or `rejected`); later superseded/expired records can be archived.
- Only reviewers can submit/verify/approve.
- Source verification is performed while the version is pending review, as required by current API.
- Approval requires all sources verified and eligibility criteria valid.
- Never publish just because parsing or ingestion succeeded.
- Record reviewer identity, timestamps, rejection reason and content hash in audit logs (add audit fields/table if not already available).

## 8. Deduplication/versioning policy
- Stable scheme identity is `schemes.slug`.
- A material change to benefits/eligibility/source guidance should create a new `scheme_versions.version_number`, not overwrite an approved version.
- Keep previous approved versions for audit; set validity dates where official evidence supplies them.
- If multiple languages represent the same policy, they should share the stable scheme identity but have language-specific scheme versions as supported by current schema.
- Avoid creating separate schemes solely because of spelling/translation variants.

## 9. Release gates
Do not release a batch unless:
- schema validation passes
- all records have a primary official source and documented reuse basis
- no unresolved duplicate candidates remain in the release batch
- eligibility rules have source citations and typed values
- high-impact fields reviewed by a second person
- translation review is complete for released languages
- tests cover missing evidence, stale source, duplicate identity, invalid operator and unsupported rule
- counts by state/UT, category, language and review status are generated
