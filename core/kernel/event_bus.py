"""
Event Bus
=========
Lightweight publish/subscribe system for decoupled inter-module communication.

All modules communicate through the kernel's event bus instead of direct calls.

Standard event types:
  task.submitted   — a new task was submitted to the kernel
  task.completed   — a task finished execution
  task.rejected    — a task was rejected (priority / resources)
  state.locked     — NEXA was locked
  state.unlocked   — NEXA was unlocked
  media.started    — media playback started (NVP, music)
  media.stopped    — media playback stopped
  gpu.allocated    — GPU VRAM allocated for a task
  gpu.released     — GPU VRAM released
"""

import logging
import threading
from collections import defaultdict
from typing import Callable, Any, Dict

logger = logging.getLogger(__name__)


class EventBus:
    """
    Thread-safe publish/subscribe event system.

    Usage:
        bus = EventBus()
        bus.subscribe("media.started", my_handler)
        bus.publish("media.started", source="nvp")
    """

    def __init__(self):
        self._handlers: Dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """
        Register a handler for an event type.

        Args:
            event_type: Event name (e.g., "media.started").
            handler: Callable that accepts keyword arguments.
        """
        with self._lock:
            if handler not in self._handlers[event_type]:
                self._handlers[event_type].append(handler)
                logger.debug(f"📡 EventBus: subscribed to '{event_type}'")

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """
        Remove a handler for an event type.

        Args:
            event_type: Event name.
            handler: Previously registered handler.
        """
        with self._lock:
            try:
                self._handlers[event_type].remove(handler)
                logger.debug(f"📡 EventBus: unsubscribed from '{event_type}'")
            except ValueError:
                pass  # handler was not registered

    def publish(self, event_type: str, **data: Any) -> None:
        """
        Publish an event to all subscribed handlers.

        Handlers are called synchronously in subscription order.
        Exceptions in individual handlers are logged but do not
        prevent other handlers from running.

        Args:
            event_type: Event name.
            **data: Keyword arguments passed to each handler.
        """
        with self._lock:
            handlers = list(self._handlers.get(event_type, []))

        if handlers:
            logger.debug(f"📡 EventBus: publishing '{event_type}' to {len(handlers)} handler(s)")

        for handler in handlers:
            try:
                handler(**data)
            except Exception as e:
                logger.error(
                    f"📡 EventBus: handler error for '{event_type}': {e}",
                    exc_info=True,
                )

    def clear(self) -> None:
        """Remove all subscriptions."""
        with self._lock:
            self._handlers.clear()
            logger.debug("📡 EventBus: all subscriptions cleared")
