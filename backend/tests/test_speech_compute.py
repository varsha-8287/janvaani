import httpx
import pytest

from app.speech.bhashini_client import BhashiniClient
from app.speech.config import BhashiniSettings
from app.speech.inference_config import InferenceEndpoint


@pytest.fixture
def endpoint():
    return InferenceEndpoint(
        callback_url="https://example.invalid/inference",
        auth_header_name="Authorization",
        auth_header_value="test-only-token",
        is_sync=True,
    )


@pytest.fixture
def client():
    settings = BhashiniSettings(
        user_id="test-user",
        ulca_api_key="test-key",
    )
    return settings


def test_asr_compute_payload(client, endpoint):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={"pipelineResponse": [{"taskType": "asr"}]},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        api = BhashiniClient(client, http_client)
        result = api.transcribe_audio(
            endpoint=endpoint,
            audio_base64="dGVzdC1hdWRpbw==",
            source_language="hi",
            service_id="test-asr-service",
        )

    assert result["pipelineResponse"][0]["taskType"] == "asr"
    assert len(requests) == 1
    assert requests[0].headers["Authorization"] == "test-only-token"

    payload = requests[0].read().decode()
    assert '"taskType":"asr"' in payload
    assert '"sourceLanguage":"hi"' in payload
    assert '"audioFormat":"wav"' in payload
    assert '"audioContent":"dGVzdC1hdWRpbw=="' in payload


def test_tts_compute_payload(client, endpoint):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={"pipelineResponse": [{"taskType": "tts"}]},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        api = BhashiniClient(client, http_client)
        result = api.synthesize_speech(
            endpoint=endpoint,
            text="Namaste",
            source_language="en",
            service_id="test-tts-service",
        )

    assert result["pipelineResponse"][0]["taskType"] == "tts"
    payload = requests[0].read().decode()
    assert '"taskType":"tts"' in payload
    assert '"source":"Namaste"' in payload
    assert '"gender":"female"' in payload


def test_tts_rejects_invalid_speed(client, endpoint):
    api = BhashiniClient(client)

    with pytest.raises(ValueError, match="speed"):
        api.synthesize_speech(
            endpoint=endpoint,
            text="Hello",
            source_language="en",
            service_id="test-tts-service",
            speed=3.0,
        )
