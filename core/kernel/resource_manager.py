"""
Resource Manager (GPU Scheduler)
================================
Manages GPU VRAM allocation to prevent overload and freezing.

Wraps the existing GPUMonitor for live VRAM readings and adds
allocation gating — tasks must request VRAM before they can run.

VRAM Budget (from Architecture Refactor Plan §5):
  LLaMA 3.1B (quantized) = 3.5GB
  Whisper Base            = 1.0GB
  PaddleOCR              = 1.5GB
  Vision Model           = 2.0GB
  NVP Playback           = 0.5GB

  Total VRAM             = 8GB
  Safe threshold         = 7.2GB (90%)
"""

import logging
import threading
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class ResourceManager:
    """
    GPU VRAM gatekeeper.

    Before a GPU-heavy task runs, the kernel asks:
        resource_mgr.can_allocate(vram_needed)

    If allocation would exceed the safe threshold, the task is
    queued or rejected. On task completion, VRAM is released.
    """

    # Defaults matching a typical 8GB GPU
    DEFAULT_TOTAL_VRAM_MB = 8192
    DEFAULT_SAFE_THRESHOLD_MB = 7372  # ~90% of 8GB

    def __init__(
        self,
        gpu_monitor=None,
        total_vram_mb: int = DEFAULT_TOTAL_VRAM_MB,
        safe_threshold_mb: int = DEFAULT_SAFE_THRESHOLD_MB,
    ):
        """
        Initialize the resource manager.

        Args:
            gpu_monitor: Optional existing GPUMonitor instance for live readings.
            total_vram_mb: Total GPU VRAM in MB.
            safe_threshold_mb: Maximum VRAM usage allowed before rejecting tasks.
        """
        self._gpu_monitor = gpu_monitor
        self._total_vram_mb = total_vram_mb
        self._safe_threshold_mb = safe_threshold_mb

        # Bookkeeping: task_id → allocated VRAM in MB
        self._allocations: Dict[str, int] = {}
        self._lock = threading.Lock()

        logger.info(
            f"📊 ResourceManager: total={total_vram_mb}MB, "
            f"safe_threshold={safe_threshold_mb}MB"
        )

    def set_gpu_monitor(self, gpu_monitor) -> None:
        """Attach or replace the GPU monitor for live readings."""
        self._gpu_monitor = gpu_monitor

    def get_live_usage(self) -> Optional[Tuple[int, int, float]]:
        """
        Get live GPU usage from the monitor.

        Returns:
            (used_mb, total_mb, usage_percent) or None if unavailable.
        """
        if self._gpu_monitor and hasattr(self._gpu_monitor, "get_current_usage"):
            return self._gpu_monitor.get_current_usage()
        return None

    def get_available_vram(self) -> int:
        """
        Estimate available VRAM in MB.

        Uses live GPU readings if available, otherwise falls back to
        bookkeeping-based estimation.

        Returns:
            Available VRAM in MB.
        """
        live = self.get_live_usage()
        if live:
            used_mb, total_mb, _ = live
            return max(0, total_mb - used_mb)

        # Fallback: use bookkeeping
        with self._lock:
            allocated = sum(self._allocations.values())
        return max(0, self._total_vram_mb - allocated)

    def get_usage_percent(self) -> float:
        """
        Get current GPU usage as a percentage (0.0 to 100.0).

        Returns:
            Usage percentage.
        """
        live = self.get_live_usage()
        if live:
            _, _, pct = live
            return pct

        with self._lock:
            allocated = sum(self._allocations.values())
        if self._total_vram_mb == 0:
            return 0.0
        return (allocated / self._total_vram_mb) * 100.0

    def can_allocate(self, vram_needed_mb: int) -> bool:
        """
        Check if the requested VRAM can be safely allocated.

        Args:
            vram_needed_mb: VRAM needed in MB.

        Returns:
            True if allocation would stay within the safe threshold.
        """
        if vram_needed_mb <= 0:
            return True

        available = self.get_available_vram()
        # Check against safe threshold, not total
        live = self.get_live_usage()
        if live:
            used_mb, _, _ = live
            would_use = used_mb + vram_needed_mb
        else:
            with self._lock:
                allocated = sum(self._allocations.values())
            would_use = allocated + vram_needed_mb

        result = would_use <= self._safe_threshold_mb
        if not result:
            logger.warning(
                f"📊 ResourceManager: CANNOT allocate {vram_needed_mb}MB "
                f"(would_use={would_use}MB, threshold={self._safe_threshold_mb}MB)"
            )
        return result

    def allocate(self, task_id: str, vram_mb: int) -> bool:
        """
        Reserve VRAM for a task.

        Args:
            task_id: Unique task identifier.
            vram_mb: VRAM to reserve in MB.

        Returns:
            True if allocated successfully, False if would exceed threshold.
        """
        if vram_mb <= 0:
            return True

        if not self.can_allocate(vram_mb):
            return False

        with self._lock:
            self._allocations[task_id] = vram_mb
            total_booked = sum(self._allocations.values())

        logger.info(
            f"📊 ResourceManager: allocated {vram_mb}MB for task '{task_id}' "
            f"(total booked: {total_booked}MB)"
        )
        return True

    def release(self, task_id: str) -> int:
        """
        Release VRAM reserved by a completed/cancelled task.

        Args:
            task_id: Task whose VRAM to release.

        Returns:
            Amount of VRAM released in MB (0 if task had no allocation).
        """
        with self._lock:
            released = self._allocations.pop(task_id, 0)

        if released:
            logger.info(f"📊 ResourceManager: released {released}MB from task '{task_id}'")

        return released

    def get_allocations(self) -> Dict[str, int]:
        """Get a snapshot of current VRAM allocations."""
        with self._lock:
            return dict(self._allocations)

    def clear(self) -> None:
        """Release all allocations."""
        with self._lock:
            self._allocations.clear()
        logger.debug("📊 ResourceManager: all allocations cleared")
