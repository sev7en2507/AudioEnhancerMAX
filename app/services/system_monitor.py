"""
AudioEnhancerMAX by Fd — System Monitor Service
Real-time CPU/GPU/ANE/RAM monitoring for Apple Silicon M3 MAX.
Uses psutil (CPU/RAM) + macmon pipe (GPU/ANE/Power/Thermal).
"""
import asyncio
import json
import logging
import platform
import shutil
import subprocess
import threading
import time
from collections import deque
from typing import Optional

import psutil

logger = logging.getLogger(__name__)

# Rolling history (60 seconds at 1-second intervals)
_HISTORY_SIZE = 60


class SystemMonitor:
    """Collects real-time system metrics for Apple Silicon."""

    def __init__(self):
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._macmon_proc: Optional[subprocess.Popen] = None

        # Current snapshot
        self._current = {
            "cpu_percent": 0.0,
            "cpu_per_core": [],
            "ram_percent": 0.0,
            "ram_used_gb": 0.0,
            "ram_total_gb": 0.0,
            "gpu_percent": 0.0,
            "ane_percent": 0.0,
            "power_watts": 0.0,
            "thermal_pressure": "nominal",
            "cpu_freq_ghz": 0.0,
            "gpu_freq_ghz": 0.0,
            "swap_used_gb": 0.0,
            "disk_read_mb_s": 0.0,
            "disk_write_mb_s": 0.0,
            "net_sent_mb_s": 0.0,
            "net_recv_mb_s": 0.0,
            "timestamp": 0.0,
            "platform": platform.machine(),
            "chip": self._detect_chip(),
            "macmon_available": False,
        }

        # History ring buffers
        self._history = {
            "cpu_percent": deque(maxlen=_HISTORY_SIZE),
            "gpu_percent": deque(maxlen=_HISTORY_SIZE),
            "ane_percent": deque(maxlen=_HISTORY_SIZE),
            "ram_percent": deque(maxlen=_HISTORY_SIZE),
            "power_watts": deque(maxlen=_HISTORY_SIZE),
            "timestamps": deque(maxlen=_HISTORY_SIZE),
        }

        # I/O counters for delta calculation
        self._prev_disk = None
        self._prev_net = None
        self._prev_time = time.time()

    @staticmethod
    def _detect_chip() -> str:
        """Detect Apple Silicon chip name."""
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip()
        except Exception:
            return platform.processor() or "Unknown"

    def _find_macmon(self) -> Optional[str]:
        """Find macmon binary."""
        paths = [
            shutil.which("macmon"),
            "/opt/homebrew/bin/macmon",
            "/usr/local/bin/macmon",
        ]
        for p in paths:
            if p and shutil.which(p.split("/")[-1]) or (p and __import__("os").path.isfile(p)):
                return p
        return None

    def start(self):
        """Start the monitoring background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(f"System monitor started (chip: {self._current['chip']})")

    def stop(self):
        """Stop monitoring."""
        self._running = False
        if self._macmon_proc:
            self._macmon_proc.terminate()
        if self._thread:
            self._thread.join(timeout=3)

    def _monitor_loop(self):
        """Main monitoring loop running in background thread."""
        # Try to start macmon pipe
        macmon_path = self._find_macmon()
        if macmon_path:
            try:
                self._macmon_proc = subprocess.Popen(
                    [macmon_path, "pipe", "--interval", "1000"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                )
                self._current["macmon_available"] = True
                logger.info(f"macmon pipe started: {macmon_path}")
            except Exception as e:
                logger.warning(f"macmon failed to start: {e}")
                self._macmon_proc = None
        else:
            logger.info("macmon not found — GPU/ANE metrics unavailable, using CPU/RAM only")

        while self._running:
            try:
                self._collect_psutil_metrics()

                if self._macmon_proc and self._macmon_proc.stdout:
                    self._collect_macmon_metrics()

                # Update history
                with self._lock:
                    now = time.time()
                    self._history["cpu_percent"].append(self._current["cpu_percent"])
                    self._history["gpu_percent"].append(self._current["gpu_percent"])
                    self._history["ane_percent"].append(self._current["ane_percent"])
                    self._history["ram_percent"].append(self._current["ram_percent"])
                    self._history["power_watts"].append(self._current["power_watts"])
                    self._history["timestamps"].append(now)
                    self._current["timestamp"] = now

                time.sleep(1)
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                time.sleep(2)

    def _collect_psutil_metrics(self):
        """Collect CPU, RAM, disk, network metrics via psutil."""
        now = time.time()
        dt = now - self._prev_time

        # CPU
        cpu_pct = psutil.cpu_percent(interval=None)
        cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)
        cpu_freq = psutil.cpu_freq()

        # RAM
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # Disk I/O delta
        disk = psutil.disk_io_counters()
        disk_read = 0.0
        disk_write = 0.0
        if self._prev_disk and dt > 0:
            disk_read = (disk.read_bytes - self._prev_disk.read_bytes) / dt / 1024 / 1024
            disk_write = (disk.write_bytes - self._prev_disk.write_bytes) / dt / 1024 / 1024
        self._prev_disk = disk

        # Network I/O delta
        net = psutil.net_io_counters()
        net_sent = 0.0
        net_recv = 0.0
        if self._prev_net and dt > 0:
            net_sent = (net.bytes_sent - self._prev_net.bytes_sent) / dt / 1024 / 1024
            net_recv = (net.bytes_recv - self._prev_net.bytes_recv) / dt / 1024 / 1024
        self._prev_net = net

        self._prev_time = now

        with self._lock:
            self._current.update({
                "cpu_percent": round(cpu_pct, 1),
                "cpu_per_core": [round(c, 1) for c in cpu_per_core],
                "cpu_freq_ghz": round(cpu_freq.current / 1000, 2) if cpu_freq else 0,
                "ram_percent": round(mem.percent, 1),
                "ram_used_gb": round(mem.used / 1024**3, 2),
                "ram_total_gb": round(mem.total / 1024**3, 2),
                "swap_used_gb": round(swap.used / 1024**3, 2),
                "disk_read_mb_s": round(max(0, disk_read), 1),
                "disk_write_mb_s": round(max(0, disk_write), 1),
                "net_sent_mb_s": round(max(0, net_sent), 2),
                "net_recv_mb_s": round(max(0, net_recv), 2),
            })

    def _collect_macmon_metrics(self):
        """Collect GPU/ANE/Power metrics from macmon pipe output."""
        try:
            line = self._macmon_proc.stdout.readline()
            if not line:
                return

            data = json.loads(line.strip())

            with self._lock:
                # macmon output fields vary by version
                self._current["gpu_percent"] = round(
                    data.get("gpu_usage", data.get("gpu", {}).get("active", 0)) * 100
                    if isinstance(data.get("gpu_usage", 0), float) and data.get("gpu_usage", 0) <= 1
                    else data.get("gpu_usage", 0), 1
                )
                self._current["ane_percent"] = round(
                    data.get("ane_usage", data.get("ane", {}).get("active", 0)) * 100
                    if isinstance(data.get("ane_usage", 0), float) and data.get("ane_usage", 0) <= 1
                    else data.get("ane_usage", 0), 1
                )
                self._current["power_watts"] = round(
                    data.get("power", data.get("sys_power", data.get("package_w", 0))), 1
                )
                self._current["thermal_pressure"] = data.get(
                    "thermal_pressure", data.get("thermal", "nominal")
                )
                gpu_freq = data.get("gpu_freq", data.get("gpu", {}).get("freq", 0))
                if gpu_freq > 100:  # MHz
                    self._current["gpu_freq_ghz"] = round(gpu_freq / 1000, 2)
                elif gpu_freq > 0:  # Already GHz
                    self._current["gpu_freq_ghz"] = round(gpu_freq, 2)

        except json.JSONDecodeError:
            pass
        except Exception as e:
            logger.debug(f"macmon parse error: {e}")

    def get_stats(self) -> dict:
        """Get current system stats snapshot."""
        with self._lock:
            return dict(self._current)

    def get_history(self) -> dict:
        """Get last 60 seconds of metrics history."""
        with self._lock:
            return {
                k: list(v) for k, v in self._history.items()
            }


# Global singleton
system_monitor = SystemMonitor()
