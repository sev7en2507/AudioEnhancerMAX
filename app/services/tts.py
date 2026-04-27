"""
AudioEnhancerMAX by Fd — Text-to-Speech Service
Uses Coqui XTTS-v2 for high-quality, multilingual TTS with voice cloning.
"""
import os
import numpy as np
from typing import Optional, List
from pathlib import Path
import tempfile
import logging
import soundfile as sf

# Auto-accept Coqui TTS license (non-commercial use)
os.environ["COQUI_TOS_AGREED"] = "1"

logger = logging.getLogger(__name__)

# Lazy-loaded model
_tts_model = None
_tts_init_attempts = 0
_TTS_MAX_RETRIES = 3

# Available preset voices
PRESET_VOICES = [
    {"id": "default", "name": "Default Male", "language": "en", "gender": "male",
     "description": "Clear, professional male voice"},
    {"id": "female_1", "name": "Sofia", "language": "en", "gender": "female",
     "description": "Warm, expressive female voice"},
    {"id": "male_2", "name": "Marcus", "language": "en", "gender": "male",
     "description": "Deep, authoritative male voice"},
    {"id": "female_2", "name": "Elena", "language": "it", "gender": "female",
     "description": "Natural Italian female voice"},
    {"id": "male_3", "name": "Alessandro", "language": "it", "gender": "male",
     "description": "Professional Italian male voice"},
]


def _init_tts():
    """Lazily initialize TTS model with retry logic."""
    global _tts_model, _tts_init_attempts
    if _tts_model is not None:
        return  # Already loaded

    if _tts_init_attempts >= _TTS_MAX_RETRIES:
        return  # Give up after max retries

    _tts_init_attempts += 1
    logger.info(f"🗣️ TTS init attempt {_tts_init_attempts}/{_TTS_MAX_RETRIES}...")

    try:
        from TTS.api import TTS
    except ImportError:
        logger.error("❌ Coqui TTS package not installed! Run: pip install TTS")
        return

    # Try XTTS-v2 first (multilingual, high quality)
    try:
        _tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
        logger.info("✅ XTTS-v2 model loaded successfully")
        return
    except Exception as e:
        logger.warning(f"⚠️ XTTS-v2 failed (likely transformers incompatibility): {e}")

    # Fallback: tacotron2-DDC (English only, but works with any transformers version)
    try:
        _tts_model = TTS("tts_models/en/ljspeech/tacotron2-DDC")
        logger.info("✅ Fallback TTS model loaded (tacotron2-DDC, English only)")
    except Exception as e2:
        logger.error(f"❌ All TTS models failed: {e2}")


def get_available_voices() -> List[dict]:
    """Get list of available voices."""
    return PRESET_VOICES


def synthesize_speech(
    text: str,
    language: str = "en",
    voice_id: str = "default",
    speed: float = 1.0,
    pitch: float = 1.0,
    warmth: float = 0.5,
    style: str = "neutral",
    clone_voice_path: Optional[str] = None,
) -> tuple:
    """
    Generate speech from text.

    Returns (audio_array, sample_rate)
    """
    _init_tts()

    if _tts_model is None:
        raise RuntimeError(
            f"TTS model not available after {_tts_init_attempts} attempts. "
            f"Check that Coqui TTS is installed: pip install TTS"
        )

    try:
        # Output temp file
        temp_path = tempfile.mktemp(suffix=".wav")

        # Check if model is multilingual (XTTS) or single-language (tacotron2)
        is_multilingual = hasattr(_tts_model, 'is_multi_lingual') and _tts_model.is_multi_lingual

        if clone_voice_path and is_multilingual:
            # Voice cloning mode (XTTS only)
            _tts_model.tts_to_file(
                text=text,
                file_path=temp_path,
                speaker_wav=clone_voice_path,
                language=language,
                speed=speed,
            )
        elif is_multilingual:
            # Multilingual model with language parameter
            speaker = _get_speaker_for_voice(voice_id)
            tts_kwargs = {
                "text": text,
                "file_path": temp_path,
                "language": language,
                "speed": speed,
            }
            if speaker:
                tts_kwargs["speaker"] = speaker
            _tts_model.tts_to_file(**tts_kwargs)
        else:
            # Single-language model (tacotron2) — no language/speaker params
            _tts_model.tts_to_file(
                text=text,
                file_path=temp_path,
            )

        # Load the generated audio
        audio, sr = sf.read(temp_path)
        Path(temp_path).unlink(missing_ok=True)

        # Apply post-processing for pitch and warmth
        audio = _apply_voice_adjustments(audio, sr, pitch, warmth, style)

        return audio, sr

    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}")
        return np.zeros(1), 22050


def _get_speaker_for_voice(voice_id: str) -> Optional[str]:
    """Map voice ID to TTS model speaker."""
    # XTTS-v2 uses reference audio for speaker, not speaker IDs
    # For preset voices, we'd have reference audio files
    # For now, return None to use default
    return None


def _apply_voice_adjustments(
    audio: np.ndarray,
    sr: int,
    pitch: float = 1.0,
    warmth: float = 0.5,
    style: str = "neutral",
) -> np.ndarray:
    """Apply pitch shifting, warmth, and style adjustments."""
    import librosa

    # Pitch adjustment
    if abs(pitch - 1.0) > 0.05:
        n_steps = (pitch - 1.0) * 12  # Convert ratio to semitones
        audio = librosa.effects.pitch_shift(
            y=audio, sr=sr, n_steps=n_steps
        )

    # Warmth: low-shelf boost / high-shelf cut
    try:
        import pedalboard as pb

        effects = []

        if warmth > 0.5:
            # Warmer: boost lows, cut highs
            boost = (warmth - 0.5) * 6  # 0-3dB boost
            effects.append(pb.LowShelfFilter(cutoff_frequency_hz=200, gain_db=boost))
            effects.append(pb.HighShelfFilter(cutoff_frequency_hz=6000, gain_db=-boost * 0.5))
        elif warmth < 0.5:
            # Cooler/brighter: cut lows, boost highs
            cut = (0.5 - warmth) * 6
            effects.append(pb.LowShelfFilter(cutoff_frequency_hz=200, gain_db=-cut))
            effects.append(pb.HighShelfFilter(cutoff_frequency_hz=6000, gain_db=cut * 0.5))

        # Style adjustments
        if style == "energetic":
            effects.extend([
                pb.Compressor(threshold_db=-15, ratio=2.5, attack_ms=5, release_ms=50),
                pb.Gain(gain_db=2.0),
            ])
        elif style == "calm":
            effects.extend([
                pb.Compressor(threshold_db=-25, ratio=1.5, attack_ms=20, release_ms=200),
                pb.LowpassFilter(cutoff_frequency_hz=12000),
            ])
        elif style == "expressive":
            effects.extend([
                pb.Compressor(threshold_db=-18, ratio=2.0, attack_ms=10, release_ms=100),
                pb.PeakFilter(cutoff_frequency_hz=2500, gain_db=2.0, q=0.7),
            ])

        if effects:
            board = pb.Pedalboard(effects)
            audio_2d = audio.reshape(1, -1) if audio.ndim == 1 else audio
            audio = board(audio_2d, sr)
            audio = audio.flatten() if audio.ndim != 1 else audio

    except ImportError:
        pass

    # Final safety clip
    audio = np.clip(audio, -1.0, 1.0)

    return audio
