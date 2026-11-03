"""Tests for document OCR extraction, validation, profile conflict detection, and fallbacks."""

import base64
from unittest.mock import MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.auth import CurrentUser, get_current_user
from app.database.base import Base
from app.database.models import Profile
from app.database.session import get_db
from app.documents.bhashini_ocr_client import (
    BhashiniOCRClient,
    BhashiniOCRSettings,
    OCRConfigurationError,
)
from app.documents.ocr_service import (
    GeminiVisionOCRProvider,
    OCRService,
    OCRServiceError,
    OCRValidationError,
    extract_regex_fields,
    validate_file_payload,
)
from app.documents.router import get_optional_current_user
from app.main import app
from app.speech.errors import BhashiniAPIError
from app.speech.inference_config import InferenceEndpoint

VALID_JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb"
VALID_PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
VALID_WEBP_BYTES = b"RIFF\x1a\x00\x00\x00WEBPVP8 \x0e\x00\x00\x00"
VALID_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


@pytest.fixture
def in_memory_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(in_memory_db):
    def override_db():
        yield in_memory_db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client, in_memory_db
    app.dependency_overrides.clear()


# --- Unit Tests: Regex Field Extraction ---


def test_extract_regex_fields_hindi_income():
    text = "प्रमाण पत्र संख्या: 123\nवार्षिक आय: रु 50,000\nजारी दिनांक: 15/08/2023"
    fields = extract_regex_fields(text, "income_certificate")
    assert fields.get("annual_income") == 50000.0
    assert fields.get("issue_date") == "2023-08-15"


def test_extract_regex_fields_english_income():
    text = "GOVERNMENT OF TAMIL NADU\nTotal Income: INR 1,20,000.50\nIssue Date: 2024-02-28"
    fields = extract_regex_fields(text, "income_certificate")
    assert fields.get("annual_income") == 120000.50
    assert fields.get("issue_date") == "2024-02-28"


def test_extract_regex_fields_empty():
    assert extract_regex_fields("", "income_certificate") == {}


# --- Unit Tests: Payload Validation ---


def test_validate_file_payload_success():
    validate_file_payload(VALID_JPEG_BYTES, "image/jpeg")
    validate_file_payload(VALID_PNG_BYTES, "image/png")
    validate_file_payload(VALID_WEBP_BYTES, "image/webp")
    validate_file_payload(VALID_PDF_BYTES, "application/pdf")


def test_validate_file_payload_empty():
    with pytest.raises(OCRValidationError, match="must not be empty"):
        validate_file_payload(b"", "image/jpeg")


def test_validate_file_payload_oversized():
    huge = b"\xff\xd8\xff" + b"0" * (10 * 1024 * 1024 + 1)
    with pytest.raises(OCRValidationError, match="exceeds maximum allowed size"):
        validate_file_payload(huge, "image/jpeg")


def test_validate_file_payload_unsupported_mime():
    with pytest.raises(OCRValidationError, match="Unsupported media type"):
        validate_file_payload(b"hello text", "text/plain")


def test_validate_file_payload_magic_mismatch():
    with pytest.raises(OCRValidationError, match="do not match expected signature"):
        validate_file_payload(b"fake jpeg content", "image/jpeg")


# --- Unit Tests: Bhashini OCR Client ---


def test_bhashini_ocr_client_parse_service_id():
    config = {
        "pipelineResponseConfig": [
            {
                "taskType": "ocr",
                "config": [
                    {
                        "serviceId": "ai4bharat/indic-ocr-hi",
                        "language": {"sourceLanguage": "hi"},
                    },
                    {
                        "serviceId": "ai4bharat/indic-ocr-ta",
                        "language": {"sourceLanguage": "ta"},
                    },
                ],
            }
        ]
    }
    svc_hi = BhashiniOCRClient.parse_ocr_service_id(config, "hi")
    assert svc_hi == "ai4bharat/indic-ocr-hi"

    svc_ta = BhashiniOCRClient.parse_ocr_service_id(config, "ta")
    assert svc_ta == "ai4bharat/indic-ocr-ta"


def test_bhashini_ocr_client_parse_service_id_fallback():
    config = {
        "pipelineResponseConfig": [
            {
                "taskType": "ocr",
                "config": [
                    {
                        "serviceId": "ai4bharat/generic-ocr",
                    }
                ],
            }
        ]
    }
    svc = BhashiniOCRClient.parse_ocr_service_id(config, "kn")
    assert svc == "ai4bharat/generic-ocr"


def test_bhashini_ocr_client_parse_service_id_missing():
    config = {"pipelineResponseConfig": []}
    with pytest.raises(BhashiniAPIError, match="No OCR task found"):
        BhashiniOCRClient.parse_ocr_service_id(config, "hi")


def test_bhashini_ocr_client_parse_ocr_response():
    resp = {
        "pipelineResponse": [
            {
                "taskType": "ocr",
                "output": [
                    {"source": "प्रमाण पत्र संख्या: 1234"},
                    {"source": "वार्षिक आय: 50000"},
                ],
            }
        ]
    }
    text = BhashiniOCRClient._parse_ocr_response(resp)
    assert text == "प्रमाण पत्र संख्या: 1234\nवार्षिक आय: 50000"


def test_bhashini_ocr_client_parse_ocr_response_empty():
    resp = {"pipelineResponse": [{"taskType": "ocr", "output": []}]}
    with pytest.raises(BhashiniAPIError, match="did not return recognized text"):
        BhashiniOCRClient._parse_ocr_response(resp)


def test_bhashini_ocr_client_extract_text_empty_input():
    client = BhashiniOCRClient(BhashiniOCRSettings(user_id="u", ulca_api_key="k"))
    endpoint = InferenceEndpoint(
        callback_url="https://example.com/compute",
        auth_header_name="Auth",
        auth_header_value="val",
        is_sync=True,
    )
    with pytest.raises(ValueError, match="must not be empty"):
        client.extract_text(endpoint, "", "hi", "service1")


# --- Unit Tests: Gemini Vision OCR Provider ---


def test_gemini_vision_provider_not_configured():
    provider = GeminiVisionOCRProvider(api_key="")
    assert provider.is_available() is False
    with pytest.raises(OCRServiceError, match="not configured"):
        provider.extract(VALID_JPEG_BYTES, "image/jpeg")


def test_gemini_vision_provider_success():
    provider = GeminiVisionOCRProvider(api_key="fake-key")

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = '{"raw_text": "Income Certificate\\nAnnual Income: 75000", "fields": {"annual_income": 75000, "issue_date": "2023-11-05"}}'
    mock_client.models.generate_content.return_value = mock_resp

    with patch("google.genai.Client", return_value=mock_client):
        raw_text, fields = provider.extract(VALID_JPEG_BYTES, "image/jpeg", "income_certificate", "en")

    assert "Income Certificate" in raw_text
    assert fields.get("annual_income") == 75000
    assert fields.get("issue_date") == "2023-11-05"


# --- API Endpoint Integration Tests ---


def test_extract_endpoint_empty_payload(client):
    test_client, _ = client
    resp = test_client.post(
        "/api/documents/extract",
        headers={"Content-Type": "image/jpeg"},
        content=b"",
    )
    assert resp.status_code == 400
    assert "must not be empty" in resp.json()["detail"]


def test_extract_endpoint_unsupported_media_type(client):
    test_client, _ = client
    resp = test_client.post(
        "/api/documents/extract",
        headers={"Content-Type": "text/plain"},
        content=b"some plain text",
    )
    assert resp.status_code == 415
    assert "Unsupported media type" in resp.json()["detail"]


def test_extract_endpoint_magic_mismatch(client):
    test_client, _ = client
    resp = test_client.post(
        "/api/documents/extract",
        headers={"Content-Type": "image/jpeg"},
        content=b"this is not jpeg binary data",
    )
    assert resp.status_code == 400
    assert "do not match expected signature" in resp.json()["detail"]


def test_extract_endpoint_unsupported_language(client):
    test_client, _ = client
    resp = test_client.post(
        "/api/documents/extract?language=xx",
        headers={"Content-Type": "image/jpeg"},
        content=VALID_JPEG_BYTES,
    )
    assert resp.status_code == 422
    assert "Unsupported language 'xx'" in resp.json()["detail"]


def test_extract_endpoint_bhashini_success(client):
    test_client, _ = client

    mock_bhashini = MagicMock(spec=BhashiniOCRClient)
    mock_bhashini.extract_document_text.return_value = (
        "प्रमाण पत्र संख्या: 9876\nवार्षिक आय: रु 55,000\nजारी दिनांक: 2023-10-12"
    )

    with patch("app.documents.ocr_service.OCRService._get_bhashini_client", return_value=mock_bhashini):
        resp = test_client.post(
            "/api/documents/extract?document_type=income_certificate&language=hi",
            headers={"Content-Type": "image/jpeg"},
            content=VALID_JPEG_BYTES,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "bhashini"
    assert data["review_required"] is True
    assert data["authenticity_verified"] is False
    assert data["document_type"] == "income_certificate"
    assert data["fields"]["annual_income"] == 55000.0
    assert data["fields"]["issue_date"] == "2023-10-12"
    assert data["validation"]["valid"] is True
    assert data["validation"]["issues"] == []


def test_extract_endpoint_gemini_fallback_on_pdf(client):
    test_client, _ = client

    mock_gemini = MagicMock(spec=GeminiVisionOCRProvider)
    mock_gemini.is_available.return_value = True
    mock_gemini.extract.return_value = (
        "Annual Income: Rs 48000\nIssue Date: 2024-01-15",
        {"annual_income": 48000.0, "issue_date": "2024-01-15"},
    )

    with patch("app.documents.ocr_service.GeminiVisionOCRProvider", return_value=mock_gemini):
        resp = test_client.post(
            "/api/documents/extract?document_type=income_certificate&language=en",
            headers={"Content-Type": "application/pdf"},
            content=VALID_PDF_BYTES,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "gemini_vision"
    assert data["fields"]["annual_income"] == 48000.0
    assert data["validation"]["valid"] is True


def test_extract_endpoint_json_base64_mode(client):
    test_client, _ = client

    b64_str = base64.b64encode(VALID_JPEG_BYTES).decode("ascii")
    payload = {
        "file_base64": b64_str,
        "mime_type": "image/jpeg",
        "document_type": "income_certificate",
        "language": "hi",
    }

    mock_bhashini = MagicMock(spec=BhashiniOCRClient)
    mock_bhashini.extract_document_text.return_value = "वार्षिक आय: 60000"

    with patch("app.documents.ocr_service.OCRService._get_bhashini_client", return_value=mock_bhashini):
        resp = test_client.post(
            "/api/documents/extract",
            headers={"Content-Type": "application/json"},
            json=payload,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["fields"]["annual_income"] == 60000.0
    assert data["validation"]["valid"] is True


def test_extract_endpoint_invalid_base64_json(client):
    test_client, _ = client
    payload = {
        "file_base64": "!!!not_valid_base64!!!",
        "mime_type": "image/jpeg",
    }
    resp = test_client.post(
        "/api/documents/extract",
        headers={"Content-Type": "application/json"},
        json=payload,
    )
    assert resp.status_code == 400
    assert "Invalid base64 encoding" in resp.json()["detail"]


def test_extract_endpoint_invalid_income_format_reported(client):
    test_client, _ = client

    mock_bhashini = MagicMock(spec=BhashiniOCRClient)
    # Income parsed as negative or invalid
    mock_bhashini.extract_document_text.return_value = "Annual Income: -1000"

    with patch("app.documents.ocr_service.OCRService._get_bhashini_client", return_value=mock_bhashini):
        # Directly mock fields to return invalid negative income
        with patch("app.documents.ocr_service.extract_regex_fields", return_value={"annual_income": -1000}):
            resp = test_client.post(
                "/api/documents/extract?document_type=income_certificate",
                headers={"Content-Type": "image/jpeg"},
                content=VALID_JPEG_BYTES,
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["validation"]["valid"] is False
    assert len(data["validation"]["issues"]) == 1
    assert data["validation"]["issues"][0]["field_name"] == "annual_income"
    assert data["validation"]["issues"][0]["status"] == "INVALID"


def test_extract_endpoint_profile_conflict_detected(client):
    test_client, db = client

    # Create profile with income 45000
    profile = Profile(
        firebase_uid="citizen-conflict-user",
        preferred_language="en",
        attributes={"annual_income": 45000.0},
    )
    db.add(profile)
    db.commit()

    # Authenticate as citizen-conflict-user
    app.dependency_overrides[get_optional_current_user] = lambda: CurrentUser(uid="citizen-conflict-user")

    mock_bhashini = MagicMock(spec=BhashiniOCRClient)
    mock_bhashini.extract_document_text.return_value = "वार्षिक आय: 95000"

    with patch("app.documents.ocr_service.OCRService._get_bhashini_client", return_value=mock_bhashini):
        resp = test_client.post(
            "/api/documents/extract?document_type=income_certificate",
            headers={"Content-Type": "image/jpeg"},
            content=VALID_JPEG_BYTES,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["profile_conflicts"]) == 1
    conflict = data["profile_conflicts"][0]
    assert conflict["field_name"] == "annual_income"
    assert conflict["status"] == "CONFLICT"
    assert "differs from the profile claim" in conflict["explanation"]


def test_extract_endpoint_profile_match_no_conflict(client):
    test_client, db = client

    profile = Profile(
        firebase_uid="citizen-matching-user",
        preferred_language="en",
        attributes={"annual_income": 50000.0},
    )
    db.add(profile)
    db.commit()

    app.dependency_overrides[get_optional_current_user] = lambda: CurrentUser(uid="citizen-matching-user")

    mock_bhashini = MagicMock(spec=BhashiniOCRClient)
    mock_bhashini.extract_document_text.return_value = "वार्षिक आय: 50000"

    with patch("app.documents.ocr_service.OCRService._get_bhashini_client", return_value=mock_bhashini):
        resp = test_client.post(
            "/api/documents/extract?document_type=income_certificate",
            headers={"Content-Type": "image/jpeg"},
            content=VALID_JPEG_BYTES,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["profile_conflicts"] == []


def test_extract_endpoint_both_providers_fail(client):
    test_client, _ = client

    mock_bhashini = MagicMock(spec=BhashiniOCRClient)
    mock_bhashini.extract_document_text.side_effect = BhashiniAPIError("Bhashini timeout")

    mock_gemini = MagicMock(spec=GeminiVisionOCRProvider)
    mock_gemini.is_available.return_value = True
    mock_gemini.extract.side_effect = OCRServiceError("Gemini rate limit")

    with patch("app.documents.ocr_service.OCRService._get_bhashini_client", return_value=mock_bhashini):
        with patch("app.documents.ocr_service.GeminiVisionOCRProvider", return_value=mock_gemini):
            resp = test_client.post(
                "/api/documents/extract",
                headers={"Content-Type": "image/jpeg"},
                content=VALID_JPEG_BYTES,
            )

    assert resp.status_code == 502
    assert "Document OCR service failed" in resp.json()["detail"]


# --- Tests for Bhashini-Bodhan Model & Provider Selection ---


def test_bhashini_bodhan_model_id_configured_as_default():
    from app.documents.bhashini_ocr_client import DEFAULT_HINDI_OCR_MODEL_ID

    assert DEFAULT_HINDI_OCR_MODEL_ID == "6aa243f05786747464e05fc1"

    settings = BhashiniOCRSettings(user_id="u", ulca_api_key="k")
    assert settings.model_id is None

    with patch.dict("os.environ", {"BHASHINI_USER_ID": "u", "BHASHINI_ULCA_API_KEY": "k"}, clear=False):
        settings_env = BhashiniOCRSettings.from_env()
        assert settings_env.model_id == "6aa243f05786747464e05fc1"


def test_bhashini_ocr_client_compute_model_ocr_success():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "output": [
                    {"source": "प्रमाण पत्र संख्या: 998877\nवार्षिक आय: 40000"}
                ]
            },
        )

    settings = BhashiniOCRSettings(
        user_id="test-u",
        ulca_api_key="test-k",
        model_id="6aa243f05786747464e05fc1",
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as mock_http:
        client = BhashiniOCRClient(settings, http_client=mock_http)
        result = client.compute_model_ocr(
            image_base64="dGVzdA==",
            source_language="hi",
            model_id="6aa243f05786747464e05fc1",
        )

    assert "प्रमाण पत्र संख्या: 998877" in result
    assert len(requests) == 1
    assert "model/compute" in str(requests[0].url)
    assert requests[0].headers["userID"] == "test-u"
    assert requests[0].headers["ulcaApiKey"] == "test-k"


def test_bhashini_ocr_client_compute_model_ocr_upstream_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"code": "", "message": "OCR Model Compute Failed"})

    settings = BhashiniOCRSettings(user_id="u", ulca_api_key="k", model_id="6aa243f05786747464e05fc1")
    with httpx.Client(transport=httpx.MockTransport(handler)) as mock_http:
        client = BhashiniOCRClient(settings, http_client=mock_http)
        with pytest.raises(BhashiniAPIError, match="model compute failed with HTTP 500"):
            client.compute_model_ocr("dGVzdA==", source_language="hi")


def test_bhashini_ocr_client_compute_model_ocr_empty_input():
    settings = BhashiniOCRSettings(user_id="u", ulca_api_key="k")
    client = BhashiniOCRClient(settings)
    with pytest.raises(ValueError, match="must not be empty"):
        client.compute_model_ocr("", source_language="hi")


def test_extract_endpoint_explicit_provider_selection_gemini(client):
    test_client, _ = client

    mock_gemini = MagicMock(spec=GeminiVisionOCRProvider)
    mock_gemini.is_available.return_value = True
    mock_gemini.extract.return_value = (
        "Income: 70000",
        {"annual_income": 70000.0},
    )

    with patch("app.documents.ocr_service.GeminiVisionOCRProvider", return_value=mock_gemini):
        resp = test_client.post(
            "/api/documents/extract?preferred_provider=gemini_vision",
            headers={"Content-Type": "image/jpeg"},
            content=VALID_JPEG_BYTES,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "gemini_vision"
    assert data["fields"]["annual_income"] == 70000.0


def test_extract_endpoint_fallback_when_bhashini_fails_then_gemini_succeeds(client):
    test_client, _ = client

    mock_bhashini = MagicMock(spec=BhashiniOCRClient)
    mock_bhashini.extract_document_text.side_effect = BhashiniAPIError("OCR Model Compute Failed")

    mock_gemini = MagicMock(spec=GeminiVisionOCRProvider)
    mock_gemini.is_available.return_value = True
    mock_gemini.extract.return_value = (
        "Annual Income: 52000",
        {"annual_income": 52000.0},
    )

    with patch("app.documents.ocr_service.OCRService._get_bhashini_client", return_value=mock_bhashini):
        with patch("app.documents.ocr_service.GeminiVisionOCRProvider", return_value=mock_gemini):
            resp = test_client.post(
                "/api/documents/extract?preferred_provider=bhashini",
                headers={"Content-Type": "image/jpeg"},
                content=VALID_JPEG_BYTES,
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "gemini_vision"
    assert data["fields"]["annual_income"] == 52000.0


def test_extract_endpoint_identity_card_and_land_record_types_accepted(client):
    test_client, _ = client

    mock_gemini = MagicMock(spec=GeminiVisionOCRProvider)
    mock_gemini.is_available.return_value = True
    mock_gemini.extract.return_value = (
        "Name: John Doe Aadhaar: 1234 5678 9012",
        {"id_number": "123456789012"},
    )

    with patch("app.documents.ocr_service.GeminiVisionOCRProvider", return_value=mock_gemini):
        # 1. Test exact request from user observation: identity_card & language=en
        resp_id = test_client.post(
            "/api/documents/extract?document_type=identity_card&language=en&preferred_provider=gemini_vision",
            headers={"Content-Type": "image/jpeg"},
            content=VALID_JPEG_BYTES,
        )
        assert resp_id.status_code == 200
        data_id = resp_id.json()
        assert data_id["document_type"] == "identity_proof"
        assert data_id["authenticity_verified"] is False
        assert data_id["review_required"] is True

        # 2. Test land_record
        mock_gemini.extract.return_value = (
            "Land area: 1.8 hectares",
            {"land_hectares": 1.8},
        )
        resp_land = test_client.post(
            "/api/documents/extract?document_type=land_record&language=en&preferred_provider=gemini_vision",
            headers={"Content-Type": "image/jpeg"},
            content=VALID_JPEG_BYTES,
        )
        assert resp_land.status_code == 200
        data_land = resp_land.json()
        assert data_land["document_type"] == "land_record"
        assert data_land["authenticity_verified"] is False


