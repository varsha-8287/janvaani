# Janvaani NLP — Implementation & Verification Checklist

**Document Purpose**: Internal technical audit and verification tracking document supporting the academic submission of the Janvaani NLP Final Project Implementation Report.
**Date**: October 2026
**Target Repository**: `janvaani` (FastAPI backend + Expo React Native mobile client)

---

## 1. Source Materials and Document Audit

| Source Document | Expected Content | Actual Location / Status | Verified Notes |
| :--- | :--- | :--- | :--- |
| **DA-1 Report Document** | Problem statement, 15-paper literature survey, proposed architecture, evaluation plan | `DA1_Problem_Literature_Statement_Architecture.docx` (Root directory, 261 KB) | Fully verified and extracted. Contains exact rubric mappings, stakeholder analysis, and research gaps. |
| **Proposed Solution Brief** | Executive architecture summary, novelty definition | `Proposed_Solution.docx` (Parent directory, 6 KB) | Verified and extracted. Defines Evidence-Aware Eligibility and Application-Readiness Layer. |
| **Supplied Literature PDFs** | 11 research papers referenced in DA-1 | `../` (Parent directory, 11 PDF files) | All 11 PDFs converted and analyzed (authors, methodology, findings, limitations verified). |
| **Additional Public-Sector Papers** | References [14] and [15] from *Government Information Quarterly* | Detailed in DA-1 Table 1 | Citations and findings recorded in literature review matrix. |
| **Database Migration History** | Initial schema and conversation history | `backend/migrations/versions/` (2 revision scripts) | Revisions `8683abb215e8` and `8f2c3b4e5d6a` verified. Backup SQL file exists. |
| **Dataset & Audit Reports** | Ingestion audits, validation logs, pilot schemes | `janvaani_government_schemes_dataset/reports/` (17 report files) | 3,534 raw records, 3,437 schema-valid, 97 invalid, 8 pilot schemes verified. |

---

## 2. Test Execution and Numerical Verification

| Verification Category | Target Command | Environment Tested | Observed Result | Evidence Location / Log |
| :--- | :--- | :--- | :--- | :--- |
| **Backend Test Suite** | `pytest` | Python 3.12.4, PostgreSQL 16 (Local), Windows 11 | **320 passed, 3 skipped, 0 failed** in 84.92s (323 items collected) | `backend/tests/` (Task-149 log) |
| **Mobile API Contract Tests** | `npm test` | Node 20+, Node Test Runner with experimental strip-types | **8 passed, 0 failed** (195ms) | `apps/mobile/scripts/test-api-contract.js` |
| **Mobile TypeScript Compilation** | `npm run typecheck` | TypeScript 5.8 (`tsc --noEmit`) | **0 errors, exit code 0** | `apps/mobile/tsconfig.json` (Task-174 log) |
| **Android JavaScript Export** | `npx expo export --platform android` | Metro Bundler, Expo SDK 57 | **645 modules bundled, 2 assets bundled, exit code 0** | `apps/mobile/dist/` (Task-227 log) |
| **Database E2E Suite** | `pytest tests/test_e2e_postgresql.py` | Local PostgreSQL `janvaani_dev` | **7 passed, 0 failed** | Included in 320 passed suite |
| **Skipped Backend Tests** | Transaction rollback tests | SQLite fallback / mock session | **3 skipped** (`test_ingestion_transactions.py`) | Tests require specific multi-nested session engine |

---

## 3. Discrepancy Analysis (DA-1 Proposed vs. Codebase Implementation)

| Architectural Area | Proposed in DA-1 | Implemented in Codebase | Discrepancy Classification & Practical Rationale |
| :--- | :--- | :--- | :--- |
| **Frontend Framework** | Proposed Flutter / Web UI in preliminary diagram | React Native with Expo SDK 57 and TypeScript | **Architecture Evolution**: Expo chosen for multiplatform native Android/iOS bundling and native device module integration (Camera, Audio recording, Safe Area). |
| **Government Data Ingestion** | Explored real-time scraping vs. versioned knowledge base | Offline versioned staging repository with schema validation and dry-run scripts | **Intentional Architectural Constraint**: DA-1 explicitly mandated avoiding unstable live scraping. Versioned staging repository implemented. |
| **Dense Retrieval / Embeddings** | Proposed Multilingual SentenceTransformers / Vector DB | Lexical BM25 chunking + keyword overlap + Gemini Flash RAG grounding | **Implementation Scope**: Current backend implements verified keyword chunking (`chunk_text`, `retrieve_chunks`) with Gemini Flash LLM grounding. |
| **Primary Document OCR** | Proposed Bhashini OCR as primary | Bhashini OCR client implemented with automatic fallback to Gemini Vision OCR | **Provider Provisioning Workaround**: Live Bhashini OCR pipeline was unprovisioned on ULCA; Gemini Vision fallback handles PDFs and images deterministically. |
| **ASR English Language Handling** | Independent English acoustic model | Multilingual fallback mapping (`candidate_languages = [language, "hi"]`) | **Service Constraint**: When English ASR is requested on Bhashini pipelines lacking English acoustic models, it falls back to Hindi ASR endpoint. |
| **Formal Model Benchmarking** | Proposed Precision/Recall/F1 over 1,000 synthetic profiles | 320 unit/integration tests and pilot scheme verification (8 schemes) | **Academic Boundary**: Functional software verification demonstrated; full empirical human/synthetic benchmarking remains future academic work. |

---

## 4. Live Services & Physical Device Limitations

The following items are functional in code and tested via contract/mock suites, but have live operational boundaries:

1. **Physical Device Live Network Access**:
   - The mobile client defaults to `http://10.216.94.61:8000` or Android emulator `http://10.0.2.2:8000`. On physical devices, cleartext traffic is permitted (`android:usesCleartextTraffic="true"`) strictly for local LAN debugging. Production deployments require TLS/HTTPS with public DNS.
2. **External AI Credentials**:
   - Gemini Vision and Gemini Chat require a valid `GEMINI_API_KEY`. In the absence of an API key, the retrieval service returns `INSUFFICIENT_EVIDENCE` fallback responses rather than hallucinating answers.
3. **Bhashini ULCA API Credentials**:
   - Requires active `BHASHINI_USER_ID`, `BHASHINI_API_KEY`, and `BHASHINI_PIPELINE_ID`. If credentials expire or tasks are unprovisioned, graceful fallback occurs (Gemini Vision for OCR, native Expo Speech for TTS).
4. **Official Scheme Status**:
   - Although 3,437 records pass JSON schema validation, all 3,534 records remain in `pending_review` status. Zero schemes have been approved for automated production release without administrative human review.
