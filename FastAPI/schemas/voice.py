"""Schemas for multilingual voice transcription."""

from __future__ import annotations

from pydantic import BaseModel, Field


class VoiceTranscribeResponse(BaseModel):
    success: bool = True
    detected_language: str | None = Field(
        default=None,
        description="Best-effort language code (es, fr, hi, ta, ml, en, ...).",
    )
    original_text: str = Field(..., description="Transcription in the source language.")
    english_text: str = Field(..., description="English text for the copilot / LangGraph.")
    message: str | None = None
