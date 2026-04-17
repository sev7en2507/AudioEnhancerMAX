# Contributing to AudioEnhancerMAX

Thank you for considering contributing to AudioEnhancerMAX! 🎙️

## How to Contribute

### 🐛 Reporting Bugs

1. Check existing [Issues](https://github.com/sev7en2507/AudioEnhancerMAX/issues) to avoid duplicates.
2. Open a new issue using the **Bug Report** template.
3. Include: OS, Python version, steps to reproduce, expected vs actual behavior, audio sample if possible.

### 💡 Suggesting Features

1. Open a new issue using the **Feature Request** template.
2. Describe the use case — who benefits and why.
3. If possible, reference similar implementations in other tools.

### 🔧 Submitting Code

1. **Fork** the repository and create a feature branch:
   ```bash
   git checkout -b feature/my-awesome-feature
   ```

2. **Follow the code style:**
   - Python: PEP 8, type hints where practical
   - JavaScript: ES6+, no frameworks (vanilla JS)
   - CSS: BEM-inspired naming, CSS custom properties

3. **Write meaningful commit messages:**
   ```
   feat(noise): add spectral smoothing to wind noise filter
   fix(enhancement): cap compressor gain to prevent clipping
   docs: add edge computing setup guide
   ```

4. **Test your changes:**
   - Run the server and verify via the UI
   - Test with various audio samples (clean, noisy, outdoor, music)
   - Check for regressions in existing filters

5. **Submit a Pull Request** with:
   - Clear description of what changed and why
   - Before/after comparison if it's a DSP change
   - Screenshots if it's a UI change

### 🌍 Translations

AudioEnhancerMAX supports English and Italian. To add a new language:

1. Add your language strings to `frontend/landing.html`
2. Add UI translations to `frontend/js/app.js`
3. Submit a PR with the language code in the title (e.g., `i18n: add French translations`)

---

## Development Setup

```bash
# Clone and setup
git clone https://github.com/sev7en2507/AudioEnhancerMAX.git
cd AudioEnhancerMAX
pip install -r requirements.txt

# Run with auto-reload
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# (Optional) Install Gemma 4 for AI features
ollama pull gemma4:e2b
```

### Project Structure

```
AudioEnhancerMAX/
├── app/
│   ├── main.py              # FastAPI app + all API routes
│   ├── config.py             # Configuration and defaults
│   ├── models/
│   │   └── schemas.py        # Pydantic models
│   ├── services/
│   │   ├── noise_removal.py  # AI + spectral noise reduction
│   │   ├── enhancement.py    # Studio sound, EQ, normalization
│   │   ├── specific_noise.py # Wind, buzz, static, reverb filters
│   │   ├── speech_cleanup.py # Filler words, breaths, stuttering
│   │   ├── super_resolution.py
│   │   ├── smart_mode.py     # Gemma 4 AI intelligence
│   │   ├── system_monitor.py # CPU/GPU/ANE monitoring
│   │   ├── cluster_manager.py # Distributed processing orchestrator
│   │   ├── edge_worker.py    # Standalone worker for Android
│   │   └── ...
│   └── utils/
│       ├── audio_io.py       # Audio loading/saving
│       └── progress.py       # WebSocket progress tracking
├── frontend/
│   ├── index.html            # Main app UI
│   ├── landing.html          # Product landing page (EN/IT)
│   ├── css/style.css         # Glassmorphism dark theme
│   └── js/app.js             # Frontend logic
├── docs/                     # Documentation
├── setup_worker.sh           # Termux setup for Android workers
├── requirements.txt
├── LICENSE
└── README.md
```

---

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold this code.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
