"""
AudioEnhancerMAX by Fd — Text-to-Speech Service
Uses Microsoft Edge Neural TTS for expressive, natural-sounding speech.
Supports 400+ voices in 100+ languages with zero API keys.
Fallback: Coqui tacotron2 for fully offline operation.
"""
import asyncio
import os
import numpy as np
from typing import Optional, List
from pathlib import Path
import tempfile
import logging
import soundfile as sf

logger = logging.getLogger(__name__)

# ── Voice Registry ──
# Map friendly IDs to edge-tts voice names
VOICE_MAP = {
    # Italian
    "it_giuseppe":  "it-IT-GiuseppeMultilingualNeural",
    "it_diego":     "it-IT-DiegoNeural",
    "it_isabella":  "it-IT-IsabellaNeural",
    "it_elsa":      "it-IT-ElsaNeural",
    # English
    "en_aria":      "en-US-AriaNeural",
    "en_guy":       "en-US-GuyNeural",
    "en_jenny":     "en-US-JennyNeural",
    "en_davis":     "en-US-DavisNeural",
    "en_sonia":     "en-GB-SoniaNeural",
    # Spanish
    "es_elena":     "es-AR-ElenaNeural",
    "es_tomas":     "es-AR-TomasNeural",
    # French
    "fr_denise":    "fr-FR-DeniseNeural",
    "fr_henri":     "fr-FR-HenriNeural",
    # German
    "de_katja":     "de-DE-KatjaNeural",
    "de_conrad":    "de-DE-ConradNeural",
}

# Language → default voice fallback
LANG_DEFAULTS = {
    "it": "it-IT-GiuseppeMultilingualNeural",
    "en": "en-US-AriaNeural",
    "es": "es-AR-ElenaNeural",
    "fr": "fr-FR-DeniseNeural",
    "de": "de-DE-KatjaNeural",
    "pt": "pt-BR-FranciscaNeural",
    "ja": "ja-JP-NanamiNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "ko": "ko-KR-SunHiNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "ar": "ar-SA-ZariyahNeural",
    "hi": "hi-IN-SwaraNeural",
}

PRESET_VOICES = [
    {"id": "it_giuseppe", "name": "Giuseppe 🇮🇹", "language": "it", "gender": "male",
     "description": "Natural Italian multilingual voice — warm and expressive"},
    {"id": "it_isabella", "name": "Isabella 🇮🇹", "language": "it", "gender": "female",
     "description": "Clear Italian female voice — professional tone"},
    {"id": "it_diego", "name": "Diego 🇮🇹", "language": "it", "gender": "male",
     "description": "Deep Italian male voice — authoritative"},
    {"id": "en_aria", "name": "Aria 🇺🇸", "language": "en", "gender": "female",
     "description": "Expressive American female — versatile and natural"},
    {"id": "en_guy", "name": "Guy 🇺🇸", "language": "en", "gender": "male",
     "description": "Clear American male — podcast-quality narration"},
    {"id": "en_davis", "name": "Davis 🇺🇸", "language": "en", "gender": "male",
     "description": "Deep American male — warm and conversational"},
    {"id": "en_sonia", "name": "Sonia 🇬🇧", "language": "en", "gender": "female",
     "description": "British female — elegant and articulate"},
    {"id": "es_elena", "name": "Elena 🇪🇸", "language": "es", "gender": "female",
     "description": "Natural Spanish female voice"},
    {"id": "fr_denise", "name": "Denise 🇫🇷", "language": "fr", "gender": "female",
     "description": "Warm French female voice"},
    {"id": "de_katja", "name": "Katja 🇩🇪", "language": "de", "gender": "female",
     "description": "Professional German female voice"},
]


def get_available_voices() -> List[dict]:
    """Get list of available voices."""
    return PRESET_VOICES


def _resolve_voice(voice_id: str, language: str) -> str:
    """Resolve voice ID to edge-tts voice name."""
    # Direct match in voice map
    if voice_id in VOICE_MAP:
        return VOICE_MAP[voice_id]

    # Language fallback
    lang_code = language[:2].lower() if language else "en"
    return LANG_DEFAULTS.get(lang_code, "en-US-AriaNeural")


def _style_to_rate_pitch(style: str, speed: float, pitch: float):
    """Convert style + speed + pitch to edge-tts rate/pitch strings."""
    # Speed: 1.0 = normal, 0.5 = slow, 2.0 = fast
    rate_pct = int((speed - 1.0) * 100)

    # Pitch: 1.0 = normal, range ~0.5 to 1.5
    pitch_hz = int((pitch - 1.0) * 50)

    # Style adjustments
    if style == "energetic":
        rate_pct += 10
        pitch_hz += 5
    elif style == "calm":
        rate_pct -= 10
        pitch_hz -= 3
    elif style == "expressive":
        rate_pct += 5
        pitch_hz += 8

    rate_str = f"+{rate_pct}%" if rate_pct >= 0 else f"{rate_pct}%"
    pitch_str = f"+{pitch_hz}Hz" if pitch_hz >= 0 else f"{pitch_hz}Hz"

    return rate_str, pitch_str


async def _synthesize_edge(text: str, voice: str, rate: str, pitch: str, output_path: str):
    """Generate speech using edge-tts (async)."""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)


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
    Generate speech from text using Microsoft Edge Neural TTS.
    Returns (audio_array, sample_rate).
    """
    voice = _resolve_voice(voice_id, language)
    rate_str, pitch_str = _style_to_rate_pitch(style, speed, pitch)

    temp_path = tempfile.mktemp(suffix=".mp3")

    try:
        # edge-tts is async — run in a new event loop (we're called from a thread)
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_synthesize_edge(text, voice, rate_str, pitch_str, temp_path))
        finally:
            loop.close()

        # Load the generated audio
        audio, sr = sf.read(temp_path)
        Path(temp_path).unlink(missing_ok=True)

        logger.info(f"✅ Edge TTS: {voice} — {len(audio)/sr:.1f}s generated")

        # Apply warmth post-processing
        audio = _apply_warmth(audio, sr, warmth, style)

        return audio, sr

    except Exception as e:
        logger.error(f"⚠️ Edge TTS failed: {e}")
        Path(temp_path).unlink(missing_ok=True)

        # Fallback to Coqui tacotron2 (offline)
        logger.info("Trying offline fallback (Coqui tacotron2)...")
        return _synthesize_coqui_fallback(text)


def _synthesize_coqui_fallback(text: str) -> tuple:
    """Offline fallback using Coqui tacotron2-DDC."""
    try:
        os.environ["COQUI_TOS_AGREED"] = "1"
        from TTS.api import TTS
        model = TTS("tts_models/en/ljspeech/tacotron2-DDC")
        temp_path = tempfile.mktemp(suffix=".wav")
        model.tts_to_file(text=text, file_path=temp_path)
        audio, sr = sf.read(temp_path)
        Path(temp_path).unlink(missing_ok=True)
        logger.info(f"✅ Coqui fallback: {len(audio)/sr:.1f}s generated (English only)")
        return audio, sr
    except Exception as e:
        logger.error(f"❌ All TTS engines failed: {e}")
        raise RuntimeError(f"No TTS engine available: {e}")


def _apply_warmth(audio: np.ndarray, sr: int, warmth: float = 0.5, style: str = "neutral") -> np.ndarray:
    """Apply warmth and style EQ adjustments via pedalboard."""
    try:
        import pedalboard as pb

        effects = []

        if warmth > 0.5:
            boost = (warmth - 0.5) * 6
            effects.append(pb.LowShelfFilter(cutoff_frequency_hz=200, gain_db=boost))
            effects.append(pb.HighShelfFilter(cutoff_frequency_hz=6000, gain_db=-boost * 0.5))
        elif warmth < 0.5:
            cut = (0.5 - warmth) * 6
            effects.append(pb.LowShelfFilter(cutoff_frequency_hz=200, gain_db=-cut))
            effects.append(pb.HighShelfFilter(cutoff_frequency_hz=6000, gain_db=cut * 0.5))

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

        if effects:
            board = pb.Pedalboard(effects)
            audio_2d = audio.reshape(1, -1) if audio.ndim == 1 else audio
            audio = board(audio_2d, sr)
            audio = audio.flatten() if audio.ndim != 1 else audio

    except ImportError:
        pass

    return np.clip(audio, -1.0, 1.0)
