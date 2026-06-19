"""Multilingual voice transcription for copilot chat (HF Whisper)."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from dependencies.auth import TokenUser, get_current_user
from schemas.voice import VoiceTranscribeResponse
from security import rate_limit
from services import voice as voice_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])

ALLOWED_CONTENT_TYPES = {
    "audio/webm",
    "audio/ogg",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mpeg",
    "audio/mp4",
    "audio/mp3",
}


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy", "provider": "huggingface-whisper"}


@router.post(
    "/transcribe",
    response_model=VoiceTranscribeResponse,
    dependencies=[Depends(rate_limit(10, 60))],
)
async def transcribe(
    current_user: Annotated[TokenUser, Depends(get_current_user)],
    audio: UploadFile = File(..., description="Recorded microphone audio"),
    language_hint: str = Form(default="auto"),
) -> VoiceTranscribeResponse:
    _ = current_user

    if not audio.filename and not audio.content_type:
        raise HTTPException(status_code=400, detail="Audio file is required.")

    content_type = (audio.content_type or "").split(";")[0].strip().lower()
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio type: {content_type}. Use webm, wav, ogg, or mp4.",
        )

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio recording.")

    try:
        result = voice_service.transcribe_and_translate(
            audio_bytes,
            filename=audio.filename,
            content_type=audio.content_type,
            language_hint=language_hint,
        )
        return VoiceTranscribeResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Voice transcription failed")
        raise HTTPException(
            status_code=502,
            detail=f"Voice transcription failed: {exc}",
        ) from exc
