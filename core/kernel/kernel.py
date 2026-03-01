"""
NEXA Core Kernel
================
Central dispatcher — control plane only, no execution logic.

The kernel is the single authority for:
  1. Receiving all task requests
  2. Checking priority and rejection rules
  3. Allocating GPU resources
  4. Dispatching execution
  5. Monitoring task lifecycle
  6. Tracking system state (locked, media active)

All modules communicate THROUGH the kernel, never directly.
"""

import logging
import threading
from typing import Optional, Callable, Dict, Any

from .event_bus import EventBus
from .priority_manager import PriorityLevel, PriorityManager
from .task_queue import TaskEntry, TaskQueue
from .resource_manager import ResourceManager

logger = logging.getLogger(__name__)


class NexaKernel:
    """
    Central dispatcher for the NEXA AI system.

    Responsibilities:
    - Receive all events
    - Assign priority
    - Allocate resources (GPU VRAM)
    - Dispatch execution via capability registry
    - Monitor task lifecycle
    - Track lock state and media playback state

    Usage:
        kernel = NexaKernel(gpu_monitor=gpu_monitor)
        kernel.register_capability("youtube", handler, PriorityLevel.USER_COMMAND)
        task_id = kernel.submit_task(TaskEntry(
            name="idle_suggestion",
            priority=PriorityLevel.IDLE_SUGGESTION,
        ))
    """

    def __init__(self, gpu_monitor=None):
        """
        Initialize the kernel and all sub-components.

        Args:
            gpu_monitor: Optional GPUMonitor instance for live VRAM readings.
        """
        self.event_bus = EventBus()
        self.priority_mgr = PriorityManager()
        self.task_queue = TaskQueue()
        self.resource_mgr = ResourceManager(gpu_monitor=gpu_monitor)

        # System state
        self._is_locked = False
        self._media_active = False
        self._lock = threading.Lock()

        # ── Capability Registry ─────────────────────────────────────
        # Maps capability names to their handler + default priority.
        # Modules register themselves so the kernel knows every
        # subsystem's entry point and default priority level.
        self._capabilities: Dict[str, Dict[str, Any]] = {}

        # Subscribe to our own events for state tracking
        self.event_bus.subscribe("state.locked", self._on_state_locked)
        self.event_bus.subscribe("state.unlocked", self._on_state_unlocked)
        self.event_bus.subscribe("media.started", self._on_media_started)
        self.event_bus.subscribe("media.stopped", self._on_media_stopped)

        logger.info("🔷 NexaKernel initialized")

    # ── Public API ──────────────────────────────────────────────────

    def submit_task(self, task: TaskEntry) -> Optional[str]:
        """
        Submit a task for execution.

        Flow (from Architecture Plan §4):
        1. Check should_reject() — idle + locked/playing → reject
        2. Compare priority with active task → preempt or queue
        3. If gpu_required → check resource_mgr.can_allocate()
        4. Queue the task
        5. Publish "task.submitted" event

        Args:
            task: TaskEntry describing the work to be done.

        Returns:
            Task ID if accepted, None if rejected.
        """
        # Step 1: Check rejection rules
        if self.priority_mgr.should_reject(
            priority=task.priority,
            is_locked=self.is_locked,
            media_active=self.is_media_active,
            has_active_task=self.task_queue.has_active_tasks(),
        ):
            logger.info(
                f"🔷 Kernel: REJECTED task '{task.name}' "
                f"(priority={task.priority.name}, locked={self.is_locked}, "
                f"media={self.is_media_active})"
            )
            self.event_bus.publish(
                "task.rejected",
                task_name=task.name,
                priority=task.priority,
                reason="rejected_by_priority_rules",
            )
            return None

        # Step 2: Check preemption (informational — we still queue)
        active_task = self.task_queue.peek_active()
        if active_task:
            can_preempt = self.priority_mgr.can_preempt(task.priority, active_task.priority)
            if can_preempt and active_task.interruptible:
                logger.info(
                    f"🔷 Kernel: task '{task.name}' (P{int(task.priority)}) "
                    f"can preempt '{active_task.name}' (P{int(active_task.priority)})"
                )
            elif not can_preempt:
                logger.debug(
                    f"🔷 Kernel: task '{task.name}' (P{int(task.priority)}) "
                    f"queued behind '{active_task.name}' (P{int(active_task.priority)})"
                )

        # Step 3: GPU resource check
        if task.gpu_required and task.estimated_vram_mb > 0:
            if not self.resource_mgr.can_allocate(task.estimated_vram_mb):
                logger.warning(
                    f"🔷 Kernel: task '{task.name}' needs {task.estimated_vram_mb}MB VRAM "
                    f"but insufficient available — queuing anyway"
                )
                # Still queue it — kernel can retry later or caller can check

        # Step 4: Enqueue
        task_id = self.task_queue.submit(task)

        # Step 5: Publish event
        self.event_bus.publish(
            "task.submitted",
            task_id=task_id,
            task_name=task.name,
            priority=task.priority,
        )

        logger.info(
            f"🔷 Kernel: ACCEPTED task '{task.name}' "
            f"(priority={task.priority.name}, id={task_id})"
        )
        return task_id

    def activate_task(self, task: TaskEntry) -> bool:
        """
        Mark a task as actively running and allocate GPU if needed.

        Args:
            task: The task to activate.

        Returns:
            True if activated (and GPU allocated if needed).
        """
        # Allocate GPU resources if required
        if task.gpu_required and task.estimated_vram_mb > 0:
            if not self.resource_mgr.allocate(task.task_id, task.estimated_vram_mb):
                logger.warning(
                    f"🔷 Kernel: cannot activate '{task.name}' — "
                    f"GPU allocation failed ({task.estimated_vram_mb}MB needed)"
                )
                return False
            self.event_bus.publish(
                "gpu.allocated",
                task_id=task.task_id,
                vram_mb=task.estimated_vram_mb,
            )

        self.task_queue.activate_task(task)
        return True

    def complete_task(self, task_id: str) -> None:
        """
        Mark a task as completed and release its resources.

        Args:
            task_id: ID of the completed task.
        """
        task = self.task_queue.complete(task_id)
        if task:
            # Release GPU resources
            released = self.resource_mgr.release(task_id)
            if released:
                self.event_bus.publish(
                    "gpu.released",
                    task_id=task_id,
                    vram_mb=released,
                )

            self.event_bus.publish(
                "task.completed",
                task_id=task_id,
                task_name=task.name,
            )
            logger.info(f"🔷 Kernel: completed task '{task.name}' (id={task_id})")

    def cancel_task(self, task_id: str) -> None:
        """
        Cancel a task and release its resources.

        Args:
            task_id: ID of the task to cancel.
        """
        task = self.task_queue.cancel(task_id)
        if task:
            released = self.resource_mgr.release(task_id)
            if released:
                self.event_bus.publish(
                    "gpu.released",
                    task_id=task_id,
                    vram_mb=released,
                )
            logger.info(f"🔷 Kernel: cancelled task '{task.name}' (id={task_id})")

    # ── System State ────────────────────────────────────────────────

    @property
    def is_locked(self) -> bool:
        """Whether NEXA is in locked state."""
        with self._lock:
            return self._is_locked

    @property
    def is_media_active(self) -> bool:
        """Whether media (NVP, music) is currently playing."""
        with self._lock:
            return self._media_active

    def set_locked(self, locked: bool) -> None:
        """
        Update the lock state and publish the corresponding event.

        Args:
            locked: True to lock, False to unlock.
        """
        with self._lock:
            if self._is_locked == locked:
                return
            self._is_locked = locked

        event = "state.locked" if locked else "state.unlocked"
        self.event_bus.publish(event)
        logger.info(f"🔷 Kernel: {'🔒 LOCKED' if locked else '🔓 UNLOCKED'}")

    def set_media_active(self, active: bool) -> None:
        """
        Update the media playback state and publish the corresponding event.

        Args:
            active: True when media starts, False when it stops.
        """
        with self._lock:
            if self._media_active == active:
                return
            self._media_active = active

        event = "media.started" if active else "media.stopped"
        self.event_bus.publish(event)
        logger.info(f"🔷 Kernel: {'▶️ MEDIA ACTIVE' if active else '⏹️ MEDIA STOPPED'}")

    def can_run_idle(self) -> bool:
        """
        Check if idle/proactive suggestions are allowed right now.

        Governance rules:
        - Disabled when NEXA locked
        - Disabled when media is active (NVP, music playback)
        - Disabled when ANY task is active
        - Disabled when GPU usage > 85%

        Returns:
            True if idle suggestions can proceed.
        """
        if self.is_locked:
            logger.debug("🔷 can_run_idle: blocked (locked)")
            return False

        if self.is_media_active:
            logger.debug("🔷 can_run_idle: blocked (media active)")
            return False

        if self.task_queue.has_active_tasks():
            logger.debug("🔷 can_run_idle: blocked (active tasks)")
            return False

        gpu_pct = self.resource_mgr.get_usage_percent()
        if gpu_pct > 85.0:
            logger.debug(f"🔷 can_run_idle: blocked (GPU at {gpu_pct:.1f}%)")
            return False

        return True

    # ── Capability Registry ─────────────────────────────────────────

    def register_capability(
        self,
        name: str,
        handler: Callable,
        default_priority: PriorityLevel = PriorityLevel.USER_COMMAND,
        gpu_required: bool = False,
        estimated_vram_mb: int = 0,
    ) -> None:
        """
        Register a subsystem capability with the kernel.

        This lets the kernel know which modules exist and their default
        priority/resource requirements.  Modules call this at startup.

        Args:
            name: Unique capability name (e.g., "llm_inference", "tts", "youtube").
            handler: Callable that performs the capability's work.
            default_priority: Default PriorityLevel for tasks from this capability.
            gpu_required: Whether this capability typically needs GPU.
            estimated_vram_mb: Typical VRAM usage in MB.
        """
        self._capabilities[name] = {
            "handler": handler,
            "default_priority": default_priority,
            "gpu_required": gpu_required,
            "estimated_vram_mb": estimated_vram_mb,
        }
        logger.info(
            f"🔷 Kernel: registered capability '{name}' "
            f"(priority={default_priority.name}, gpu={gpu_required})"
        )

    def get_capability(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Look up a registered capability by name.

        Args:
            name: Capability name.

        Returns:
            Capability dict or None if not registered.
        """
        return self._capabilities.get(name)

    def get_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """Return a snapshot of all registered capabilities."""
        return dict(self._capabilities)

    # ── Internal Event Handlers ─────────────────────────────────────

    def _on_state_locked(self, **kwargs) -> None:
        with self._lock:
            self._is_locked = True

    def _on_state_unlocked(self, **kwargs) -> None:
        with self._lock:
            self._is_locked = False

    def _on_media_started(self, **kwargs) -> None:
        with self._lock:
            self._media_active = True

    def _on_media_stopped(self, **kwargs) -> None:
        with self._lock:
            self._media_active = False

    # ── Shutdown ────────────────────────────────────────────────────

    def shutdown(self) -> None:
        """Clean up kernel resources."""
        self.task_queue.clear()
        self.resource_mgr.clear()
        self.event_bus.clear()
        logger.info("🔷 NexaKernel shutdown complete")
