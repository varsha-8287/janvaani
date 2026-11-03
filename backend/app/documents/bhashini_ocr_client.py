"""Client for Digital India Bhashini ULCA OCR pipeline inference."""

import base64
from dataclasses import dataclass
from typing import Any

import httpx

from app.speech.config import PIPELINE_CONFIG_URL
from app.speech.errors import BhashiniAPIError
from app.speech.inference_config import InferenceEndpoint, parse_inference_endpoint

MODEL_COMPUTE_URL = (
    "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/compute"
)
DEFAULT_HINDI_OCR_MODEL_ID = "6aa243f05786747464e05fc1"  # Bhashini-Bodhan OCR - Hindi


class OCRConfigurationError(RuntimeError):
    """Raised when OCR provider settings are missing or invalid."""


@dataclass(frozen=True)
class BhashiniOCRSettings:
    """Settings for Bhashini OCR pipeline and model inference."""

    user_id: str
    ulca_api_key: str
    pipeline_id: str | None = None
    model_id: str | None = None
    timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "BhashiniOCRSettings":
        import os

        user_id = os.getenv("BHASHINI_USER_ID", "").strip()
        api_key = os.getenv("BHASHINI_ULCA_API_KEY", "").strip()
        pipeline_id = os.getenv("BHASHINI_OCR_PIPELINE_ID", "").strip() or None
        model_id = os.getenv("BHASHINI_OCR_MODEL_ID", "").strip() or DEFAULT_HINDI_OCR_MODEL_ID
        timeout = os.getenv("BHASHINI_TIMEOUT_SECONDS", "30").strip()

        if not user_id or not api_key:
            raise OCRConfigurationError(
                "BHASHINI_USER_ID and BHASHINI_ULCA_API_KEY must be configured."
            )

        try:
            timeout_seconds = float(timeout)
        except ValueError as exc:
            raise OCRConfigurationError(
                "BHASHINI_TIMEOUT_SECONDS must be a number."
            ) from exc

        if timeout_seconds <= 0:
            raise OCRConfigurationError(
                "BHASHINI_TIMEOUT_SECONDS must be greater than zero."
            )

        return cls(
            user_id=user_id,
            ulca_api_key=api_key,
            pipeline_id=pipeline_id,
            model_id=model_id,
            timeout_seconds=timeout_seconds,
        )


class BhashiniOCRClient:
    """Client for querying and executing Bhashini OCR pipelines."""

    def __init__(
        self,
        settings: BhashiniOCRSettings,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings
        self._http_client = http_client

    def get_pipeline_config(self, source_language: str = "hi") -> dict[str, Any]:
        """Fetch OCR pipeline configuration for the specified source language."""
        task_config: dict[str, Any] = {
            "taskType": "ocr",
            "config": {
                "language": {
                    "sourceLanguage": source_language,
                }
            },
        }

        payload: dict[str, Any] = {
            "pipelineTasks": [task_config],
        }

        if self.settings.pipeline_id:
            payload["pipelineRequestConfig"] = {
                "pipelineId": self.settings.pipeline_id,
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
                with httpx.Client(timeout=self.settings.timeout_seconds) as client:
                    response = client.post(
                        PIPELINE_CONFIG_URL,
                        headers=headers,
                        json=payload,
                    )

            response.raise_for_status()
            result = response.json()
        except httpx.HTTPStatusError as exc:
            raise BhashiniAPIError(
                f"BHASHINI OCR configuration failed with HTTP {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            raise BhashiniAPIError(
                "BHASHINI OCR pipeline configuration request failed."
            ) from exc
        except ValueError as exc:
            raise BhashiniAPIError("BHASHINI OCR returned invalid JSON.") from exc

        if not isinstance(result, dict):
            raise BhashiniAPIError(
                "BHASHINI OCR returned an unexpected configuration response."
            )

        return result

    def extract_text(
        self,
        endpoint: InferenceEndpoint,
        image_base64: str,
        source_language: str,
        service_id: str,
    ) -> str:
        """Submit base64-encoded image for OCR and return recognized text."""
        if not image_base64.strip():
            raise ValueError("image_base64 must not be empty.")

        payload = {
            "pipelineTasks": [
                {
                    "taskType": "ocr",
                    "config": {
                        "language": {
                            "sourceLanguage": source_language,
                        },
                        "serviceId": service_id,
                    },
                }
            ],
            "inputData": {
                "image": [
                    {
                        "imageContent": image_base64,
                    }
                ],
            },
        }

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
                with httpx.Client(timeout=self.settings.timeout_seconds) as client:
                    response = client.post(
                        endpoint.callback_url,
                        headers=headers,
                        json=payload,
                    )

            response.raise_for_status()
            result = response.json()
        except httpx.HTTPStatusError as exc:
            raise BhashiniAPIError(
                f"BHASHINI OCR compute returned HTTP {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            raise BhashiniAPIError(
                "BHASHINI OCR compute request failed."
            ) from exc
        except ValueError as exc:
            raise BhashiniAPIError("BHASHINI OCR compute returned invalid JSON.") from exc

        return self._parse_ocr_response(result)

    @staticmethod
    def _parse_ocr_response(result: dict[str, Any]) -> str:
        """Parse recognized text from Bhashini pipelineResponse."""
        tasks = result.get("pipelineResponse")
        if not isinstance(tasks, list) or not tasks:
            raise BhashiniAPIError("BHASHINI OCR response missing pipelineResponse.")

        for task in tasks:
            if not isinstance(task, dict) or task.get("taskType") != "ocr":
                continue

            output = task.get("output")
            if isinstance(output, list):
                extracted = []
                for item in output:
                    if isinstance(item, dict):
                        text = item.get("source", "")
                        if isinstance(text, str) and text.strip():
                            extracted.append(text.strip())
                if extracted:
                    return "\n".join(extracted)

        raise BhashiniAPIError("BHASHINI OCR did not return recognized text.")

    @staticmethod
    def parse_ocr_service_id(config: dict[str, Any], source_language: str) -> str:
        """Find the matching OCR serviceId from pipelineResponseConfig."""
        tasks = config.get("pipelineResponseConfig")
        if not isinstance(tasks, list):
            raise BhashiniAPIError(
                "BHASHINI OCR configuration missing pipelineResponseConfig."
            )

        ocr_tasks = [
            task for task in tasks
            if isinstance(task, dict) and task.get("taskType") == "ocr"
        ]
        if not ocr_tasks:
            raise BhashiniAPIError("No OCR task found in BHASHINI pipeline configuration.")

        for task in ocr_tasks:
            entries = task.get("config")
            if not isinstance(entries, list):
                continue

            for entry in entries:
                if not isinstance(entry, dict):
                    continue

                lang = entry.get("language")
                if isinstance(lang, dict) and lang.get("sourceLanguage") == source_language:
                    service_id = entry.get("serviceId")
                    if isinstance(service_id, str) and service_id.strip():
                        return service_id.strip()

        # Fallback to any available serviceId in the OCR task
        for task in ocr_tasks:
            entries = task.get("config")
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, dict):
                        service_id = entry.get("serviceId")
                        if isinstance(service_id, str) and service_id.strip():
                            return service_id.strip()

        raise BhashiniAPIError(
            f"No BHASHINI OCR serviceId available for language '{source_language}'."
        )

    def compute_model_ocr(
        self,
        image_base64: str,
        source_language: str = "hi",
        model_id: str | None = None,
    ) -> str:
        """Submit image to ULCA model compute endpoint for a specific modelId."""
        if not image_base64.strip():
            raise ValueError("image_base64 must not be empty.")

        target_model_id = model_id or self.settings.model_id or DEFAULT_HINDI_OCR_MODEL_ID

        payload = {
            "modelId": target_model_id,
            "task": "ocr",
            "image": [{"imageContent": image_base64}],
            "config": {
                "detectionLevel": "word",
                "modality": "print",
                "languages": [{"sourceLanguage": source_language}],
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
                    MODEL_COMPUTE_URL,
                    headers=headers,
                    json=payload,
                    timeout=self.settings.timeout_seconds,
                )
            else:
                with httpx.Client(timeout=self.settings.timeout_seconds) as client:
                    response = client.post(
                        MODEL_COMPUTE_URL,
                        headers=headers,
                        json=payload,
                    )

            response.raise_for_status()
            result = response.json()
        except httpx.HTTPStatusError as exc:
            raise BhashiniAPIError(
                f"BHASHINI model compute failed with HTTP {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            raise BhashiniAPIError(
                "BHASHINI model compute request failed."
            ) from exc
        except ValueError as exc:
            raise BhashiniAPIError("BHASHINI model compute returned invalid JSON.") from exc

        return self._parse_model_compute_response(result)

    @staticmethod
    def _parse_model_compute_response(result: dict[str, Any]) -> str:
        """Parse recognized text from ULCA model compute output."""
        if not isinstance(result, dict):
            raise BhashiniAPIError("BHASHINI model compute returned an unexpected response.")

        output = result.get("output")
        if isinstance(output, list) and output:
            extracted = []
            for item in output:
                if isinstance(item, dict):
                    text = item.get("source", "")
                    if isinstance(text, str) and text.strip():
                        extracted.append(text.strip())
            if extracted:
                return "\n".join(extracted)

        if "pipelineResponse" in result:
            return BhashiniOCRClient._parse_ocr_response(result)

        raise BhashiniAPIError("BHASHINI model compute did not return recognized text.")

    def extract_document_text(
        self,
        image_bytes: bytes,
        source_language: str = "hi",
    ) -> str:
        """Execute Bhashini OCR: attempts configured pipeline or direct model compute."""
        if not image_bytes:
            raise ValueError("image_bytes must not be empty.")

        image_base64 = base64.b64encode(image_bytes).decode("ascii")

        # 1. If an OCR pipeline ID is explicitly configured, use pipeline inference
        if self.settings.pipeline_id:
            try:
                config = self.get_pipeline_config(source_language=source_language)
                endpoint = parse_inference_endpoint(config)
                service_id = self.parse_ocr_service_id(config, source_language)
                return self.extract_text(
                    endpoint=endpoint,
                    image_base64=image_base64,
                    source_language=source_language,
                    service_id=service_id,
                )
            except BhashiniAPIError:
                # If pipeline inference fails, attempt direct model compute fallback
                pass

        # 2. Compute via modelId (e.g. Bhashini-Bodhan OCR - Hindi)
        return self.compute_model_ocr(
            image_base64=image_base64,
            source_language=source_language,
            model_id=self.settings.model_id,
        )
