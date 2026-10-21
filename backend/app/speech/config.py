import os
from dataclasses import dataclass


PIPELINE_CONFIG_URL = (
    "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"
)

IIT_MADRAS_PIPELINE_ID = "660fa5bec7fb5b0328229016"


class SpeechConfigurationError(RuntimeError):
    """Raised when speech integration settings are missing or invalid."""


@dataclass(frozen=True)
class BhashiniSettings:
    user_id: str
    ulca_api_key: str
    timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "BhashiniSettings":
        user_id = os.getenv("BHASHINI_USER_ID", "").strip()
        api_key = os.getenv("BHASHINI_ULCA_API_KEY", "").strip()
        timeout = os.getenv("BHASHINI_TIMEOUT_SECONDS", "30").strip()

        if not user_id or not api_key:
            raise SpeechConfigurationError(
                "BHASHINI_USER_ID and BHASHINI_ULCA_API_KEY must be configured."
            )

        try:
            timeout_seconds = float(timeout)
        except ValueError as exc:
            raise SpeechConfigurationError(
                "BHASHINI_TIMEOUT_SECONDS must be a number."
            ) from exc

        if timeout_seconds <= 0:
            raise SpeechConfigurationError(
                "BHASHINI_TIMEOUT_SECONDS must be greater than zero."
            )

        return cls(
            user_id=user_id,
            ulca_api_key=api_key,
            timeout_seconds=timeout_seconds,
        )
