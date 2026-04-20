"""
AudioEnhancerMAX by Fd — Main FastAPI Application
Full-featured audio processing dashboard backend.
Optimized for Apple Silicon M3 MAX.
"""
import os
import asyncio
import logging
import uuid
from pathlib import Path
from typing import Optional, List

import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, Query, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import (
    UPLOAD_DIR, OUTPUT_DIR, FRONTEND_DIR,
    ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB
)
from app.models.schemas import (
    ProcessingOptions, ProcessingRequest,
    TranscriptionRequest, TranscriptFormat,
    TTSRequest, FileInfo, ContentType
)
from app.utils.audio_io import (
    generate_file_id, get_upload_path, get_output_path,
    validate_extension, load_audio, save_audio, get_audio_info,
    generate_waveform_data
)
from app.utils.progress import progress_tracker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════
# FastAPI App
# ══════════════════════════════════════════════════════════

app = FastAPI(
    title="AudioEnhancerMAX by Fd",
    description="Professional podcast audio processing suite — Apple Silicon Metal GPU + Edge Cluster computing",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")


# ── Schemas for new endpoints ──

class PresetSaveRequest(BaseModel):
    name: str
    description: str = ""
    options: ProcessingOptions

class BatchRequest(BaseModel):
    file_ids: List[str]
    options: ProcessingOptions
    preset_id: Optional[str] = None

class DiarizationRequest(BaseModel):
    file_id: str
    num_speakers: Optional[int] = None
    min_speakers: int = 1
    max_speakers: int = 10


# ══════════════════════════════════════════════════════════
# Lifecycle — Start/Stop services
# ══════════════════════════════════════════════════════════

@app.on_event("startup")
async def startup_services():
    """Start background services on app startup."""
    # Configure Apple Silicon acceleration (MPS/Metal/Accelerate)
    from app.services.apple_acceleration import configure_apple_acceleration
    configure_apple_acceleration()

    from app.services.system_monitor import system_monitor
    from app.services.cluster_manager import cluster_manager
    system_monitor.start()
    cluster_manager.start()
    logger.info("🚀 System monitor + Cluster manager started")

    # Run DSP benchmark in background (doesn't block startup)
    import threading
    def _run_benchmark():
        from app.services.benchmark import run_dsp_benchmark
        run_dsp_benchmark()
    threading.Thread(target=_run_benchmark, daemon=True).start()


@app.on_event("shutdown")
async def shutdown_services():
    """Stop background services on app shutdown."""
    from app.services.system_monitor import system_monitor
    from app.services.cluster_manager import cluster_manager
    system_monitor.stop()
    cluster_manager.stop()


# ══════════════════════════════════════════════════════════
# Routes — System Monitor
# ══════════════════════════════════════════════════════════

@app.get("/api/system/stats")
async def get_system_stats():
    """Real-time CPU/GPU/ANE/RAM metrics."""
    from app.services.system_monitor import system_monitor
    return system_monitor.get_stats()


@app.get("/api/system/history")
async def get_system_history():
    """Last 60 seconds of metrics history for sparkline charts."""
    from app.services.system_monitor import system_monitor
    return system_monitor.get_history()


# ══════════════════════════════════════════════════════════
# Routes — Cluster Management
# ══════════════════════════════════════════════════════════

@app.get("/api/cluster/status")
async def get_cluster_status():
    """Get connected workers and cluster status."""
    from app.services.cluster_manager import cluster_manager
    return await cluster_manager.get_status()


class WorkerAddRequest(BaseModel):
    ip: str
    port: int = 8877


@app.post("/api/cluster/add")
async def add_cluster_worker(req: WorkerAddRequest):
    """Manually add a worker by IP address."""
    from app.services.cluster_manager import cluster_manager
    return await cluster_manager.add_worker(req.ip, req.port)


@app.post("/api/cluster/remove")
async def remove_cluster_worker(req: WorkerAddRequest):
    """Remove a worker from the cluster."""
    from app.services.cluster_manager import cluster_manager
    return await cluster_manager.remove_worker(req.ip, req.port)


@app.post("/api/cluster/health-check")
async def cluster_health_check():
    """Ping all workers and update their status."""
    from app.services.cluster_manager import cluster_manager
    await cluster_manager.health_check_all()
    return await cluster_manager.get_status()


# ══════════════════════════════════════════════════════════
# Routes — Frontend
# ══════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/landing", response_class=HTMLResponse)
async def serve_landing():
    """Bilingual landing page presenting AudioEnhancerMAX."""
    return FileResponse(str(FRONTEND_DIR / "landing.html"))


# ══════════════════════════════════════════════════════════
# Per-Filter Benchmarks (seconds per 60s of audio on M3 MAX)
# ══════════════════════════════════════════════════════════

FILTER_BENCHMARKS = {
    "remove_noise":          {"seconds_per_60s": 8.0,  "group": "deepfilter"},
    "wind_noise_remover":    {"seconds_per_60s": 2.5,  "group": "dsp"},
    "buzzing_noise_remover": {"seconds_per_60s": 0.5,  "group": "dsp"},
    "static_noise_remover":  {"seconds_per_60s": 2.5,  "group": "dsp"},
    "reverb_echo_remover":   {"seconds_per_60s": 4.0,  "group": "dsp"},
    "remove_filler_words":   {"seconds_per_60s": 35.0, "group": "whisper"},
    "eliminate_hesitations":  {"seconds_per_60s": 35.0, "group": "whisper"},
    "remove_stuttering":     {"seconds_per_60s": 35.0, "group": "whisper"},
    "remove_mouth_sounds":   {"seconds_per_60s": 2.0,  "group": "dsp"},
    "remove_breaths":        {"seconds_per_60s": 3.0,  "group": "dsp"},
    "remove_long_silences":  {"seconds_per_60s": 1.0,  "group": "dsp"},
    "auto_eq":               {"seconds_per_60s": 0.3,  "group": "dsp"},
    "studio_sound":          {"seconds_per_60s": 0.5,  "group": "dsp"},
    "normalize":             {"seconds_per_60s": 0.3,  "group": "dsp"},
    "keep_music":            {"seconds_per_60s": 25.0, "group": "demucs"},
    "frequency_restoration": {"seconds_per_60s": 5.0,  "group": "dsp"},
}

# One-time model load costs per group (seconds)
GROUP_LOAD_COSTS = {
    "deepfilter": 5,
    "whisper": 12,
    "demucs": 8,
    "dsp": 0,
}


# ══════════════════════════════════════════════════════════
# Routes — Estimation
# ══════════════════════════════════════════════════════════

@app.post("/api/estimate")
async def estimate_processing_time(request: ProcessingRequest):
    """Estimate processing time for given options and audio duration."""
    opts = request.options
    file_id = request.file_id

    # Try to get actual duration
    duration = 60.0  # default
    source = _find_source(file_id)
    if source:
        try:
            info = get_audio_info(source)
            duration = info.get("duration", 60.0)
        except Exception:
            pass

    scale = duration / 60.0
    total = 3.0  # base I/O overhead
    breakdown = []
    groups_counted = set()
    opts_dict = opts.model_dump()

    for key, bench in FILTER_BENCHMARKS.items():
        if opts_dict.get(key):
            cost = bench["seconds_per_60s"] * scale
            group = bench["group"]

            # Add model load cost once per group
            if group not in groups_counted and GROUP_LOAD_COSTS.get(group, 0) > 0:
                cost += GROUP_LOAD_COSTS[group]
                groups_counted.add(group)

            total += cost
            breakdown.append({
                "filter": key,
                "estimated_seconds": round(cost, 1),
                "group": group,
            })

    return {
        "estimated_seconds": round(total),
        "audio_duration": round(duration, 1),
        "active_filters": len(breakdown),
        "breakdown": breakdown,
    }


# ══════════════════════════════════════════════════════════
# Routes — Upload
# ══════════════════════════════════════════════════════════

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    if not validate_extension(file.filename):
        raise HTTPException(400, f"Unsupported format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    file_id = generate_file_id()
    ext = Path(file.filename).suffix.lower()
    upload_path = get_upload_path(file_id, ext)

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(400, f"File too large. Max: {MAX_FILE_SIZE_MB}MB")

    with open(upload_path, "wb") as f:
        f.write(content)

    try:
        info = get_audio_info(upload_path)
        audio, sr = load_audio(upload_path)
        wav_path = get_upload_path(file_id, ".wav")
        if ext != ".wav":
            save_audio(audio, sr, wav_path)

        waveform = generate_waveform_data(audio, num_points=500)

        return {
            "file_id": file_id,
            "filename": file.filename,
            "size_bytes": len(content),
            "duration_seconds": info["duration"],
            "sample_rate": info["sample_rate"],
            "channels": info["channels"],
            "format": ext.lstrip("."),
            "bitrate": info.get("bitrate"),
            "waveform_data": waveform,
            "audio_url": f"/api/audio/{file_id}",
        }
    except Exception as e:
        upload_path.unlink(missing_ok=True)
        raise HTTPException(500, f"Failed to process upload: {str(e)}")


@app.get("/api/audio/{file_id}")
async def get_audio(file_id: str, version: str = "original"):
    if version == "processed":
        for ext in [".wav", ".mp3", ".flac"]:
            path = get_output_path(file_id, "_processed", ext)
            if path.exists():
                return FileResponse(str(path), media_type=f"audio/{ext.lstrip('.')}")

    for ext in [".wav", ".mp3", ".mp4", ".flac", ".ogg", ".m4a"]:
        path = get_upload_path(file_id, ext)
        if path.exists():
            return FileResponse(str(path), media_type=f"audio/{ext.lstrip('.')}")

    raise HTTPException(404, "Audio file not found")


# ══════════════════════════════════════════════════════════
# Routes — Processing
# ══════════════════════════════════════════════════════════

@app.post("/api/process")
async def process_audio(request: ProcessingRequest):
    file_id = request.file_id
    options = request.options

    source_path = _find_source(file_id)
    if not source_path:
        raise HTTPException(404, "Source file not found")

    try:
        audio, sr = load_audio(source_path)

        await progress_tracker.send_progress(file_id, "loading", 0.05, "Audio loaded")

        steps = _count_steps(options)
        if steps == 0:
            raise HTTPException(400, "No processing options selected")

        # ── v2.0: Dynamic Parameter Tuning ──
        # Analyze audio and dynamically adjust filter strengths
        # using Gemma 4 (or heuristic fallback) based on actual audio characteristics.
        try:
            from app.services.smart_mode import get_dynamic_parameters
            opts_dict = options.model_dump()
            dynamic_params = get_dynamic_parameters(audio, sr, opts_dict)

            if dynamic_params:
                logger.info(f"v2.0 Dynamic tuning active: {len(dynamic_params)} filters adjusted")
                # Apply dynamic strength overrides
                if "remove_noise" in dynamic_params and hasattr(options, 'noise_reduction_strength'):
                    options.noise_reduction_strength = dynamic_params["remove_noise"]["strength"]
                if "remove_breaths" in dynamic_params and hasattr(options, 'breath_reduction_strength'):
                    options.breath_reduction_strength = dynamic_params["remove_breaths"]["strength"]
                if "remove_mouth_sounds" in dynamic_params and hasattr(options, 'mouth_sound_sensitivity'):
                    options.mouth_sound_sensitivity = dynamic_params["remove_mouth_sounds"]["strength"]

                await progress_tracker.send_progress(
                    file_id, "tuning", 0.08,
                    f"🧠 Dynamic tuning: {len(dynamic_params)} filters optimized for this audio"
                )
        except Exception as e:
            logger.warning(f"Dynamic tuning skipped: {e}")

        current = [0]
        async def step(name, msg):
            current[0] += 1
            await progress_tracker.send_progress(file_id, name, current[0]/steps, msg)

        # ── v2.0: Distributed Edge Processing ──
        # If edge workers are online, offload DSP filters to them in parallel
        try:
            from app.services.cluster_manager import cluster_manager
            opts_dict = options.model_dump()

            if cluster_manager.can_distribute(opts_dict):
                n_workers = len(cluster_manager.online_workers)
                await progress_tracker.send_progress(
                    file_id, "cluster", 0.08,
                    f"🌐 Distributing DSP to {n_workers} edge worker(s)..."
                )

                # Build filter dict for offloadable filters only
                from app.services.cluster_manager import OFFLOADABLE_FILTERS
                offload_opts = {}
                for key in OFFLOADABLE_FILTERS:
                    if opts_dict.get(key):
                        offload_opts[key] = True

                if offload_opts:
                    audio = await cluster_manager.process_distributed(
                        audio, sr, offload_opts,
                        progress_callback=lambda name, pct, msg: progress_tracker.send_progress(file_id, name, pct, msg)
                    )

                    # Mark offloaded DSP filters as done so the local chain skips them
                    distributed_filters = set(offload_opts.keys())
                    logger.info(f"🌐 Distributed processing done for: {distributed_filters}")

                    await progress_tracker.send_progress(
                        file_id, "cluster_done", 0.35,
                        f"🌐 Edge processing complete — {len(distributed_filters)} filters distributed"
                    )
                else:
                    distributed_filters = set()
            else:
                distributed_filters = set()
        except Exception as e:
            logger.warning(f"Distributed processing skipped: {e}")
            distributed_filters = set()

        # ── Processing Chain (order matters!) ──
        # Filters already handled by distributed workers are skipped.

        if options.remove_noise and "remove_noise" not in distributed_filters:
            from app.services.noise_removal import remove_noise
            audio = remove_noise(audio, sr, options.noise_reduction_strength)
            await step("remove_noise", "✓ Noise removal complete")

        if options.wind_noise_remover and "wind_noise_remover" not in distributed_filters:
            from app.services.specific_noise import remove_wind_noise
            audio = remove_wind_noise(audio, sr)
            await step("wind", "✓ Wind noise removed")

        if options.buzzing_noise_remover and "buzzing_noise_remover" not in distributed_filters:
            from app.services.specific_noise import remove_buzzing_noise
            audio = remove_buzzing_noise(audio, sr, options.buzz_frequency_hz)
            await step("buzz", "✓ Buzzing removed")

        if options.static_noise_remover and "static_noise_remover" not in distributed_filters:
            from app.services.specific_noise import remove_static_noise
            audio = remove_static_noise(audio, sr)
            await step("static", "✓ Static noise removed")

        if options.reverb_echo_remover and "reverb_echo_remover" not in distributed_filters:
            from app.services.specific_noise import remove_reverb_echo
            audio = remove_reverb_echo(audio, sr)
            await step("reverb", "✓ Reverb/echo removed")

        if options.remove_mouth_sounds and "remove_mouth_sounds" not in distributed_filters:
            from app.services.speech_cleanup import remove_mouth_sounds
            audio = remove_mouth_sounds(audio, sr, options.mouth_sound_sensitivity)
            await step("mouth", "✓ Mouth sounds removed")

        if options.remove_filler_words:
            from app.services.speech_cleanup import remove_filler_words
            audio = remove_filler_words(audio, sr, options.custom_filler_words)
            await step("fillers", "✓ Filler words removed")

        if options.eliminate_hesitations:
            from app.services.speech_cleanup import eliminate_hesitations
            audio = eliminate_hesitations(audio, sr)
            await step("hesitations", "✓ Hesitations eliminated")

        if options.remove_stuttering:
            from app.services.speech_cleanup import remove_stuttering
            audio = remove_stuttering(audio, sr)
            await step("stutter", "✓ Stuttering removed")

        if options.remove_breaths and "remove_breaths" not in distributed_filters:
            from app.services.speech_cleanup import remove_breaths
            audio = remove_breaths(audio, sr, options.breath_reduction_strength)
            await step("breaths", "✓ Breaths removed")

        if options.remove_long_silences and "remove_long_silences" not in distributed_filters:
            from app.services.silence_removal import remove_long_silences, mute_segments, detect_silences
            if options.mute_segments:
                silences = detect_silences(audio, sr, options.silence_threshold_db, options.min_silence_duration_ms)
                audio = mute_segments(audio, sr, silences)
            else:
                audio = remove_long_silences(audio, sr, options.silence_threshold_db, options.min_silence_duration_ms)
            await step("silence", "✓ Silences processed")

        if options.keep_music:
            from app.services.enhancement import keep_music
            audio = keep_music(audio, sr)
            await step("music", "✓ Music preserved")

        if options.auto_eq and "auto_eq" not in distributed_filters:
            from app.services.enhancement import apply_auto_eq
            audio = apply_auto_eq(audio, sr)
            await step("eq", "✓ AutoEQ applied")

        if options.studio_sound and "studio_sound" not in distributed_filters:
            from app.services.enhancement import apply_studio_sound
            audio = apply_studio_sound(audio, sr)
            await step("studio", "✓ Studio sound applied")

        if options.frequency_restoration and "frequency_restoration" not in distributed_filters:
            from app.services.super_resolution import restore_frequencies
            audio, sr = restore_frequencies(audio, sr, options.target_sample_rate)
            await step("superres", "✓ Frequency restoration complete")

        if options.normalize and "normalize" not in distributed_filters:
            from app.services.enhancement import normalize_volume
            audio = normalize_volume(audio, sr, options.target_loudness_lufs)
            await step("normalize", "✓ Volume normalized")

        # ── Save output ──
        fmt = options.output_format.value
        output_path = get_output_path(file_id, "_processed", f".{fmt}")
        save_audio(audio, sr, output_path, format=fmt)

        waveform = generate_waveform_data(audio, num_points=500)
        result_url = f"/outputs/{file_id}_processed.{fmt}"

        await progress_tracker.send_complete(file_id, result_url)

        return {
            "file_id": file_id,
            "status": "completed",
            "output_url": result_url,
            "duration_seconds": len(audio) / sr,
            "sample_rate": sr,
            "waveform_data": waveform,
            "format": fmt,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        await progress_tracker.send_error(file_id, str(e))
        raise HTTPException(500, f"Processing failed: {str(e)}")


# ══════════════════════════════════════════════════════════
# Routes — Smart Mode (Gemma 4 E2B)
# ══════════════════════════════════════════════════════════

@app.post("/api/smart-mode/{file_id}")
async def smart_mode_analyze(file_id: str):
    source_path = _find_source(file_id)
    if not source_path:
        raise HTTPException(404, "File not found")

    try:
        audio, sr = load_audio(source_path)
        from app.services.smart_mode import analyze_and_suggest
        return analyze_and_suggest(audio, sr)
    except Exception as e:
        raise HTTPException(500, f"Smart mode failed: {str(e)}")


@app.post("/api/smart-mode/{file_id}/suggestions")
async def get_editing_suggestions(file_id: str):
    """Get AI-powered editing suggestions from Gemma 4."""
    source_path = _find_source(file_id)
    if not source_path:
        raise HTTPException(404, "File not found")

    try:
        audio, sr = load_audio(source_path)
        from app.services.smart_mode import get_editing_suggestions
        from app.services.transcription import transcribe

        # Quick transcribe for context
        result = transcribe(audio[:sr*60], sr)  # First 60 seconds
        suggestions = get_editing_suggestions(audio, sr, result.get("text", ""))
        return {"suggestions": suggestions}
    except Exception as e:
        raise HTTPException(500, f"Suggestions failed: {str(e)}")


# ══════════════════════════════════════════════════════════
# Routes — Transcription (STT)
# ══════════════════════════════════════════════════════════

@app.post("/api/transcribe")
async def transcribe_audio(request: TranscriptionRequest):
    source_path = _find_source(request.file_id)
    if not source_path:
        raise HTTPException(404, "File not found")

    try:
        audio, sr = load_audio(source_path)
        from app.services.transcription import transcribe, format_as_srt, format_as_vtt, format_as_json

        result = transcribe(audio, sr, language=request.language)

        formatters = {
            TranscriptFormat.SRT: lambda: format_as_srt(result["segments"]),
            TranscriptFormat.VTT: lambda: format_as_vtt(result["segments"]),
            TranscriptFormat.JSON: lambda: format_as_json(result["segments"], result["text"], result["language"]),
            TranscriptFormat.TXT: lambda: result["text"],
        }
        formatted = formatters.get(request.output_format, lambda: result["text"])()

        return {
            "text": result["text"],
            "language": result["language"],
            "duration": result["duration"],
            "segments": result["segments"],
            "formatted": formatted,
            "format": request.output_format.value,
        }
    except Exception as e:
        raise HTTPException(500, f"Transcription failed: {str(e)}")


# ══════════════════════════════════════════════════════════
# Routes — Text-to-Speech (TTS)
# ══════════════════════════════════════════════════════════

@app.get("/api/tts/voices")
async def get_voices():
    from app.services.tts import get_available_voices
    return {"voices": get_available_voices()}


@app.post("/api/tts/synthesize")
async def synthesize(request: TTSRequest):
    try:
        from app.services.tts import synthesize_speech

        clone_path = None
        if request.clone_voice_file_id:
            clone_path = str(_find_source(request.clone_voice_file_id) or "")

        audio, sr = synthesize_speech(
            text=request.text, language=request.language,
            voice_id=request.voice_id, speed=request.speed,
            pitch=request.pitch, warmth=request.warmth,
            style=request.style, clone_voice_path=clone_path if clone_path else None,
        )

        file_id = generate_file_id()
        output_path = get_output_path(file_id, "_tts", ".wav")
        save_audio(audio, sr, output_path)

        return {
            "file_id": file_id,
            "audio_url": f"/outputs/{file_id}_tts.wav",
            "duration": len(audio) / sr,
        }
    except Exception as e:
        raise HTTPException(500, f"TTS failed: {str(e)}")


# ══════════════════════════════════════════════════════════
# Routes — Speaker Diarization
# ══════════════════════════════════════════════════════════

@app.post("/api/diarize")
async def diarize_audio(request: DiarizationRequest):
    source_path = _find_source(request.file_id)
    if not source_path:
        raise HTTPException(404, "File not found")

    try:
        audio, sr = load_audio(source_path)
        from app.services.diarization import diarize, get_speaker_stats

        segments = diarize(
            audio, sr,
            num_speakers=request.num_speakers,
            min_speakers=request.min_speakers,
            max_speakers=request.max_speakers,
        )
        stats = get_speaker_stats(segments)

        return {
            "file_id": request.file_id,
            "segments": segments,
            "speaker_stats": stats,
            "total_speakers": len(stats),
        }
    except Exception as e:
        raise HTTPException(500, f"Diarization failed: {str(e)}")


# ══════════════════════════════════════════════════════════
# Routes — Audio Watermarking
# ══════════════════════════════════════════════════════════

@app.post("/api/watermark/{file_id}")
async def add_watermark(file_id: str, identifier: str = ""):
    source_path = _find_source(file_id, check_outputs=True)
    if not source_path:
        raise HTTPException(404, "File not found")

    try:
        audio, sr = load_audio(source_path)
        from app.services.watermarking import embed_watermark

        watermarked = embed_watermark(audio, sr, identifier or file_id)
        output_path = get_output_path(file_id, "_watermarked", ".wav")
        save_audio(watermarked, sr, output_path)

        return {
            "file_id": file_id,
            "watermarked_url": f"/outputs/{file_id}_watermarked.wav",
            "status": "watermark_embedded",
        }
    except Exception as e:
        raise HTTPException(500, f"Watermarking failed: {str(e)}")


@app.post("/api/watermark/detect/{file_id}")
async def detect_watermark(file_id: str):
    source_path = _find_source(file_id, check_outputs=True)
    if not source_path:
        raise HTTPException(404, "File not found")

    try:
        audio, sr = load_audio(source_path)
        from app.services.watermarking import detect_watermark as _detect
        result = _detect(audio, sr)
        return {"file_id": file_id, "watermark": result}
    except Exception as e:
        raise HTTPException(500, f"Detection failed: {str(e)}")


# ══════════════════════════════════════════════════════════
# Routes — Presets
# ══════════════════════════════════════════════════════════

@app.get("/api/presets")
async def list_all_presets():
    from app.services.batch_presets import list_presets, get_builtin_presets
    return {
        "builtin": get_builtin_presets(),
        "custom": list_presets(),
    }


@app.post("/api/presets")
async def save_preset(request: PresetSaveRequest):
    from app.services.batch_presets import save_preset
    return save_preset(request.name, request.options, request.description)


@app.get("/api/presets/{preset_id}")
async def get_preset(preset_id: str):
    from app.services.batch_presets import load_preset, get_builtin_presets
    # Check builtin first
    for bp in get_builtin_presets():
        if bp["id"] == preset_id:
            return bp
    result = load_preset(preset_id)
    if not result:
        raise HTTPException(404, "Preset not found")
    return result


@app.delete("/api/presets/{preset_id}")
async def remove_preset(preset_id: str):
    from app.services.batch_presets import delete_preset
    if delete_preset(preset_id):
        return {"status": "deleted"}
    raise HTTPException(404, "Preset not found")


# ══════════════════════════════════════════════════════════
# Routes — Batch Processing
# ══════════════════════════════════════════════════════════

@app.post("/api/batch")
async def start_batch(request: BatchRequest):
    from app.services.batch_presets import create_batch_job, load_preset, get_builtin_presets

    job_id = str(uuid.uuid4())[:12]

    # If preset_id is provided, load its options
    options = request.options
    if request.preset_id:
        for bp in get_builtin_presets():
            if bp["id"] == request.preset_id:
                options = ProcessingOptions(**bp["options"])
                break
        else:
            preset = load_preset(request.preset_id)
            if preset:
                options = ProcessingOptions(**preset["options"])

    job = create_batch_job(job_id, request.file_ids, options)

    # Process files sequentially in background
    asyncio.create_task(_process_batch(job_id, request.file_ids, options))

    return {"job_id": job_id, "status": "started", "total_files": len(request.file_ids)}


@app.get("/api/batch/{job_id}")
async def get_batch_status(job_id: str):
    from app.services.batch_presets import get_batch_job
    job = get_batch_job(job_id)
    if not job:
        raise HTTPException(404, "Batch job not found")
    return job.to_dict()


async def _process_batch(job_id: str, file_ids: List[str], options: ProcessingOptions):
    """Process batch files sequentially."""
    from app.services.batch_presets import update_batch_progress

    for file_id in file_ids:
        try:
            req = ProcessingRequest(file_id=file_id, options=options)
            result = await process_audio(req)
            update_batch_progress(job_id, file_id, {"status": "completed", "output_url": result["output_url"]})
        except Exception as e:
            update_batch_progress(job_id, file_id, {"status": "error", "error": str(e)})


# ══════════════════════════════════════════════════════════
# Routes — Download
# ══════════════════════════════════════════════════════════

@app.get("/api/download/{file_id}")
async def download_file(file_id: str, format: str = "wav", version: str = "processed"):
    suffix = f"_{version}" if version != "original" else ""

    path = get_output_path(file_id, suffix, f".{format}")
    if path.exists():
        return FileResponse(str(path), media_type=f"audio/{format}", filename=f"AudioEnhancerMAX_{file_id}.{format}")

    for ext in [".wav", ".mp3", ".flac"]:
        source = get_output_path(file_id, suffix, ext)
        if source.exists():
            if format != ext.lstrip("."):
                audio, sr = load_audio(source)
                converted = get_output_path(file_id, suffix, f".{format}")
                save_audio(audio, sr, converted, format=format)
                return FileResponse(str(converted), filename=f"AudioEnhancerMAX_{file_id}.{format}")
            return FileResponse(str(source), filename=f"AudioEnhancerMAX_{file_id}{ext}")

    for ext in [".wav", ".mp3", ".mp4", ".flac"]:
        source = get_upload_path(file_id, ext)
        if source.exists():
            return FileResponse(str(source), filename=f"AudioEnhancerMAX_{file_id}{ext}")

    raise HTTPException(404, "File not found")


# ══════════════════════════════════════════════════════════
# WebSocket — Progress
# ══════════════════════════════════════════════════════════

@app.websocket("/ws/progress/{file_id}")
async def websocket_progress(websocket: WebSocket, file_id: str):
    await progress_tracker.connect(file_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        await progress_tracker.disconnect(file_id)


# ══════════════════════════════════════════════════════════
# Health & System
# ══════════════════════════════════════════════════════════

@app.get("/api/health")
async def health():
    import torch
    gpu_info = "Apple Silicon M3 MAX (MPS)" if torch.backends.mps.is_available() else "CPU"

    # Check Ollama / Gemma 4
    gemma_status = "unknown"
    gemma_model = None
    try:
        from app.services.smart_mode import _check_ollama_available
        import app.services.smart_mode as smart_mod
        if _check_ollama_available():
            gemma_status = "available"
            gemma_model = smart_mod.OLLAMA_MODEL
        else:
            gemma_status = "not_running"
    except Exception:
        gemma_status = "error"

    # System utilization (real-time from macmon)
    system_data = {}
    try:
        from app.services.system_monitor import system_monitor
        metrics = system_monitor.get_stats()
        if metrics:
            system_data = {
                "chip": metrics.get("chip", "Apple M3 Max"),
                "cpu_percent": metrics.get("cpu_percent", 0),
                "cpu_per_core": metrics.get("cpu_per_core", []),
                "cpu_freq_ghz": metrics.get("cpu_freq_ghz", 0),
                "gpu_percent": metrics.get("gpu_percent", 0),
                "gpu_freq_ghz": metrics.get("gpu_freq_ghz", 0),
                "ram_percent": metrics.get("ram_percent", 0),
                "ram_used_gb": metrics.get("ram_used_gb", 0),
                "ram_total_gb": metrics.get("ram_total_gb", 0),
                "ane_percent": metrics.get("ane_percent", 0),
                "power_watts": metrics.get("power_watts", 0),
                "thermal_pressure": metrics.get("thermal_pressure", "nominal"),
                "timestamp": metrics.get("timestamp", 0),
            }
            # Include benchmark score if available
            try:
                from app.services.benchmark import get_benchmark_result
                bench = get_benchmark_result()
                if bench:
                    system_data["benchmark_score"] = bench.get("score", 0)
            except Exception:
                pass
    except Exception:
        pass

    return {
        "status": "healthy",
        "app": "AudioEnhancerMAX by Fd",
        "version": "3.0.0",
        "compute": gpu_info,
        "mps_available": torch.backends.mps.is_available(),
        "gemma4_status": gemma_status,
        "gemma_model": gemma_model,
        "system": system_data,
    }


@app.get("/api/acceleration")
async def acceleration_info():
    """Show active hardware acceleration configuration."""
    from app.services.apple_acceleration import get_acceleration_info
    return get_acceleration_info()


@app.get("/api/benchmark")
async def benchmark_results():
    """Get benchmark results for all devices in the cluster."""
    from app.services.benchmark import get_benchmark_result
    from app.services.cluster_manager import cluster_manager

    mac_bench = get_benchmark_result()
    
    # Gather worker benchmarks from cluster status
    workers = []
    try:
        status = await cluster_manager.get_status()
        for w in status.get("workers", []):
            workers.append({
                "name": w.get("device_model", w.get("name", "Unknown")),
                "ip": w.get("ip", ""),
                "status": w.get("status", "offline"),
                "benchmark_score": w.get("benchmark_score", 0),
                "tasks_completed": w.get("tasks_completed", 0),
                "avg_speed": w.get("avg_speed", None),
            })
    except Exception:
        pass

    return {
        "master": {
            "name": "Mac — Master",
            "chip": mac_bench.get("tests", {}).get("fft", {}).get("description", "") if mac_bench else "",
            "score": mac_bench.get("score", 0) if mac_bench else 0,
            "tests": mac_bench.get("tests", {}) if mac_bench else {},
        },
        "workers": workers,
    }


# ══════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════

def _find_source(file_id: str, check_outputs: bool = False) -> Optional[Path]:
    """Find audio file by ID across uploads and outputs."""
    for ext in [".wav", ".mp3", ".mp4", ".flac", ".ogg", ".m4a"]:
        path = get_upload_path(file_id, ext)
        if path.exists():
            return path

    if check_outputs:
        for suffix in ["_processed", "_watermarked", "_tts"]:
            for ext in [".wav", ".mp3", ".flac"]:
                path = get_output_path(file_id, suffix, ext)
                if path.exists():
                    return path
    return None


def _count_steps(options: ProcessingOptions) -> int:
    """Count active processing steps."""
    return sum([
        options.remove_noise, options.remove_long_silences,
        options.remove_mouth_sounds, options.eliminate_hesitations,
        options.remove_stuttering, options.remove_filler_words,
        options.remove_breaths, options.studio_sound,
        options.auto_eq, options.normalize,
        options.keep_music, options.wind_noise_remover,
        options.buzzing_noise_remover, options.static_noise_remover,
        options.reverb_echo_remover, options.frequency_restoration,
    ])
