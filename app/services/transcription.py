"""
AudioEnhancerMAX by Fd — Speech-to-Text Transcription Service
Uses faster-whisper for high-quality, local transcription.
"""
import numpy as np
from typing import Optional, List
from pathlib import Path
import tempfile
import logging
import json
import soundfile as sf

logger = logging.getLogger(__name__)

# Lazy-loaded model
_model = None


def _init_model(model_size: str = "medium"):
    """Lazily initialize the Whisper model."""
    global _model
    if _model is None:
        try:
            from faster_whisper import WhisperModel
            # CTranslate2 doesn't support MPS, but ARM NEON on M3 MAX
            # makes CPU inference very fast with int8 quantization
            _model = WhisperModel(
                model_size,
                device="cpu",
                compute_type="int8",
                num_workers=4,  # M3 MAX has plenty of cores
            )
            logger.info(f"faster-whisper model '{model_size}' loaded (ARM NEON optimized)")
        except ImportError:
            try:
                import whisper
                _model = whisper.load_model(model_size.replace("-v3", "").replace("-v2", ""))
                logger.info(f"OpenAI Whisper model loaded (fallback)")
            except ImportError:
                logger.error("No whisper implementation available! Install: pip install faster-whisper")
        except Exception as e:
            logger.error(f"Model initialization failed: {e}")


def transcribe(
    audio: np.ndarray,
    sr: int,
    language: Optional[str] = None,
    model_size: str = "medium",
) -> dict:
    """
    Transcribe audio to text with word-level timestamps.
    Returns: {
        "text": str,
        "language": str,
        "segments": [...],
        "duration": float,
    }
    """
    _init_model(model_size)

    if _model is None:
        logger.error("Transcription model failed to load — returning error")
        return {
            "text": "[Transcription model not available. Please check that faster-whisper is installed.]",
            "language": "",
            "segments": [],
            "duration": len(audio) / sr,
        }

    # Save temp file for model input
    temp_path = Path(tempfile.mktemp(suffix=".wav"))
    # Ensure mono float32 for whisper
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    sf.write(str(temp_path), audio.astype(np.float32), sr)

    try:
        logger.info(f"Starting transcription ({len(audio)/sr:.1f}s, {sr}Hz)...")
        result = _transcribe_faster_whisper(temp_path, language)
        logger.info(f"Transcription complete: {len(result.get('text', ''))} chars, language={result.get('language')}")
    except Exception as e:
        logger.error(f"faster-whisper failed: {e}, trying openai whisper...")
        try:
            result = _transcribe_openai_whisper(temp_path, language)
        except Exception as e2:
            logger.error(f"All transcription methods failed: {e2}")
            result = {"text": f"[Transcription failed: {str(e)}]", "language": "", "segments": []}
    finally:
        temp_path.unlink(missing_ok=True)

    result["duration"] = len(audio) / sr
    return result


def _transcribe_faster_whisper(
    audio_path: Path,
    language: Optional[str] = None,
) -> dict:
    """Transcribe using faster-whisper."""
    from faster_whisper import WhisperModel

    # First attempt: with relaxed VAD filter
    segments_iter, info = _model.transcribe(
        str(audio_path),
        language=language,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters=dict(
            min_silence_duration_ms=500,
            speech_pad_ms=400,
            threshold=0.35,  # Lower = less aggressive
        ),
        beam_size=5,
    )

    text_parts = []
    segments = []

    for segment in segments_iter:
        text_parts.append(segment.text.strip())
        seg_data = {
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip(),
            "confidence": segment.avg_logprob,
        }

        if segment.words:
            seg_data["words"] = [
                {
                    "word": w.word.strip(),
                    "start": w.start,
                    "end": w.end,
                    "probability": w.probability,
                }
                for w in segment.words
            ]

        segments.append(seg_data)

    # If VAD filtered everything out, retry without VAD
    if not text_parts:
        logger.warning("VAD filtered all audio — retrying without VAD filter")
        segments_iter2, info = _model.transcribe(
            str(audio_path),
            language=language,
            word_timestamps=True,
            vad_filter=False,
            beam_size=5,
        )

        for segment in segments_iter2:
            text_parts.append(segment.text.strip())
            seg_data = {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "confidence": segment.avg_logprob,
            }
            if segment.words:
                seg_data["words"] = [
                    {"word": w.word.strip(), "start": w.start, "end": w.end, "probability": w.probability}
                    for w in segment.words
                ]
            segments.append(seg_data)

    return {
        "text": " ".join(text_parts),
        "language": info.language,
        "segments": segments,
    }


def _transcribe_openai_whisper(
    audio_path: Path,
    language: Optional[str] = None,
) -> dict:
    """Fallback transcription using OpenAI Whisper."""
    result = _model.transcribe(
        str(audio_path),
        language=language,
        word_timestamps=True,
    )

    segments = []
    for seg in result.get("segments", []):
        seg_data = {
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"].strip(),
            "confidence": seg.get("avg_logprob", 0),
        }
        if "words" in seg:
            seg_data["words"] = [
                {
                    "word": w["word"].strip(),
                    "start": w["start"],
                    "end": w["end"],
                    "probability": w.get("probability", 0),
                }
                for w in seg["words"]
            ]
        segments.append(seg_data)

    return {
        "text": result.get("text", ""),
        "language": result.get("language", ""),
        "segments": segments,
    }


# ── Export Formats ──────────────────────────────────

def format_as_srt(segments: List[dict]) -> str:
    """Export transcript as SRT subtitle format."""
    lines = []
    for i, seg in enumerate(segments, 1):
        start = _format_timestamp_srt(seg["start"])
        end = _format_timestamp_srt(seg["end"])
        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        lines.append(seg["text"])
        lines.append("")
    return "\n".join(lines)


def format_as_vtt(segments: List[dict]) -> str:
    """Export transcript as WebVTT format."""
    lines = ["WEBVTT", ""]
    for seg in segments:
        start = _format_timestamp_vtt(seg["start"])
        end = _format_timestamp_vtt(seg["end"])
        lines.append(f"{start} --> {end}")
        lines.append(seg["text"])
        lines.append("")
    return "\n".join(lines)


def format_as_json(segments: List[dict], full_text: str, language: str) -> str:
    """Export transcript as detailed JSON."""
    return json.dumps({
        "text": full_text,
        "language": language,
        "segments": segments,
    }, ensure_ascii=False, indent=2)


def _format_timestamp_srt(seconds: float) -> str:
    """Format seconds as SRT timestamp: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def _format_timestamp_vtt(seconds: float) -> str:
    """Format seconds as VTT timestamp: HH:MM:SS.mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"
