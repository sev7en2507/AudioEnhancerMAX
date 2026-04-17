<div align="center">

# 🎙️ AudioEnhancerMAX

### The Open-Source AI Audio Media Center

**Next-gen, AI-powered audio processing suite for podcasters, creators and professionals.**<br>
**16+ intelligent filters · Gemma 4 AI · Edge Computing · 100% Local · Zero Cloud**

[![License: MIT](https://img.shields.io/badge/License-MIT-7c3aed.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-06b6d4.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-10b981.svg)](https://fastapi.tiangolo.com)
[![Apple Silicon](https://img.shields.io/badge/Apple_Silicon-Optimized-f59e0b.svg)](#)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[**Features**](#-features) · [**Download**](#-download--installation) · [**Use Cases**](#-use-cases) · [**Architecture**](#-architecture) · [**Docs**](#-documentation) · [**Contributing**](#-contributing) · [**Landing Page**](/frontend/landing.html)

---

<img src="frontend/img/screenshot.png" alt="AudioEnhancerMAX Dashboard" width="800">

*Professional-grade audio processing running entirely on your hardware — no subscriptions, no cloud, no limits.*

</div>

---

## 🎯 What is AudioEnhancerMAX?

AudioEnhancerMAX is the **open-source audio media center** — a unified, beautiful, AI-powered suite that turns raw recordings into broadcast-quality audio. Think of it as the **XMB Media Center, but for audio processing**.

Unlike cloud-based tools (Adobe Podcast, Descript, Auphonic), AudioEnhancerMAX runs **100% locally** on your hardware. Your audio never leaves your machine. No subscriptions. No hourly limits. No compromises.

**Built for Apple Silicon M3 MAX** with distributed edge computing support — turn your Android smartphones into additional compute nodes.

---

## ✨ Features

### 🔇 Noise Removal
| Feature | Technology | Description |
|---------|-----------|-------------|
| **AI Noise Removal** | DeepFilterNet v3 + noisereduce | Background noise removal with wet/dry mixing and temporal smoothing. Zero metallic artifacts. |
| **Wind Noise Remover** | Butterworth + Spectral Gating | Tuned for outdoor recordings. Gentle blend preserves voice warmth. |
| **Buzzing Remover** | Notch Filter | Targets 50/60Hz electrical hum and harmonics. Auto-detects mains frequency. |
| **Static Noise Remover** | Spectral Gating | Stationary noise with frequency/temporal smoothing. Capped at 85% with wet/dry mix. |
| **Reverb & Echo Remover** | Spectral Subtraction | Harmonic-preserving floor removes room ambience without destroying voice texture. |

### 💬 Speech Cleanup
| Feature | Technology | Description |
|---------|-----------|-------------|
| **Filler Word Removal** | Whisper Large-v3 | Removes "uhm", "eh", "cioè", "basically" — 20+ fillers in English & Italian. |
| **Hesitation Eliminator** | Whisper Large-v3 | Detects false starts, mid-sentence pauses. Surgical removal preserving flow. |
| **Stuttering Removal** | Whisper Large-v3 | Finds repeated syllables/fragments. Keeps only the final complete utterance. |
| **Breath Reduction** | DSP | v2.0: Caps at 80% attenuation with 30ms crossfades. Natural, no "holes". |
| **Mouth Sound Removal** | Spectral Flux Analysis | Detects clicks and lip smacks. Local-average interpolation for smooth repair. |

### 🎙️ Audio Enhancement
| Feature | Technology | Description |
|---------|-----------|-------------|
| **Studio Sound v2.0** | Pedalboard (Spotify) | Broadcast-quality chain: warmth (150Hz), presence (4kHz), de-esser (6kHz), gentle 2:1 compression. |
| **Auto EQ** | Pedalboard | Broadcast, warm, and natural profiles with intelligent frequency shaping. |
| **Loudness Normalization** | pyloudnorm | Target LUFS normalization for podcast and broadcast standards. |
| **Audio Super-Resolution** | DSP | Upsamples to 48kHz with subtle harmonic enhancement. |
| **Music Preservation** | Demucs (Meta) | Source separation keeps background music while processing speech. |

### 🧠 AI Intelligence
| Feature | Technology | Description |
|---------|-----------|-------------|
| **Smart Mode** | Gemma 4 E2B (Ollama) | Auto-classifies content (podcast, interview, voice memo, music, outdoor) and selects optimal preset. |
| **Dynamic Parameter Tuning** | Gemma 4 E2B | Analyzes audio SNR/spectrum and tunes every filter's strength individually. Clean audio → lighter processing. |
| **AI Transcription** | Whisper Large-v3 | Word-level transcription with timestamps. Export to TXT, SRT, VTT, JSON. 99+ languages. |
| **Editing Suggestions** | Gemma 4 E2B | AI recommends specific editing improvements based on content analysis. |

### 🌐 Edge Computing & Monitoring
| Feature | Technology | Description |
|---------|-----------|-------------|
| **Distributed Processing** | FastAPI Workers | Turn Android smartphones into compute nodes via Termux. DSP filters run in parallel. |
| **Auto-Discovery** | UDP Broadcast | Workers announce themselves on the network. Zero configuration. |
| **System Monitor** | psutil + macmon | Real-time CPU, GPU, ANE, RAM, Power, Temperature. 60-second sparkline history. |
| **ETA Engine** | Per-filter Benchmarks | 16 individual filter benchmarks calibrated for M3 MAX. Live progress with per-step timing. |

---

## 📋 Use Cases

### 🎙️ Podcast Production
> Upload raw recording → Smart Mode detects "podcast" → Gemma 4 tunes parameters for clean indoor recording → Auto-remove fillers, normalize loudness, apply broadcast EQ → Export production-ready episode.

### 🎤 Interview Cleanup
> Multi-speaker recording → Remove background noise, breaths, hesitations → Preserve natural conversation flow → Normalize per-speaker volume → Export with chapter markers.

### 🏞️ Outdoor Recording Rescue
> Noisy outdoor recording → Wind noise remover + static remover + AI noise reduction → Reverb removal → Studio sound polish → Transform unusable audio into clean voiceover.

### 🎮 Sound Design
> Game dialogue → Remove room ambience → Super-resolution upsampling → Normalize → Export multi-format (WAV, FLAC, MP3) for game engine integration.

### ⚡ Batch Processing with Edge Computing
> 10 podcast episodes → Connect Android phones as workers → Distributed processing across Mac + S24 Ultra + Xiaomi 17 Ultra → 3x faster batch completion.

---

## 📦 Download & Installation

### Requirements
- **Python** 3.10+
- **macOS** 14+ (Apple Silicon recommended) / Linux / Windows
- **FFmpeg** (for audio format conversion)
- **Ollama** + Gemma 4 model (optional, for AI features)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/AudioEnhancerMAX.git
cd AudioEnhancerMAX

# Install dependencies
pip install -r requirements.txt

# Install FFmpeg (macOS)
brew install ffmpeg

# (Optional) Install Ollama + Gemma 4 for AI features
# See: https://ollama.com
ollama pull gemma4:e2b

# Launch
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000** in your browser.

### Edge Workers (Android)
```bash
# On your Android phone in Termux:
bash setup_worker.sh
./start_worker.sh
```
See [Edge Computing Setup Guide](docs/edge-computing.md) for details.

---

## 🎵 Supported Formats

### Input
| Format | Extensions |
|--------|-----------|
| Uncompressed | `.wav`, `.aiff` |
| Lossless | `.flac` |
| Lossy | `.mp3`, `.aac`, `.ogg`, `.m4a`, `.wma` |
| Video (audio extraction) | `.mp4` |

### Output
| Format | Quality |
|--------|---------|
| WAV | 32-bit float, up to 96kHz |
| FLAC | Lossless compression |
| MP3 | VBR, up to 320kbps |

### Internal Processing
- **32-bit float** throughout the pipeline
- **Non-destructive**: original file is never modified
- **Sample rates**: 16kHz to 96kHz, with super-resolution upsampling

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                   AudioEnhancerMAX — System Architecture           │
├────────────────────────┬────────────────────────────────────────────┤
│  🖥️  M3 MAX (Master)   │  📱 Edge Workers (Android via Termux)     │
│                        │                                            │
│  ┌────────────────┐    │  ┌─────────────┐  ┌────────────────────┐  │
│  │ FastAPI Backend │    │  │ S24 Ultra    │  │ Xiaomi 17 Ultra    │  │
│  │ ├─ Whisper      │◄──┼─►│ noisereduce  │  │ noisereduce        │  │
│  │ ├─ Demucs       │    │  │ pedalboard   │  │ pedalboard         │  │
│  │ ├─ Gemma 4      │    │  │ scipy/DSP    │  │ scipy/DSP          │  │
│  │ └─ Cluster Mgr  │    │  └─────────────┘  └────────────────────┘  │
│  └────────────────┘    │        Wi-Fi LAN / HTTP + UDP Discovery    │
│  ┌────────────────┐    │                                            │
│  │ System Monitor  │    │                                            │
│  │ CPU·GPU·ANE·RAM │    │                                            │
│  └────────────────┘    │                                            │
├────────────────────────┴────────────────────────────────────────────┤
│  🌐 Frontend — Glassmorphism Dark UI                                │
│  ├─ Processing Dashboard · ETA Engine · Smart Presets               │
│  ├─ System Monitor Panel · Cluster Management                       │
│  └─ Waveform Viewer · Transcription · TTS                          │
└─────────────────────────────────────────────────────────────────────┘
```

### Tech Stack
| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI, Python 3.10+ |
| **AI Models** | Whisper Large-v3, Gemma 4 E2B (Ollama), Demucs |
| **DSP** | Pedalboard (Spotify), noisereduce, librosa, scipy |
| **Frontend** | Vanilla JS, CSS (glassmorphism dark theme) |
| **Monitoring** | psutil, macmon (Apple Silicon GPU/ANE) |
| **Edge Computing** | FastAPI workers, UDP auto-discovery |

---

## 🆚 Comparison

| Feature | AudioEnhancerMAX | Adobe Podcast | Descript | Auphonic | iZotope RX 11 |
|---------|:---:|:---:|:---:|:---:|:---:|
| **Price** | **Free / OSS** | $9.99/mo | $24/mo | $11-99/mo | $399-$1,349 |
| **100% Local** | ✅ | ❌ Cloud | ❌ Cloud | ❌ Cloud | ✅ |
| **AI Noise Removal** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Filler Word Removal** | ✅ | ❌ | ✅ | ❌ | ❌ |
| **AI Content Classification** | ✅ Gemma 4 | ❌ | ❌ | ◐ | ❌ |
| **Dynamic Parameter Tuning** | ✅ Gemma 4 | ❌ | ❌ | ◐ | ◐ |
| **Edge Computing Cluster** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **System Monitor (GPU/ANE)** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Audio Super-Resolution** | ✅ 96kHz | ❌ | ❌ | ❌ | ◐ |
| **Processing Limit** | **∞ Unlimited** | 1-4 hrs/day | 10-30 hrs/mo | 2-100 hrs/mo | ∞ |
| **Privacy** | ✅ Always | ❌ | ❌ | ❌ | ✅ |
| **Open Source** | ✅ MIT | ❌ | ❌ | ❌ | ❌ |

---

## 📚 Documentation

- [Getting Started](docs/getting-started.md)
- [Feature Guide](docs/features.md)
- [Edge Computing Setup](docs/edge-computing.md)
- [API Reference](docs/api.md)
- [Troubleshooting / FAQ](docs/faq.md)
- [Changelog](CHANGELOG.md)

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

- 🐛 [Report a Bug](https://github.com/yourusername/AudioEnhancerMAX/issues/new?template=bug_report.md)
- 💡 [Request a Feature](https://github.com/yourusername/AudioEnhancerMAX/issues/new?template=feature_request.md)
- 🌍 [Help Translate](docs/translation.md)

---

## 📜 License

AudioEnhancerMAX is released under the [MIT License](LICENSE).

---

## 🙏 Acknowledgments

Built with these amazing open-source projects:
- [FastAPI](https://fastapi.tiangolo.com) — Backend framework
- [Whisper](https://github.com/openai/whisper) — Speech recognition
- [Pedalboard](https://github.com/spotify/pedalboard) — Audio effects (Spotify)
- [Demucs](https://github.com/facebookresearch/demucs) — Source separation (Meta)
- [noisereduce](https://github.com/timsainb/noisereduce) — Spectral noise reduction
- [Gemma](https://ai.google.dev/gemma) — AI intelligence (Google)
- [macmon](https://github.com/vladkens/macmon) — Apple Silicon monitoring

---

<div align="center">

**AudioEnhancerMAX** by **Fd** · [Landing Page](/frontend/landing.html) · Optimized for Apple Silicon M3 MAX

*The audio media center for the AI era.*

</div>
