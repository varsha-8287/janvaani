import pytest

from app.speech.bhashini_client import BhashiniAPIError
from app.speech.inference_config import parse_inference_endpoint


def test_parses_inference_endpoint():
    response = {
        "pipelineInferenceAPIEndPoint": {
            "callbackUrl": "https://example.invalid/inference",
            "inferenceApiKey": {
                "name": "Authorization",
                "value": "test-only-token",
            },
            "isSyncApi": True,
        }
    }

    result = parse_inference_endpoint(response)

    assert result.callback_url == "https://example.invalid/inference"
    assert result.auth_header_name == "Authorization"
    assert result.auth_header_value == "test-only-token"
    assert result.is_sync is True


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"pipelineInferenceAPIEndPoint": None},
        {"pipelineInferenceAPIEndPoint": {}},
        {
            "pipelineInferenceAPIEndPoint": {
                "callbackUrl": "https://example.invalid/inference",
                "inferenceApiKey": {"name": "Authorization"},
            }
        },
        {
            "pipelineInferenceAPIEndPoint": {
                "callbackUrl": "http://example.invalid/inference",
                "inferenceApiKey": {
                    "name": "Authorization",
                    "value": "test-only-token",
                },
            }
        },
    ],
)
def test_rejects_invalid_endpoint_config(response):
    with pytest.raises(BhashiniAPIError):
        parse_inference_endpoint(response)
