import json
import os
import wave
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from fastapi import HTTPException

from app.core.config import settings


@dataclass(frozen=True)
class TranscriptSegment:
    sequence_number: int
    text: str
    start_ms: int
    end_ms: int
    speaker_label: str | None
    quality_score: float | None


@lru_cache(maxsize=2)
def _load_vosk_model(model_path: str) -> Any:
    from vosk import Model

    return Model(model_path)


class VoskASRProvider:
    provider_name = "vosk-local"

    def __init__(self, model_path: str | None = None) -> None:
        self.model_path = model_path or settings.vosk_model_path

    def transcribe(self, audio_bytes: bytes) -> tuple[list[TranscriptSegment], int, str]:
        if not self.model_path or not os.path.isdir(self.model_path):
            raise HTTPException(
                503,
                "Local ASR is unavailable. Configure VOSK_MODEL_PATH with an installed, licensed model.",
            )
        try:
            with wave.open(__import__("io").BytesIO(audio_bytes), "rb") as wav:
                if wav.getcomptype() != "NONE" or wav.getsampwidth() != 2 or wav.getnchannels() != 1:
                    raise HTTPException(415, "Audio must be uncompressed, 16-bit, mono WAV for MVP ASR.")
                sample_rate = wav.getframerate()
                if not 8000 <= sample_rate <= 48000:
                    raise HTTPException(415, "WAV sample rate must be between 8 kHz and 48 kHz.")
                frame_count = wav.getnframes()
                duration_ms = round(frame_count * 1000 / sample_rate)
                audio = wav.readframes(frame_count)
        except HTTPException:
            raise
        except (wave.Error, EOFError) as exc:
            raise HTTPException(415, "The uploaded audio is not a readable WAV file.") from exc
        from vosk import KaldiRecognizer

        recognizer = KaldiRecognizer(_load_vosk_model(self.model_path), sample_rate)
        recognizer.SetWords(True)
        results: list[dict[str, Any]] = []
        frame_bytes = 4000
        for start in range(0, len(audio), frame_bytes):
            if recognizer.AcceptWaveform(audio[start : start + frame_bytes]):
                results.append(json.loads(recognizer.Result()))
        results.append(json.loads(recognizer.FinalResult()))

        tokens: list[dict[str, Any]] = []
        for result in results:
            tokens.extend(result.get("result") or [])
        segments: list[TranscriptSegment] = []
        pending: list[dict[str, Any]] = []
        for token in tokens:
            pending.append(token)
            word = str(token.get("word", ""))
            if len(pending) >= 24 or word.endswith(('.', '?', '!')):
                segments.append(self._segment(pending, len(segments)))
                pending = []
        if pending:
            segments.append(self._segment(pending, len(segments)))

        if not segments:
            text = " ".join(str(result.get("text", "")).strip() for result in results).strip()
            if text:
                segments.append(TranscriptSegment(0, text, 0, duration_ms, None, None))
        if not segments:
            raise HTTPException(422, "ASR produced no transcript text for this recording.")
        return segments, duration_ms, "vosk"

    @staticmethod
    def _segment(words: list[dict[str, Any]], sequence: int) -> TranscriptSegment:
        text = " ".join(str(item.get("word", "")).strip() for item in words).strip()
        confidences = [float(item["conf"]) for item in words if item.get("conf") is not None]
        return TranscriptSegment(
            sequence_number=sequence,
            text=text,
            start_ms=max(0, round(float(words[0].get("start", 0)) * 1000)),
            end_ms=max(0, round(float(words[-1].get("end", words[0].get("start", 0))) * 1000)),
            speaker_label=None,
            quality_score=(sum(confidences) / len(confidences)) if confidences else None,
        )
