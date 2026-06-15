"""Hugging Face Whisper STT + mBART translation to English."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import httpx

from config.env import load_env

logger = logging.getLogger(__name__)

load_env()

SUPPORTED_LANGUAGE_HINTS = frozenset(
    {"auto", "en", "es", "fr", "hi", "ta", "ml", "spanish", "french", "hindi", "tamil", "malayalam"}
)

WHISPER_LANGUAGE_MAP = {
    "spanish": "es",
    "french": "fr",
    "hindi": "hi",
    "tamil": "ta",
    "malayalam": "ml",
    "mallu": "ml",
    "english": "en",
}

MBART_SRC_LANG = {
    "es": "es_ES",
    "fr": "fr_FR",
    "hi": "hi_IN",
    "ta": "ta_IN",
    "ml": "ml_IN",
    "en": "en_XX",
}

HF_ROUTER = "https://router.huggingface.co/hf-inference/models"


def _hf_token() -> str:
    token = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
    if not token:
        raise ValueError("HF_TOKEN is not set. Add it to your .env file.")
    return token


def _whisper_model() -> str:
    return os.getenv("HF_WHISPER_MODEL", "openai/whisper-large-v3-turbo")


def _translation_model() -> str:
    return os.getenv(
        "HF_TRANSLATION_MODEL",
        "facebook/mbart-large-50-many-to-many-mmt",
    )


def _lang_detect_model() -> str:
    return os.getenv(
        "HF_LANG_DETECT_MODEL",
        "papluca/xlm-roberta-base-language-detection",
    )


def _max_bytes() -> int:
    return int(os.getenv("VOICE_MAX_BYTES", str(25 * 1024 * 1024)))


def normalize_language_hint(hint: str | None) -> str | None:
    if not hint or hint.strip().lower() == "auto":
        return None
    normalized = hint.strip().lower()
    if normalized not in SUPPORTED_LANGUAGE_HINTS:
        return None
    return WHISPER_LANGUAGE_MAP.get(normalized, normalized)


def _hf_json_post(model: str, payload: dict, *, timeout: float = 90.0) -> dict | list:
    url = f"{HF_ROUTER}/{model}"
    headers = {
        "Authorization": f"Bearer {_hf_token()}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, headers=headers, json=payload)
    if response.status_code == 503:
        time.sleep(3)
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict) and data.get("error"):
        raise ValueError(str(data["error"]))
    return data


def _convert_to_wav(audio_bytes: bytes, suffix: str) -> bytes:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return audio_bytes

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / f"input{suffix}"
        dst = Path(tmp) / "output.wav"
        src.write_bytes(audio_bytes)
        proc = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(src),
                "-ar",
                "16000",
                "-ac",
                "1",
                "-f",
                "wav",
                str(dst),
            ],
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0 or not dst.is_file():
            logger.warning("ffmpeg conversion failed; sending original audio bytes")
            return audio_bytes
        return dst.read_bytes()


def prepare_audio(audio_bytes: bytes, filename: str | None, content_type: str | None) -> tuple[bytes, str]:
    name = (filename or "").lower()
    ctype = (content_type or "").split(";")[0].strip().lower()

    if ctype in {"audio/wav", "audio/x-wav", "audio/wave"} or name.endswith(".wav"):
        return audio_bytes, "audio/wav"

    suffix = ".webm"
    if name.endswith(".ogg") or ctype == "audio/ogg":
        suffix = ".ogg"
    elif name.endswith(".mp4") or ctype == "audio/mp4":
        suffix = ".mp4"
    elif name.endswith(".mpeg") or ctype == "audio/mpeg":
        suffix = ".mp3"

    converted = _convert_to_wav(audio_bytes, suffix)
    if converted is not audio_bytes:
        return converted, "audio/wav"
    if ctype:
        return audio_bytes, ctype
    return audio_bytes, "audio/webm"


def _call_whisper_transcribe(audio_bytes: bytes, content_type: str) -> str:
    model = _whisper_model()
    url = f"{HF_ROUTER}/{model}"
    headers = {
        "Authorization": f"Bearer {_hf_token()}",
        "Content-Type": content_type,
    }
    with httpx.Client(timeout=120.0) as client:
        response = client.post(url, headers=headers, content=audio_bytes)
    if response.status_code == 503:
        time.sleep(5)
        with httpx.Client(timeout=120.0) as client:
            response = client.post(url, headers=headers, content=audio_bytes)
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict):
        if payload.get("error"):
            raise ValueError(str(payload["error"]))
        text = (payload.get("text") or "").strip()
        if text:
            return text
    raise ValueError("Whisper returned no transcription.")


def _detect_language(text: str) -> str:
    from integrations.language import detect_language

    return detect_language(text)


def _translate_to_english(text: str, lang_code: str) -> str:
    from integrations.language import translate_to_english

    return translate_to_english(text, lang_code)


def transcribe_and_translate(
    audio_bytes: bytes,
    *,
    filename: str | None = None,
    content_type: str | None = None,
    language_hint: str | None = None,
) -> dict[str, str | bool | None]:
    if len(audio_bytes) > _max_bytes():
        raise ValueError(f"Audio exceeds limit of {_max_bytes()} bytes.")

    prepared, send_type = prepare_audio(audio_bytes, filename, content_type)
    original_text = _call_whisper_transcribe(prepared, send_type)

    if not original_text:
        raise ValueError("No speech detected in the recording.")

    hint = normalize_language_hint(language_hint)
    detected = hint or _detect_language(original_text)
    english_text = _translate_to_english(original_text, detected)

    return {
        "success": True,
        "detected_language": detected,
        "original_text": original_text,
        "english_text": english_text,
    }
