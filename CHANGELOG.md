# Changelog

All notable changes to AudioEnhancerMAX are documented here.

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
