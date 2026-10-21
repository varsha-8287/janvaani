
import httpx
import pytest

from app.speech.bhashini_client import (
    BhashiniAPIError,
    BhashiniClient,
)
from app.speech.config import BhashiniSettings, PIPELINE_CONFIG_URL


@pytest.fixture
def settings():
    return BhashiniSettings(
        user_id="test-user",
        ulca_api_key="test-key",
    )


def test_asr_pipeline_config_request(settings):
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"pipelineResponseConfig": []})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = BhashiniClient(settings, client).get_pipeline_config("asr")

    assert result == {"pipelineResponseConfig": []}
    assert len(requests) == 1
    assert str(requests[0].url) == PIPELINE_CONFIG_URL
    assert requests[0].headers["userID"] == "test-user"
    assert requests[0].headers["ulcaApiKey"] == "test-key"


def test_rejects_unsupported_task(settings):
    client = BhashiniClient(settings)

    with pytest.raises(ValueError, match="task_type"):
        client.get_pipeline_config("translation")


def test_http_error_is_sanitized(settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="upstream unavailable")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        api = BhashiniClient(settings, client)

        with pytest.raises(
            BhashiniAPIError,
            match="configuration request failed",
        ):
            api.get_pipeline_config("asr")


def test_invalid_json_is_sanitized(settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"not-json",
            headers={"Content-Type": "application/json"},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        api = BhashiniClient(settings, client)

        with pytest.raises(BhashiniAPIError, match="invalid JSON"):
            api.get_pipeline_config("asr")
