# Changelog

All notable changes to AudioEnhancerMAX are documented here.

## [3.0.0] — 2026-04-20

### ⬡ Metal GPU Acceleration
- **NEW**: Apple Metal GPU (PyTorch MPS) for Demucs music separation — up to 3x faster source separation
- **NEW**: Centralized `apple_acceleration.py` module — configures MPS, Apple Accelerate (vDSP), ARM NEON, MPS GC allocator at startup
- **NEW**: Environment auto-configuration: `PYTORCH_MPS_HIGH_WATERMARK_RATIO`, `PYTORCH_ENABLE_MPS_FALLBACK`, `PYTORCH_MPS_ALLOCATOR_POLICY`
- CTranslate2 4.7.1 ARM NEON confirmed active for faster-whisper inference
- pyannote.audio diarization already on MPS (verified)
- API: `GET /api/acceleration` — shows active hardware acceleration configuration

### 📱 Android Companion App (NEW)
- **NEW**: Native Kotlin Android worker app (`android-worker/`)
- Material 3 UI with real-time task status, connection indicator, and device stats
- HTTP server on port 8080 for receiving DSP tasks from the Mac master
- Auto-discovery: smartphone pings master via UDP on startup — zero configuration
- Supports: noise removal, studio sound, auto EQ, normalization, frequency restoration
- Compatible with Samsung S24 Ultra, Xiaomi 17 Ultra, and any Android 8+ device via Termux

### 🏁 DSP Benchmark System
- **NEW**: Built-in benchmark suite testing FFT, FIR filtering, spectral gating, and resampling
- Runs automatically at server startup (background thread, non-blocking)
- M3 Max baseline: 112 ops/s overall (FFT 264 ops/s, Resample 356 ops/s)
- API: `GET /api/benchmark` — compare Mac master vs all Edge workers
- Benchmark score displayed in processing dashboard and About panel

### 📊 Enhanced Processing Dashboard
- **NEW**: Per-core CPU heatmap (16 cells, red/yellow/green by load) — shows P-cores vs E-cores activity
- **NEW**: Power consumption (watts), CPU frequency (GHz), ANE percentage, benchmark score chips
- Health API enriched: `cpu_per_core`, `cpu_freq_ghz`, `gpu_freq_ghz`, `timestamp`, `benchmark_score`
- Filter capability badges: `⬡ Metal` (green) for GPU-accelerated, `ML` (amber) for AI inference, `Edge` (cyan) for distributable

### ⚙️ Settings Panel (NEW)
- **NEW**: In-app configuration panel with 4 groups: Processing, Edge Cluster, Monitoring, AI Engine
- Settings: output format (WAV/FLAC/MP3), target LUFS, processing priority, worker timeout
- Toggle switches for auto-discovery, DSP offloading, per-core CPU display, dynamic tuning
- Whisper model size selector (base/medium/large-v3)

### ℹ️ About Panel (NEW)
- **NEW**: Comprehensive About page with architecture grid, v3.0 changelog, hardware acceleration status
- Live system info populated from `/api/health` and `/api/acceleration` endpoints
- Update instructions, license info, and credits for all open-source dependencies

### 🌐 Landing Page v3.0
- Complete redesign with cutting-edge aesthetics: animated ambient orbs, glassmorphism nav, scroll-reveal animations
- Feature cards with technology badges (Metal, AI, Edge, DSP)
- Interactive architecture diagram showing master-worker topology
- Benchmark results section with real M3 Max performance data
- Competitor comparison table: vs Adobe Podcast, Descript, Auphonic, iZotope RX 11
- CTA section with clone command and GitHub links
- Standalone HTML — deployable to Hostinger without dependencies

### 🔧 Backend
- Version bumped to 3.0.0 (FastAPI app + health endpoint)
- Sidebar version badge showing `v3.0.0 · M3 Max`
- All new files: `app/services/apple_acceleration.py`, `app/services/benchmark.py`


## [2.0.0] — 2026-04-17

### 🚀 Major — Processing Engine v2.0
- **Fixed metallic audio artifacts** across all filters
- **Noise Removal**: Capped prop_decrease at 0.85, added temporal (100ms) and frequency (500Hz) smoothing, wet/dry mixing
- **Studio Sound**: Broadcast-quality compression (25ms attack, 2:1 ratio, -18dB threshold), de-esser (6kHz -3dB), warmth boost (150Hz +1dB)
- **Specific Noise Filters**: Reduced aggressiveness for wind, static, and reverb removal
- **Speech Cleanup**: Breath removal capped at 80% with 30ms fades, improved mouth click detection
- **Super-Resolution**: Subtler harmonic blending (alpha 0.15), faster rolloff

### 🧠 AI — Gemma 4 Dynamic Tuning
- NEW: `get_dynamic_parameters()` — Gemma 4 analyzes audio and tunes every filter's strength
- Heuristic fallback with 3-tier quality classification (clean/moderate/noisy)
- Safety caps: all strengths between 0.1 and 0.85

### 📊 System Monitor
- NEW: Real-time CPU, GPU, ANE, RAM, Power, Temperature monitoring
- psutil for CPU/RAM + macmon pipe for Apple Silicon GPU/ANE (no sudo)
- 60-second rolling history for sparkline charts
- API: `GET /api/system/stats`, `GET /api/system/history`

### 🌐 Edge Computing Cluster
- NEW: Turn Android smartphones into compute nodes via Termux
- Cluster manager with UDP auto-discovery and manual registration
- Parallel chunk processing with crossfade reassembly
- Automatic fallback to local processing on worker failure
- Setup script for Termux: `setup_worker.sh`
- API: `GET /api/cluster/status`, `POST /api/cluster/add`, `POST /api/cluster/remove`

### ⏱️ ETA Engine
- NEW: 16 per-filter benchmarks calibrated for M3 MAX
- ETA badges on preset cards and process button
- Live ETA refinement during processing via WebSocket

### 🌐 Landing Page
- NEW: Bilingual (EN/IT) landing page at `/landing`
- All 16+ modules detailed with technology tags
- Competitor comparison table: vs Adobe Podcast, Descript, Auphonic, iZotope RX 11

### 📦 Infrastructure
- Added `psutil`, `httpx` to requirements
- Installed `macmon` for Apple Silicon GPU monitoring
- Startup hooks for System Monitor and Cluster Manager

## [1.0.0] — 2026-04-06

### Initial Release
- 16 audio processing filters
- Whisper Large-v3 transcription
- Gemma 4 Smart Mode (content classification)
- Glassmorphism dark UI
- WebSocket real-time progress
- Smart presets (Podcast, Interview, Voice Memo, Music, Outdoor)
