from dataclasses import dataclass
from typing import Any

from app.speech.errors import BhashiniAPIError

@dataclass(frozen=True)
class InferenceEndpoint:
    callback_url: str
    auth_header_name: str
    auth_header_value: str
    is_sync: bool


def parse_inference_endpoint(
    response: dict[str, Any],
) -> InferenceEndpoint:
    endpoint = response.get("pipelineInferenceAPIEndPoint")

    if not isinstance(endpoint, dict):
        raise BhashiniAPIError(
            "BHASHINI response is missing pipelineInferenceAPIEndPoint."
        )

    callback_url = endpoint.get("callbackUrl")
    api_key = endpoint.get("inferenceApiKey")

    if not isinstance(callback_url, str) or not callback_url.strip():
        raise BhashiniAPIError(
            "BHASHINI response is missing the inference callback URL."
        )

    if not isinstance(api_key, dict):
        raise BhashiniAPIError(
            "BHASHINI response is missing inference authentication details."
        )

    name = api_key.get("name")
    value = api_key.get("value")

    if (
        not isinstance(name, str)
        or not name.strip()
        or not isinstance(value, str)
        or not value.strip()
    ):
        raise BhashiniAPIError(
            "BHASHINI returned invalid inference authentication details."
        )

    if not callback_url.startswith("https://"):
        raise BhashiniAPIError(
            "BHASHINI returned an invalid inference callback URL."
        )

    return InferenceEndpoint(
        callback_url=callback_url,
        auth_header_name=name,
        auth_header_value=value,
        is_sync=endpoint.get("isSyncApi") is True,
    )
