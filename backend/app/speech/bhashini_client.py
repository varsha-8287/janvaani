from typing import Any

import httpx

from app.speech.config import (
    IIT_MADRAS_PIPELINE_ID,
    PIPELINE_CONFIG_URL,
    BhashiniSettings,
)
from app.speech.inference_config import InferenceEndpoint

from app.speech.errors import BhashiniAPIError

class BhashiniClient:
    def __init__(
        self,
        settings: BhashiniSettings,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings
        self._http_client = http_client

    def get_pipeline_config(self, task_type: str) -> dict[str, Any]:
        if task_type not in {"asr", "tts"}:
            raise ValueError("task_type must be 'asr' or 'tts'.")

        payload = {
            "pipelineTasks": [{"taskType": task_type}],
            "pipelineRequestConfig": {
                "pipelineId": IIT_MADRAS_PIPELINE_ID,
            },
        }
        headers = {
            "userID": self.settings.user_id,
            "ulcaApiKey": self.settings.ulca_api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            if self._http_client is not None:
                response = self._http_client.post(
                    PIPELINE_CONFIG_URL,
                    headers=headers,
                    json=payload,
                    timeout=self.settings.timeout_seconds,
                )
            else:
                with httpx.Client(
                    timeout=self.settings.timeout_seconds
                ) as client:
                    response = client.post(
                        PIPELINE_CONFIG_URL,
                        headers=headers,
                        json=payload,
                    )

            response.raise_for_status()
            result = response.json()

        except httpx.HTTPError as exc:
            raise BhashiniAPIError(
                "BHASHINI pipeline configuration request failed."
            ) from exc
        except ValueError as exc:
            raise BhashiniAPIError(
                "BHASHINI returned invalid JSON."
            ) from exc

        if not isinstance(result, dict):
            raise BhashiniAPIError(
                "BHASHINI returned an unexpected configuration response."
            )

        return result

    def transcribe_audio(
        self,
        endpoint: InferenceEndpoint,
        audio_base64: str,
        source_language: str,
        service_id: str,
        sampling_rate: int = 16000,
    ) -> dict[str, Any]:
        """Submit base64-encoded WAV audio for ASR."""
        self._validate_nonempty(audio_base64, "audio_base64")
        self._validate_nonempty(source_language, "source_language")
        self._validate_nonempty(service_id, "service_id")

        if sampling_rate <= 0:
            raise ValueError("sampling_rate must be positive.")

        payload = {
            "pipelineTasks": [
                {
                    "taskType": "asr",
                    "config": {
                        "language": {
                            "sourceLanguage": source_language,
                        },
                        "serviceId": service_id,
                        "audioFormat": "wav",
                        "samplingRate": sampling_rate,
                        "preProcessors": ["vad"],
                        "postProcessors": ["itn"],
                    },
                }
            ],
            "inputData": {
                "audio": [{"audioContent": audio_base64}],
            },
        }

        return self._compute(endpoint, payload)

    def synthesize_speech(
        self,
        endpoint: InferenceEndpoint,
        text: str,
        source_language: str,
        service_id: str,
        gender: str = "female",
        speed: float = 1.0,
        sampling_rate: int = 48000,
    ) -> dict[str, Any]:
        """Submit text for TTS and return the provider response."""
        self._validate_nonempty(text, "text")
        self._validate_nonempty(source_language, "source_language")
        self._validate_nonempty(service_id, "service_id")

        if gender not in {"male", "female"}:
            raise ValueError("gender must be 'male' or 'female'.")

        if not 0.1 <= speed <= 1.99:
            raise ValueError("speed must be between 0.1 and 1.99.")

        if sampling_rate <= 0:
            raise ValueError("sampling_rate must be positive.")

        payload = {
            "pipelineTasks": [
                {
                    "taskType": "tts",
                    "config": {
                        "language": {
                            "sourceLanguage": source_language,
                        },
                        "serviceId": service_id,
                        "gender": gender,
                        "speed": speed,
                        "samplingRate": sampling_rate,
                        "audioFormat": "wav",
                    },
                }
            ],
            "inputData": {
                "input": [{"source": text}],
            },
        }

        return self._compute(endpoint, payload)

    def _compute(
        self,
        endpoint: InferenceEndpoint,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if not endpoint.callback_url.startswith("https://"):
            raise BhashiniAPIError("Invalid BHASHINI inference endpoint.")

        if not endpoint.auth_header_name or not endpoint.auth_header_value:
            raise BhashiniAPIError(
                "BHASHINI inference authentication is not configured."
            )

        if endpoint.auth_header_name.lower() in {
            "host",
            "content-length",
            "transfer-encoding",
        }:
            raise BhashiniAPIError(
                "BHASHINI returned an invalid authentication header name."
            )

        headers = {
            endpoint.auth_header_name: endpoint.auth_header_value,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        try:
            if self._http_client is not None:
                response = self._http_client.post(
                    endpoint.callback_url,
                    headers=headers,
                    json=payload,
                    timeout=self.settings.timeout_seconds,
                )
            else:
                with httpx.Client(
                    timeout=self.settings.timeout_seconds
                ) as client:
                    response = client.post(
                        endpoint.callback_url,
                        headers=headers,
                        json=payload,
                    )

            response.raise_for_status()
            result = response.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            content_type = exc.response.headers.get(
                "content-type", "unknown"
            )
            detail = "No provider error details available."

            try:
                body = exc.response.json()

                def find_error_message(value, depth=0):
                    if depth > 3:
                        return None

                    if isinstance(value, dict):
                        for key in ("message", "detail", "error_description"):
                            item = value.get(key)
                            if isinstance(item, str) and item.strip():
                                return item[:200]

                        for key in ("error", "errors", "data", "response"):
                            if key in value:
                                found = find_error_message(
                                    value[key], depth + 1
                                )
                                if found:
                                    return found

                    elif isinstance(value, list):
                        for item in value[:3]:
                            found = find_error_message(item, depth + 1)
                            if found:
                                return found

                    return None

                message = find_error_message(body)
                if message:
                    detail = message

            except ValueError:
                pass

            raise BhashiniAPIError(
                f"BHASHINI inference returned HTTP {status} "
                f"(content-type: {content_type}). {detail}"
            ) from exc

        except httpx.HTTPError as exc:
            raise BhashiniAPIError(
                "BHASHINI inference request failed due to a network or timeout error."
            ) from exc
        except ValueError as exc:
            raise BhashiniAPIError(
                "BHASHINI returned invalid inference JSON."
            ) from exc

        if not isinstance(result, dict):
            raise BhashiniAPIError(
                "BHASHINI returned an unexpected inference response."
            )

        return result

    @staticmethod
    def _validate_nonempty(value: str, name: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string.")
