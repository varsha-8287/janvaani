# Janvaani NLP — Multilingual AI Government Scheme Discovery & Document Readiness

Janvaani is a multilingual, citizen-centric mobile and backend platform designed to empower citizens (specifically farmers and rural communities) to discover government schemes, assess criteria eligibility, interact with a conversational AI companion in their local language, and scan/review verification documents using OCR.

---

## 1. System Architecture

- **Backend**: FastAPI, Python 3.12+, SQLAlchemy ORM, Alembic migrations, PostgreSQL (`janvaani_dev`).
- **Mobile Frontend**: React Native, Expo SDK 57, TypeScript, React Navigation with Safe Area Context.
- **AI & RAG Engine**: Gemini Flash for multilingual query answering and scheme evidence grounding, with BM25/hybrid retrieval and official scheme citation generation.
- **Document OCR**: Bhashini OCR with automatic graceful fallback to Gemini Vision OCR (`authenticity_verified: false`, `review_required: true`).
- **Speech Integration**: Bhashini ASR (Speech-to-Text) and TTS (Text-to-Speech) supporting Indian regional languages.
- **Localization**: Unified i18n engine across all screens, tabs, and modals with English and Hindi support and regional language fallbacks.

---

## 2. Local Backend Setup

### Prerequisites
- Python 3.12+
- PostgreSQL 16+ running locally or reachable via network
- Virtual environment in repository root (`.venv`)

### Installation & Virtual Environment
```bash
# From repository root
cd backend
..\.venv\Scripts\activate
pip install -r requirements.txt
```

### Environment Configuration
Configure your development environment in `backend/.env`. Example (safe template):
```env
# Database
DATABASE_URL=postgresql+psycopg://postgres:<PASSWORD>@127.0.0.1:5432/janvaani_dev

# AI & Providers (Never commit real API keys)
GEMINI_API_KEY=your_gemini_api_key_here
BHASHINI_USER_ID=your_bhashini_user_id
BHASHINI_API_KEY=your_bhashini_api_key
BHASHINI_PIPELINE_ID=your_bhashini_pipeline_id

# Security
ALLOW_DEVELOPMENT_TOKEN=true
DEVELOPMENT_CITIZEN_UID=local-dev-citizen
DEVELOPMENT_REVIEWER_UID=local-dev-reviewer
```

### Database Migration
The database currently contains schema through revision `8683abb215e8`. To apply the persistent chat conversation history tables (`conversations`, `chat_messages`):
```bash
cd backend
alembic upgrade head
```
*(Verify local database target and credentials prior to running against development or staging environments).*

### Starting FastAPI Development Server
To make the backend reachable from Android emulators, physical phones on LAN, and web browsers:
```bash
cd backend
..\.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- **Swagger Interactive API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **Database Health**: [http://localhost:8000/health/db](http://localhost:8000/health/db)

---

## 3. Mobile Application Setup

### Prerequisites
- Node.js 18+ (Node 20+ LTS recommended)
- Android Studio / Android SDK (for physical device or emulator testing)
- Expo CLI

### Installation
```bash
cd apps/mobile
npm install
```

### API Base URL Configuration
The mobile app automatically selects the appropriate API URL, or can be explicitly configured via `EXPO_PUBLIC_API_URL`:
- **Physical Android Phone (on local LAN)**: `http://<YOUR_DEV_PC_LAN_IP>:8000` (e.g. `http://10.216.94.61:8000`)
- **Android Emulator**: `http://10.0.2.2:8000`
- **Web Browser**: `http://localhost:8000`

To set the IP address in development without rebuilding:
```bash
# In apps/mobile/.env
EXPO_PUBLIC_API_URL=http://10.216.94.61:8000
```
*(Note: Clean native builds inline environment variables at build-time. For already-built APKs, update `client.ts` dynamic base URL setter or rebuild the APK).*

### Starting the Expo Development Server
```bash
cd apps/mobile
npm run start
```

### Running on Android Device / Emulator
```bash
cd apps/mobile
npm run android
```

---

## 4. Automated Testing

### Backend Test Suite
Runs all 314 tests including schema validation, chatbot turns, RAG retrieval benchmarks, OCR fallback, profile operations, and eligibility rules:
```bash
cd backend
..\.venv\Scripts\pytest -v
```
Expected output: `311 passed, 3 skipped, 0 failed`.

### Mobile Typecheck
Validates all TypeScript interfaces and components across the mobile application:
```bash
cd apps/mobile
npm run typecheck
```
Expected output: `tsc --noEmit` exits with 0 errors.

### Mobile API Contract Tests
Validates client payload serialization, timeouts, non-idempotent mutation safety, authorization header injection, eligibility status handling, and OCR response invariants:
```bash
cd apps/mobile
npm test
```
Expected output: `8 passed, 0 failed`.

---

## 5. Security & Invariant Rules

1. **OCR Safety Invariant**: Machine-extracted documents are strictly for citizen review and convenience.
   - `authenticity_verified` is always `false`.
   - `review_required` is always `true`.
   - Extracted data is only saved to a citizen profile upon explicit confirmation.
2. **Cleartext Traffic Policy**: `android:usesCleartextTraffic="true"` is enabled strictly for local development LAN debugging (`http://10.x.x.x`). Production release builds must enforce HTTPS.
3. **Non-Idempotent Operations**: The central API client will never auto-retry non-idempotent operations (POST / PATCH / DELETE) to prevent duplicate transactions, messages, or uploads.
4. **Credential Isolation**: Secrets, API keys, tokens, and citizen documents are never logged or stored in repository source code.
