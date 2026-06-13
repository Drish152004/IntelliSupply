"""
Text language detection and translation to English for the orchestrator.

Shared by the orchestrator init node and the voice API.
"""

from __future__ import annotations

import logging
import os

import httpx

from config.env import load_env

logger = logging.getLogger(__name__)

load_env()

SUPPORTED_LANGUAGES: frozenset[str] = frozenset({"en", "es", "fr", "hi", "ta", "ml"})

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


def _hf_token() -> str | None:
    return os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")


def _lang_detect_model() -> str:
    return os.getenv(
        "HF_LANG_DETECT_MODEL",
        "papluca/xlm-roberta-base-language-detection",
    )


def _translation_model() -> str:
    return os.getenv(
        "HF_TRANSLATION_MODEL",
        "facebook/mbart-large-50-many-to-many-mmt",
    )


def _hf_json_post(model: str, payload: dict, *, timeout: float = 60.0) -> dict | list:
    token = _hf_token()
    if not token:
        raise ValueError("HF_TOKEN is not set")
    url = f"{HF_ROUTER}/{model}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict) and data.get("error"):
        raise ValueError(str(data["error"]))
    return data


def detect_language(text: str) -> str:
    """Detect language code from text; defaults to en on failure."""
    if not text.strip():
        return "en"

    token = _hf_token()
    if not token:
        return "en"

    try:
        payload = _hf_json_post(_lang_detect_model(), {"inputs": text})
        if not isinstance(payload, list) or not payload:
            return "en"
        top = payload[0]
        if isinstance(top, list) and top:
            top = top[0]
        if isinstance(top, dict):
            label = str(top.get("label", "en")).lower()
            code = label.split("_")[0]
            return code if code in SUPPORTED_LANGUAGES else "en"
    except Exception:
        logger.debug("Language detection failed; assuming English", exc_info=True)
    return "en"


def translate_to_english(text: str, lang_code: str) -> str:
    """Translate text to English when lang_code is not en."""
    if not text.strip() or lang_code == "en":
        return text

    token = _hf_token()
    if not token:
        return text

    src_lang = MBART_SRC_LANG.get(lang_code, "en_XX")
    try:
        payload = _hf_json_post(
            _translation_model(),
            {
                "inputs": text,
                "parameters": {"src_lang": src_lang, "tgt_lang": "en_XX"},
            },
        )
        if isinstance(payload, list) and payload:
            first = payload[0]
            if isinstance(first, dict) and first.get("translation_text"):
                return str(first["translation_text"]).strip()
        if isinstance(payload, dict) and payload.get("translation_text"):
            return str(payload["translation_text"]).strip()
    except Exception:
        logger.debug("Translation failed; using original text", exc_info=True)
    return text


def normalize_query(text: str, *, language_hint: str | None = None) -> dict[str, str]:
    """
    Detect language and return English-normalized query plus metadata.

    Returns keys: original_query, user_query (English), detected_language.
    """
    hint = (language_hint or "").strip().lower()
    if hint in WHISPER_LANGUAGE_MAP:
        hint = WHISPER_LANGUAGE_MAP[hint]

    detected = hint if hint and hint in SUPPORTED_LANGUAGES else detect_language(text)
    english = translate_to_english(text, detected)

    return {
        "original_query": text,
        "user_query": english,
        "detected_language": detected,
    }
