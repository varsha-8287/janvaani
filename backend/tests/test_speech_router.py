
import base64

from fastapi.testclient import TestClient

from app.main import app
from app.speech import router as speech_router

client = TestClient(app)


def test_tts_returns_wav_audio(monkeypatch):
    fake_audio = (
        b"RIFF"
        + (36).to_bytes(4, "little")
        + b"WAVE"
        + b"fmt "
        + (16).to_bytes(4, "little")
        + (1).to_bytes(2, "little")
        + (1).to_bytes(2, "little")
        + (48000).to_bytes(4, "little")
        + (96000).to_bytes(4, "little")
        + (2).to_bytes(2, "little")
        + (16).to_bytes(2, "little")
        + b"data"
        + (0).to_bytes(4, "little")
    )

    fake_config = {
        "pipelineInferenceAPIEndPoint": {
            "callbackUrl": "https://example.invalid/inference",
            "inferenceApiKey": {"name": "x-api-key", "value": "fake"},
            "isSyncApi": True,
        },
        "pipelineResponseConfig": [
            {
                "taskType": "tts",
                "config": [
                    {
                        "serviceId": "fake-tts",
                        "language": {"sourceLanguage": "hi"},
                        "supportedVoices": ["male"],
                    }
                ],
            }
        ],
    }

    class FakeClient:
        def get_pipeline_config(self, task_type):
            assert task_type == "tts"
            return fake_config

        def synthesize_speech(self, **kwargs):
            return {
                "pipelineResponse": [
                    {
                        "taskType": "tts",
                        "audio": [
                            {
                                "audioContent": base64.b64encode(
                                    fake_audio
                                ).decode("ascii")
                            }
                        ],
                    }
                ]
            }

    monkeypatch.setattr(speech_router, "_client", lambda: FakeClient())

    response = client.post(
        "/speech/tts",
        json={
            "text": "नमस्ते",
            "language": "hi",
            "gender": "male",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content == fake_audio


def test_tts_voice_fallback(monkeypatch):
    """Test that TTS falls back to available voice if requested voice is not offered for that language."""
    fake_config = {
        "pipelineInferenceAPIEndPoint": {
            "callbackUrl": "https://example.invalid/inference",
            "inferenceApiKey": {"name": "x-api-key", "value": "fake"},
            "isSyncApi": True,
        },
        "pipelineResponseConfig": [
            {
                "taskType": "tts",
                "config": [
                    {
                        "serviceId": "fake-tts-en",
                        "language": {"sourceLanguage": "en"},
                        "supportedVoices": ["male"],  # English only offers male
                    }
                ],
            }
        ],
    }

    # Verify _language_service finds entry even when female is requested
    entry = speech_router._language_service(fake_config, "tts", "en", gender="female")
    assert entry["serviceId"] == "fake-tts-en"
    assert "male" in entry["supportedVoices"]


def test_asr_english_candidate_fallback(monkeypatch):
    """Test that ASR falls back to Indian multilingual Hindi model when English ASR pipeline is not provisioned."""
    fake_config = {
        "pipelineInferenceAPIEndPoint": {
            "callbackUrl": "https://example.invalid/inference",
            "inferenceApiKey": {"name": "x-api-key", "value": "fake"},
            "isSyncApi": True,
        },
        "pipelineResponseConfig": [
            {
                "taskType": "asr",
                "config": [
                    {
                        "serviceId": "fake-asr-hi",
                        "language": {"sourceLanguage": "hi"},
                    }
                ],
            }
        ],
    }

    # Verify _language_service selects Hindi model for English query
    entry = speech_router._language_service(fake_config, "asr", "en")
    assert entry["serviceId"] == "fake-asr-hi"

