
import base64
import binascii
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.speech.bhashini_client import BhashiniClient
from app.speech.config import BhashiniSettings, SpeechConfigurationError
from app.speech.errors import BhashiniAPIError
from app.speech.inference_config import parse_inference_endpoint

router = APIRouter(prefix="/speech", tags=["speech"])

MAX_AUDIO_BYTES = 10 * 1024 * 1024
MAX_TEXT_LENGTH = 5000
SUPPORTED_AUDIO_TYPES = {"audio/wav", "audio/x-wav"}


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    language: str = Field(min_length=2, max_length=10)
    gender: str = "male"
    speed: float = Field(default=1.0, ge=0.1, le=1.99)


def _client() -> BhashiniClient:
    try:
        return BhashiniClient(BhashiniSettings.from_env())
    except SpeechConfigurationError as exc:
        raise HTTPException(
            status_code=503,
            detail="Speech service is not configured.",
        ) from exc


def _language_service(
    config: dict[str, Any],
    task_type: str,
    language: str,
    gender: str | None = None,
) -> dict[str, Any]:
    tasks = config.get("pipelineResponseConfig")
    if not isinstance(tasks, list):
        raise HTTPException(
            status_code=502,
            detail="Speech provider returned invalid configuration.",
        )

    task = next(
        (
            item for item in tasks
            if isinstance(item, dict) and item.get("taskType") == task_type
        ),
        None,
    )
    entries = task.get("config") if isinstance(task, dict) else None

    if not isinstance(entries, list):
        raise HTTPException(
            status_code=502,
            detail="Speech provider returned invalid task configuration.",
        )

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        lang = entry.get("language")
        if not isinstance(lang, dict):
            continue
        if lang.get("sourceLanguage") != language:
            continue

        if gender is not None:
            voices = entry.get("supportedVoices", [])
            if not isinstance(voices, list) or gender not in voices:
                continue

        service_id = entry.get("serviceId")
        if isinstance(service_id, str) and service_id.strip():
            return entry

    raise HTTPException(
        status_code=422,
        detail=f"{task_type.upper()} is not available for the requested language or voice.",
    )


def _provider_error(exc: BhashiniAPIError) -> HTTPException:
    # Do not return provider exception details or credentials to clients.
    return HTTPException(
        status_code=502,
        detail="Speech provider request failed.",
    )


def _extract_transcription(result: dict[str, Any]) -> str:
    tasks = result.get("pipelineResponse")
    if not isinstance(tasks, list):
        raise HTTPException(
            status_code=502,
            detail="Speech provider returned an invalid transcription response.",
        )

    for task in tasks:
        if not isinstance(task, dict) or task.get("taskType") != "asr":
            continue

        output = task.get("output")
        if not isinstance(output, list):
            continue

        for item in output:
            if isinstance(item, dict):
                text = item.get("source")
                if isinstance(text, str) and text.strip():
                    return text.strip()

    raise HTTPException(
        status_code=502,
        detail="Speech provider did not return recognized text.",
    )


@router.post("/asr")
async def speech_to_text(
    request: Request,
    language: str = Query(min_length=2, max_length=10),
):
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type not in SUPPORTED_AUDIO_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Send a WAV file with Content-Type audio/wav.",
        )

    audio = await request.body()
    if not audio:
        raise HTTPException(status_code=400, detail="Audio body is empty.")
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio exceeds the 10 MB limit.")
    if not audio.startswith(b"RIFF") or audio[8:12] != b"WAVE":
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a valid WAV container.",
        )

    client = _client()

    try:
        config = client.get_pipeline_config("asr")
        selected = _language_service(config, "asr", language)
        endpoint = parse_inference_endpoint(config)

        result = client.transcribe_audio(
            endpoint=endpoint,
            audio_base64=base64.b64encode(audio).decode("ascii"),
            source_language=language,
            service_id=selected["serviceId"],
            sampling_rate=16000,
        )
        text = _extract_transcription(result)
        return {"text": text, "language": language}

    except BhashiniAPIError as exc:
        raise _provider_error(exc) from exc


@router.post("/tts")
def text_to_speech(body: TTSRequest):
    if not body.text.strip():
        raise HTTPException(status_code=422, detail="Text must not be blank.")
    if body.gender not in {"male", "female"}:
        raise HTTPException(
            status_code=422,
            detail="Gender must be 'male' or 'female'.",
        )

    client = _client()

    try:
        config = client.get_pipeline_config("tts")
        selected = _language_service(
            config,
            "tts",
            body.language,
            gender=body.gender,
        )
        endpoint = parse_inference_endpoint(config)

        result = client.synthesize_speech(
            endpoint=endpoint,
            text=body.text,
            source_language=body.language,
            service_id=selected["serviceId"],
            gender=body.gender,
            speed=body.speed,
            sampling_rate=48000,
        )

    except BhashiniAPIError as exc:
        raise _provider_error(exc) from exc

    tasks = result.get("pipelineResponse")
    task = next(
        (
            item for item in tasks
            if isinstance(item, dict) and item.get("taskType") == "tts"
        ),
        None,
    ) if isinstance(tasks, list) else None

    audio_items = task.get("audio") if isinstance(task, dict) else None
    audio_item = audio_items[0] if isinstance(audio_items, list) and audio_items else None
    encoded = audio_item.get("audioContent") if isinstance(audio_item, dict) else None

    if not isinstance(encoded, str) or not encoded:
        raise HTTPException(
            status_code=502,
            detail="Speech provider did not return audio.",
        )

    try:
        audio_bytes = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(
            status_code=502,
            detail="Speech provider returned invalid audio.",
        ) from exc

    if not audio_bytes.startswith(b"RIFF") or audio_bytes[8:12] != b"WAVE":
        raise HTTPException(
            status_code=502,
            detail="Speech provider returned an unexpected audio format.",
        )

    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers={"Content-Disposition": 'inline; filename="speech.wav"'},
    )
