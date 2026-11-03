"""Bhashini ULCA Machine Translation (NMT) Client.

Supports:
- ULCA / Dhruva inference translation endpoints.
- Configurable service IDs (e.g. ai4bharat/indictrans-v2-all-gpu).
- Direct inference and pipeline-based execution with timeouts.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from app.speech.config import PIPELINE_CONFIG_URL, BhashiniSettings

logger = logging.getLogger(__name__)

DEFAULT_TRANSLATION_SERVICE_ID = "ai4bharat/indictrans-v2-all-gpu"
DHRUVA_INFERENCE_TRANSLATION_URL = (
    "https://dhruva-api.bhashini.gov.in/services/inference/translation"
)


class BhashiniTranslationError(Exception):
    """Raised when Bhashini translation inference fails or is unconfigured."""


class BhashiniTranslationClient:
    def __init__(
        self,
        service_id: str | None = None,
        timeout_seconds: float = 15.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.service_id = (
            service_id
            or os.getenv("BHASHINI_TRANSLATION_SERVICE_ID")
            or DEFAULT_TRANSLATION_SERVICE_ID
        ).strip()
        self.timeout_seconds = timeout_seconds
        self._http_client = http_client

        # Try loading settings if present
        try:
            self.settings = BhashiniSettings.from_env()
        except Exception:
            self.settings = None

    def translate_texts(
        self,
        texts: list[str],
        target_language: str,
        source_language: str = "en",
        service_id: str | None = None,
    ) -> list[str]:
        """Translate a batch of strings using Bhashini Dhruva NMT."""
        if not texts:
            return []

        active_service_id = service_id or self.service_id
        if not self.settings:
            raise BhashiniTranslationError(
                "Bhashini credentials (BHASHINI_USER_ID, BHASHINI_ULCA_API_KEY) are not set."
            )

        payload = {
            "pipelineTasks": [
                {
                    "taskType": "translation",
                    "config": {
                        "language": {
                            "sourceLanguage": source_language,
                            "targetLanguage": target_language,
                        },
                        "serviceId": active_service_id,
                    },
                }
            ],
            "inputData": {
                "input": [{"source": t} for t in texts],
            },
        }

        headers = {
            "userID": self.settings.user_id,
            "ulcaApiKey": self.settings.ulca_api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Try inference URL
        url = f"{DHRUVA_INFERENCE_TRANSLATION_URL}?serviceId={active_service_id}"

        try:
            if self._http_client is not None:
                resp = self._http_client.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout_seconds,
                )
            else:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    resp = client.post(
                        url,
                        headers=headers,
                        json=payload,
                    )

            if resp.status_code != 200:
                # Also try pipeline URL if direct inference fails with 401/404
                resp = self._call_via_pipeline(payload, headers)

            resp.raise_for_status()
            data = resp.json()

            # Parse translation response from Dhruva format:
            # pipelineResponse[0].output[].target
            pipeline_response = data.get("pipelineResponse", [])
            if pipeline_response:
                task_output = pipeline_response[0].get("output", [])
                results = [item.get("target", "") for item in task_output]
                if len(results) == len(texts):
                    return results

            # Alternatively direct output format:
            output = data.get("output", [])
            if output:
                results = [item.get("target", "") for item in output]
                if len(results) == len(texts):
                    return results

            raise BhashiniTranslationError(f"Unexpected Bhashini translation structure: {data}")

        except Exception as exc:
            logger.warning("Bhashini translation failed for %s -> %s: %s", source_language, target_language, exc)
            raise BhashiniTranslationError(f"Bhashini translation failed: {exc}") from exc

    def _call_via_pipeline(self, payload: dict[str, Any], headers: dict[str, str]) -> httpx.Response:
        """Fallback to standard ULCA pipeline endpoint."""
        with httpx.Client(timeout=self.timeout_seconds) as client:
            return client.post(
                PIPELINE_CONFIG_URL,
                headers=headers,
                json=payload,
            )
