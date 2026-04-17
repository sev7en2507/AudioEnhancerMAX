"""
AudioEnhancerMAX by Fd — Progress Tracking via WebSocket
"""
import asyncio
import json
import time
from typing import Dict, Optional
from fastapi import WebSocket


class ProgressTracker:
    """Manages WebSocket connections for real-time progress updates."""

    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()
        self._step_timers: Dict[str, float] = {}  # file_id -> step start time
        self._job_timers: Dict[str, float] = {}    # file_id -> job start time

    async def connect(self, file_id: str, websocket: WebSocket):
        """Register a WebSocket connection for a file processing job."""
        await websocket.accept()
        async with self._lock:
            self.connections[file_id] = websocket
            self._job_timers[file_id] = time.monotonic()

    async def disconnect(self, file_id: str):
        """Remove a WebSocket connection."""
        async with self._lock:
            self.connections.pop(file_id, None)
            self._step_timers.pop(file_id, None)
            self._job_timers.pop(file_id, None)

    async def send_progress(
        self,
        file_id: str,
        step: str,
        progress: float,
        message: str,
        status: str = "processing"
    ):
        """Send a progress update to the client."""
        async with self._lock:
            ws = self.connections.get(file_id)
            if ws:
                now = time.monotonic()

                # Calculate step elapsed time
                step_elapsed = 0.0
                if file_id in self._step_timers:
                    step_elapsed = now - self._step_timers[file_id]
                self._step_timers[file_id] = now  # reset for next step

                # Calculate total job elapsed
                job_elapsed = 0.0
                if file_id in self._job_timers:
                    job_elapsed = now - self._job_timers[file_id]

                try:
                    await ws.send_json({
                        "file_id": file_id,
                        "step": step,
                        "progress": min(1.0, max(0.0, progress)),
                        "message": message,
                        "status": status,
                        "step_elapsed_seconds": round(step_elapsed, 2),
                        "total_elapsed_seconds": round(job_elapsed, 2),
                    })
                except Exception:
                    self.connections.pop(file_id, None)

    async def send_complete(self, file_id: str, result_url: str):
        """Send completion notification."""
        await self.send_progress(
            file_id, "complete", 1.0,
            f"Processing complete! Download ready.",
            "completed"
        )
        async with self._lock:
            ws = self.connections.get(file_id)
            if ws:
                try:
                    await ws.send_json({
                        "file_id": file_id,
                        "status": "completed",
                        "result_url": result_url,
                    })
                except Exception:
                    pass

    async def send_error(self, file_id: str, error: str):
        """Send error notification."""
        await self.send_progress(
            file_id, "error", 0.0, f"Error: {error}", "error"
        )


# Global progress tracker instance
progress_tracker = ProgressTracker()

