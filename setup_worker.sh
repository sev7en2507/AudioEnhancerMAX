#!/bin/bash
# ══════════════════════════════════════════════════════════
# AudioEnhancerMAX — Edge Worker Setup for Termux (Android)
# Run this on your Android phone in Termux:
#   bash setup_worker.sh
# ══════════════════════════════════════════════════════════

set -e

echo "╔══════════════════════════════════════════════════╗"
echo "║  AudioEnhancerMAX — Edge Worker Setup            ║"
echo "║  Setting up your phone as a compute node...      ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# 1. Update packages
echo "▶ [1/6] Updating Termux packages..."
pkg update -y && pkg upgrade -y

# 2. Install system dependencies
echo "▶ [2/6] Installing system dependencies..."
pkg install -y python git build-essential cmake libopenblas patchelf

# 3. Install Python system packages (avoid compilation issues)
echo "▶ [3/6] Installing Python scientific packages..."
pkg install -y python-numpy python-scipy

# 4. Create project directory
echo "▶ [4/6] Setting up project directory..."
WORKER_DIR="$HOME/audioenhancer-worker"
mkdir -p "$WORKER_DIR"
cd "$WORKER_DIR"

# 5. Create virtual environment and install pip packages
echo "▶ [5/6] Installing Python packages..."
python3 -m venv --system-site-packages .venv
source .venv/bin/activate

pip install --upgrade pip
pip install fastapi uvicorn soundfile noisereduce psutil httpx

# Try pedalboard (may fail on some ARM devices)
pip install pedalboard 2>/dev/null || echo "⚠ pedalboard not available on this device (DSP will use fallback)"

# 6. Download worker script
echo "▶ [6/6] Downloading edge worker..."

# If MAC_IP is set, download from orchestrator
if [ -n "$MAC_IP" ]; then
    curl -sSL "http://${MAC_IP}:8000/static/edge_worker.py" -o edge_worker.py
else
    echo "⚠ MAC_IP not set. Please copy edge_worker.py manually."
    echo "   Example: scp user@mac:~/AudioEnhancer/app/services/edge_worker.py ."
fi

# Create launcher script
cat > start_worker.sh << 'LAUNCHER'
#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate

# Auto-detect device name
DEVICE_MODEL=$(getprop ro.product.model 2>/dev/null || echo "Android Device")
WORKER_NAME="${DEVICE_MODEL}"

echo "🚀 Starting AudioEnhancerMAX Edge Worker..."
echo "   Device: $DEVICE_MODEL"
echo "   Port: 8877"
echo ""

python3 edge_worker.py --port 8877 --name "$WORKER_NAME"
LAUNCHER
chmod +x start_worker.sh

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  ✅ Setup complete!                              ║"
echo "║                                                  ║"
echo "║  To start the worker:                            ║"
echo "║    cd ~/audioenhancer-worker                     ║"
echo "║    ./start_worker.sh                             ║"
echo "║                                                  ║"
echo "║  The worker will auto-announce on the network.   ║"
echo "║  Or add manually from AudioEnhancerMAX UI:       ║"
echo "║    Enter this phone's IP address + port 8877     ║"
echo "╚══════════════════════════════════════════════════╝"
