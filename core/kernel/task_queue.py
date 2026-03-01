"""
Task Queue
==========
Priority-based task queue with lifecycle management.

Each task carries metadata about its priority, GPU requirements,
and interruptibility. The queue is sorted by priority (highest first),
with FIFO ordering within the same priority level.

Task lifecycle: pending → active → completed/cancelled
"""

import logging
import time
import uuid
import threading
import heapq
from dataclasses import dataclass, field
from typing import Callable, Optional, Dict, List, Any

from .priority_manager import PriorityLevel

logger = logging.getLogger(__name__)


@dataclass
class TaskEntry:
    """
    A unit of work submitted to the kernel.

    Attributes:
        name: Human-readable task name (e.g., "play_music", "idle_suggestion").
        priority: Numeric priority level from PriorityLevel enum.
        gpu_required: Whether this task needs GPU/VRAM.
        estimated_vram_mb: Estimated VRAM usage in megabytes.
        interruptible: Whether a higher-priority task can preempt this one.
        callback: Optional callable to execute when the task runs.
        callback_args: Optional positional arguments for the callback.
        callback_kwargs: Optional keyword arguments for the callback.
        status: Current lifecycle state.
        task_id: Unique identifier (auto-generated).
        created_at: Timestamp when the task was created.
    """
    name: str
    priority: PriorityLevel
    gpu_required: bool = False
    estimated_vram_mb: int = 0
    interruptible: bool = True
    callback: Optional[Callable] = field(default=None, repr=False)
    callback_args: tuple = field(default_factory=tuple, repr=False)
    callback_kwargs: Dict[str, Any] = field(default_factory=dict, repr=False)
    status: str = "pending"
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: float = field(default_factory=time.time)

    def __lt__(self, other: "TaskEntry") -> bool:
        """For heapq: higher priority first, then earlier creation time."""
        if self.priority != other.priority:
            return int(self.priority) > int(other.priority)  # higher = first
        return self.created_at < other.created_at  # FIFO for equal priority


class TaskQueue:
    """
    Thread-safe priority queue for task scheduling.

    - submit() adds tasks to the pending queue.
    - The kernel calls next_task() to get the highest-priority pending task.
    - active tasks are tracked separately for preemption checks.
    """

    def __init__(self):
        self._pending: List[TaskEntry] = []   # heapq (min-heap, but __lt__ inverts priority)
        self._active: Dict[str, TaskEntry] = {}
        self._completed: Dict[str, TaskEntry] = {}
        self._lock = threading.Lock()

    def submit(self, task: TaskEntry) -> str:
        """
        Add a task to the pending queue.

        Args:
            task: TaskEntry to enqueue.

        Returns:
            The task's unique ID.
        """
        with self._lock:
            task.status = "pending"
            heapq.heappush(self._pending, task)
            logger.debug(
                f"📋 TaskQueue: submitted '{task.name}' "
                f"(priority={task.priority.name}, id={task.task_id})"
            )
            return task.task_id

    def next_task(self) -> Optional[TaskEntry]:
        """
        Pop the highest-priority pending task.

        Returns:
            The next TaskEntry to execute, or None if queue is empty.
        """
        with self._lock:
            while self._pending:
                task = heapq.heappop(self._pending)
                if task.status == "pending":
                    return task
                # skip cancelled tasks that were still in the heap
            return None

    def activate(self, task_id: str) -> bool:
        """
        Mark a task as actively running.

        Args:
            task_id: ID of the task to activate.

        Returns:
            True if the task was found and activated.
        """
        with self._lock:
            # Search pending queue
            for task in self._pending:
                if task.task_id == task_id and task.status == "pending":
                    task.status = "active"
                    self._active[task_id] = task
                    logger.debug(f"📋 TaskQueue: activated '{task.name}' (id={task_id})")
                    return True
            return False

    def activate_task(self, task: TaskEntry) -> None:
        """
        Directly mark a task as active (used by kernel after popping from queue).

        Args:
            task: The TaskEntry to mark active.
        """
        with self._lock:
            task.status = "active"
            self._active[task.task_id] = task
            logger.debug(f"📋 TaskQueue: activated '{task.name}' (id={task.task_id})")

    def complete(self, task_id: str) -> Optional[TaskEntry]:
        """
        Mark a task as completed and remove from active set.

        Args:
            task_id: ID of the task to complete.

        Returns:
            The completed TaskEntry, or None if not found.
        """
        with self._lock:
            task = self._active.pop(task_id, None)
            if task:
                task.status = "completed"
                self._completed[task_id] = task
                logger.debug(f"📋 TaskQueue: completed '{task.name}' (id={task_id})")

                # Keep completed history bounded
                if len(self._completed) > 100:
                    oldest_key = next(iter(self._completed))
                    del self._completed[oldest_key]

            return task

    def cancel(self, task_id: str) -> Optional[TaskEntry]:
        """
        Cancel a task (pending or active).

        Args:
            task_id: ID of the task to cancel.

        Returns:
            The cancelled TaskEntry, or None if not found.
        """
        with self._lock:
            # Check active first
            task = self._active.pop(task_id, None)
            if task:
                task.status = "cancelled"
                logger.debug(f"📋 TaskQueue: cancelled active '{task.name}' (id={task_id})")
                return task

            # Check pending (mark as cancelled; will be skipped on pop)
            for t in self._pending:
                if t.task_id == task_id and t.status == "pending":
                    t.status = "cancelled"
                    logger.debug(f"📋 TaskQueue: cancelled pending '{t.name}' (id={task_id})")
                    return t

            return None

    def peek_active(self) -> Optional[TaskEntry]:
        """
        Get the highest-priority currently active task.

        Returns:
            The highest-priority active TaskEntry, or None.
        """
        with self._lock:
            if not self._active:
                return None
            return max(self._active.values(), key=lambda t: int(t.priority))

    def has_active_tasks(self) -> bool:
        """Check if any tasks are currently running."""
        with self._lock:
            return len(self._active) > 0

    def get_active_count(self) -> int:
        """Get the number of currently active tasks."""
        with self._lock:
            return len(self._active)

    def get_pending_count(self) -> int:
        """Get the number of pending tasks."""
        with self._lock:
            return sum(1 for t in self._pending if t.status == "pending")

    def clear(self) -> None:
        """Clear all queues."""
        with self._lock:
            self._pending.clear()
            self._active.clear()
            self._completed.clear()
            logger.debug("📋 TaskQueue: all queues cleared")
