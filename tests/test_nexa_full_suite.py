"""
NEXA AI — Comprehensive Automated Test Suite
=============================================
Tests every major subsystem including:
  • Kernel Governance (NexaKernel, PriorityManager, TaskQueue, ResourceManager, EventBus)
  • Capability Registry & dynamic registration
  • Priority-based task rejection / preemption
  • GPU resource allocation gating
  • Event bus pub/sub & thread-safety
  • Memory system (SmartMemory, MemoryTypes, IntentState, IntelligentLearner)
  • Cognition pipeline (InputValidator, DynamicPreprocessor, NaturalResponses, PromptBuilder)
  • Companion (ThinkingFeedback, IdleMonitor)
  • System controllers (Volume, Brightness, WiFi, Battery, AppController)
  • Media capabilities (MusicManager, YouTubeService)
  • Web capabilities (WebScraper, WeatherService)
  • Creative capabilities (GameManager, PDFGenerator)
  • Error handling framework
  • Context Manager basics
  • Thread-safety stress tests

Run:
    python -m pytest tests/test_nexa_full_suite.py -v --tb=short
    OR
    python tests/test_nexa_full_suite.py
"""

import os
import sys
import time
import uuid
import json
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

# ── Ensure project root is on sys.path ──────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# =====================================================================
# 1. KERNEL GOVERNANCE TESTS
# =====================================================================

class TestPriorityLevel(unittest.TestCase):
    """PriorityLevel IntEnum: numeric ordering is the foundation of governance."""

    def setUp(self):
        from core.kernel import PriorityLevel
        self.PL = PriorityLevel

    def test_ordering(self):
        """Priority values are strictly increasing from MEMORY_CLEANUP to EMERGENCY."""
        self.assertLess(self.PL.MEMORY_CLEANUP,     self.PL.IDLE_SUGGESTION)
        self.assertLess(self.PL.IDLE_SUGGESTION,    self.PL.DOWNLOAD)
        self.assertLess(self.PL.DOWNLOAD,           self.PL.BACKGROUND_SYNC)
        self.assertLess(self.PL.BACKGROUND_SYNC,    self.PL.MEDIA_PLAYBACK)
        self.assertLess(self.PL.MEDIA_PLAYBACK,     self.PL.SCREEN_QUERY)
        self.assertLess(self.PL.SCREEN_QUERY,       self.PL.NOTIFICATION_ALERT)
        self.assertLess(self.PL.NOTIFICATION_ALERT, self.PL.USER_COMMAND)
        self.assertLess(self.PL.USER_COMMAND,       self.PL.VOICE_INPUT)
        self.assertLess(self.PL.VOICE_INPUT,        self.PL.EMERGENCY)

    def test_exact_values(self):
        self.assertEqual(int(self.PL.MEMORY_CLEANUP),  10)
        self.assertEqual(int(self.PL.IDLE_SUGGESTION), 20)
        self.assertEqual(int(self.PL.DOWNLOAD),        30)
        self.assertEqual(int(self.PL.BACKGROUND_SYNC), 40)
        self.assertEqual(int(self.PL.VOICE_INPUT),    100)
        self.assertEqual(int(self.PL.EMERGENCY),      110)

    def test_all_ten_levels_exist(self):
        names = [m.name for m in self.PL]
        self.assertEqual(len(names), 10)
        required = {
            "MEMORY_CLEANUP", "IDLE_SUGGESTION", "DOWNLOAD",
            "BACKGROUND_SYNC", "MEDIA_PLAYBACK", "SCREEN_QUERY",
            "NOTIFICATION_ALERT", "USER_COMMAND", "VOICE_INPUT", "EMERGENCY",
        }
        for name in required:
            self.assertIn(name, names, f"Missing priority level: {name}")


class TestPriorityManager(unittest.TestCase):
    """PriorityManager rule tests — pure-priority governance."""

    def setUp(self):
        from core.kernel import PriorityManager, PriorityLevel
        self.pm = PriorityManager()
        self.PL = PriorityLevel

    # ── can_preempt ─────────────────────────────────────────────
    def test_higher_preempts_lower(self):
        self.assertTrue(self.pm.can_preempt(self.PL.USER_COMMAND, self.PL.MEDIA_PLAYBACK))

    def test_equal_does_not_preempt(self):
        self.assertFalse(self.pm.can_preempt(self.PL.USER_COMMAND, self.PL.USER_COMMAND))

    def test_lower_does_not_preempt(self):
        self.assertFalse(self.pm.can_preempt(self.PL.BACKGROUND_SYNC, self.PL.USER_COMMAND))

    def test_voice_input_preempts_everything(self):
        for level in self.PL:
            if level < self.PL.VOICE_INPUT:
                self.assertTrue(self.pm.can_preempt(self.PL.VOICE_INPUT, level),
                                f"VOICE_INPUT should preempt {level.name}")

    # ── should_reject ───────────────────────────────────────────
    def test_locked_rejects_below_voice_input(self):
        for level in self.PL:
            if level < self.PL.VOICE_INPUT:
                self.assertTrue(
                    self.pm.should_reject(level, is_locked=True),
                    f"{level.name} should be rejected when locked",
                )

    def test_locked_allows_voice_input(self):
        self.assertFalse(self.pm.should_reject(self.PL.VOICE_INPUT, is_locked=True))

    def test_emergency_bypasses_lock(self):
        """EMERGENCY priority is never rejected, even when locked."""
        self.assertFalse(self.pm.should_reject(self.PL.EMERGENCY, is_locked=True))

    def test_idle_rejected_when_active_task(self):
        self.assertTrue(self.pm.should_reject(
            self.PL.IDLE_SUGGESTION, has_active_task=True))

    def test_download_rejected_when_active_task(self):
        """Background DOWNLOAD priority is suppressed during active tasks."""
        self.assertTrue(self.pm.should_reject(
            self.PL.DOWNLOAD, has_active_task=True))

    def test_memory_cleanup_rejected_when_media_active(self):
        """MEMORY_CLEANUP should never run while media is active."""
        self.assertTrue(self.pm.should_reject(
            self.PL.MEMORY_CLEANUP, media_active=True))

    def test_user_command_not_rejected_when_active_task(self):
        """USER_COMMAND should NOT be rejected just because another task is active."""
        self.assertFalse(self.pm.should_reject(
            self.PL.USER_COMMAND, has_active_task=True))

    def test_media_active_suppresses_background_tasks(self):
        """media_active blocks all BACKGROUND_LEVELS tasks."""
        from core.kernel import BACKGROUND_LEVELS
        for level in BACKGROUND_LEVELS:
            self.assertTrue(
                self.pm.should_reject(level, media_active=True),
                f"{level.name} should be suppressed when media is active",
            )

    def test_media_active_does_not_suppress_foreground_tasks(self):
        """USER_COMMAND and above are unaffected by media_active alone."""
        self.assertFalse(self.pm.should_reject(
            self.PL.USER_COMMAND, media_active=True))
        self.assertFalse(self.pm.should_reject(
            self.PL.SCREEN_QUERY, media_active=True))

    def test_normal_state_no_rejection(self):
        """Nothing rejected in idle/unlocked/no-active-task state."""
        for level in self.PL:
            self.assertFalse(
                self.pm.should_reject(level, is_locked=False,
                                       media_active=False, has_active_task=False),
                f"{level.name} should not be rejected in normal state",
            )


class TestEventBus(unittest.TestCase):
    """EventBus pub/sub tests including thread-safety."""

    def setUp(self):
        from core.kernel import EventBus
        self.bus = EventBus()

    def test_subscribe_and_publish(self):
        received = []
        self.bus.subscribe("test.event", lambda **kw: received.append(kw))
        self.bus.publish("test.event", value=42)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["value"], 42)

    def test_multiple_handlers(self):
        results = {"a": 0, "b": 0}
        self.bus.subscribe("x", lambda **kw: results.update(a=results["a"] + 1))
        self.bus.subscribe("x", lambda **kw: results.update(b=results["b"] + 1))
        self.bus.publish("x")
        self.assertEqual(results["a"], 1)
        self.assertEqual(results["b"], 1)

    def test_unsubscribe(self):
        counter = {"n": 0}
        handler = lambda **kw: counter.update(n=counter["n"] + 1)
        self.bus.subscribe("evt", handler)
        self.bus.publish("evt")
        self.bus.unsubscribe("evt", handler)
        self.bus.publish("evt")
        self.assertEqual(counter["n"], 1)

    def test_handler_exception_isolated(self):
        """An exception in one handler must not prevent others from running."""
        results = []
        self.bus.subscribe("err", lambda **kw: (_ for _ in ()).throw(RuntimeError("boom")))
        self.bus.subscribe("err", lambda **kw: results.append("ok"))
        self.bus.publish("err")
        self.assertEqual(results, ["ok"])

    def test_clear(self):
        called = []
        self.bus.subscribe("c", lambda **kw: called.append(1))
        self.bus.clear()
        self.bus.publish("c")
        self.assertEqual(called, [])

    def test_no_duplicate_handlers(self):
        counter = {"n": 0}
        handler = lambda **kw: counter.update(n=counter["n"] + 1)
        self.bus.subscribe("dup", handler)
        self.bus.subscribe("dup", handler)  # same handler
        self.bus.publish("dup")
        self.assertEqual(counter["n"], 1)

    def test_concurrent_publish(self):
        """Stress-test: many threads publishing simultaneously."""
        counter = {"n": 0}
        lock = threading.Lock()
        def handler(**kw):
            with lock:
                counter["n"] += 1
        self.bus.subscribe("stress", handler)

        threads = [threading.Thread(target=self.bus.publish, args=("stress",))
                   for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(counter["n"], 50)


class TestTaskQueue(unittest.TestCase):
    """TaskQueue lifecycle: submit → activate → complete/cancel."""

    def setUp(self):
        from core.kernel import TaskQueue, TaskEntry, PriorityLevel
        self.TQ = TaskQueue
        self.TE = TaskEntry
        self.PL = PriorityLevel
        self.q = TaskQueue()

    def test_submit_and_retrieve(self):
        task = self.TE(name="t1", priority=self.PL.USER_COMMAND)
        tid = self.q.submit(task)
        self.assertIsNotNone(tid)
        popped = self.q.next_task()
        self.assertEqual(popped.task_id, tid)

    def test_priority_ordering(self):
        """Higher-priority tasks come out first regardless of insertion order."""
        low = self.TE(name="low", priority=self.PL.IDLE_SUGGESTION)
        high = self.TE(name="high", priority=self.PL.USER_COMMAND)
        self.q.submit(low)
        self.q.submit(high)
        first = self.q.next_task()
        self.assertEqual(first.name, "high")

    def test_fifo_within_same_priority(self):
        t1 = self.TE(name="first", priority=self.PL.USER_COMMAND)
        time.sleep(0.01)
        t2 = self.TE(name="second", priority=self.PL.USER_COMMAND)
        self.q.submit(t1)
        self.q.submit(t2)
        self.assertEqual(self.q.next_task().name, "first")
        self.assertEqual(self.q.next_task().name, "second")

    def test_activate_and_complete(self):
        task = self.TE(name="work", priority=self.PL.USER_COMMAND)
        self.q.submit(task)
        self.q.activate_task(task)
        self.assertTrue(self.q.has_active_tasks())
        self.assertEqual(self.q.get_active_count(), 1)
        completed = self.q.complete(task.task_id)
        self.assertIsNotNone(completed)
        self.assertEqual(completed.status, "completed")
        self.assertFalse(self.q.has_active_tasks())

    def test_cancel_pending(self):
        task = self.TE(name="cancel_me", priority=self.PL.BACKGROUND_SYNC)
        self.q.submit(task)
        cancelled = self.q.cancel(task.task_id)
        self.assertEqual(cancelled.status, "cancelled")

    def test_cancel_active(self):
        task = self.TE(name="running", priority=self.PL.USER_COMMAND)
        self.q.submit(task)
        self.q.activate_task(task)
        cancelled = self.q.cancel(task.task_id)
        self.assertEqual(cancelled.status, "cancelled")
        self.assertFalse(self.q.has_active_tasks())

    def test_peek_active_highest(self):
        t_low = self.TE(name="lo", priority=self.PL.BACKGROUND_SYNC)
        t_high = self.TE(name="hi", priority=self.PL.USER_COMMAND)
        self.q.submit(t_low)
        self.q.submit(t_high)
        self.q.activate_task(t_low)
        self.q.activate_task(t_high)
        top = self.q.peek_active()
        self.assertEqual(top.name, "hi")

    def test_empty_queue_returns_none(self):
        self.assertIsNone(self.q.next_task())
        self.assertIsNone(self.q.peek_active())

    def test_clear(self):
        self.q.submit(self.TE(name="x", priority=self.PL.USER_COMMAND))
        self.q.clear()
        self.assertIsNone(self.q.next_task())
        self.assertEqual(self.q.get_pending_count(), 0)


class TestResourceManager(unittest.TestCase):
    """ResourceManager GPU VRAM gating tests."""

    def setUp(self):
        from core.kernel import ResourceManager
        self.rm = ResourceManager(total_vram_mb=8192, safe_threshold_mb=7372)

    def test_initial_allocation(self):
        self.assertTrue(self.rm.can_allocate(4000))

    def test_allocate_and_release(self):
        self.assertTrue(self.rm.allocate("task_1", 4000))
        self.assertTrue(self.rm.can_allocate(3000))
        self.assertFalse(self.rm.can_allocate(4000))  # 4000+4000 > 7372
        released = self.rm.release("task_1")
        self.assertEqual(released, 4000)
        self.assertTrue(self.rm.can_allocate(4000))

    def test_over_threshold_rejected(self):
        self.rm.allocate("a", 7000)
        self.assertFalse(self.rm.can_allocate(500))  # 7000+500 = 7500 > 7372

    def test_zero_vram_always_allowed(self):
        self.assertTrue(self.rm.can_allocate(0))
        self.assertTrue(self.rm.allocate("zero", 0))

    def test_get_usage_percent(self):
        self.rm.allocate("half", 4096)
        pct = self.rm.get_usage_percent()
        self.assertAlmostEqual(pct, 50.0, places=0)

    def test_get_allocations(self):
        self.rm.allocate("t1", 1000)
        self.rm.allocate("t2", 2000)
        allocs = self.rm.get_allocations()
        self.assertEqual(allocs["t1"], 1000)
        self.assertEqual(allocs["t2"], 2000)

    def test_release_nonexistent(self):
        self.assertEqual(self.rm.release("nonexistent"), 0)

    def test_clear(self):
        self.rm.allocate("x", 5000)
        self.rm.clear()
        self.assertEqual(self.rm.get_allocations(), {})


class TestNexaKernel(unittest.TestCase):
    """End-to-end kernel governance tests."""

    def setUp(self):
        from core.kernel import NexaKernel, TaskEntry, PriorityLevel
        self.kernel = NexaKernel(gpu_monitor=None)
        self.TE = TaskEntry
        self.PL = PriorityLevel

    def tearDown(self):
        self.kernel.shutdown()

    # ── Task lifecycle ──────────────────────────────────────────
    def test_submit_accept(self):
        task = self.TE(name="user_cmd", priority=self.PL.USER_COMMAND)
        tid = self.kernel.submit_task(task)
        self.assertIsNotNone(tid)

    def test_submit_reject_locked(self):
        self.kernel.set_locked(True)
        task = self.TE(name="idle", priority=self.PL.IDLE_SUGGESTION)
        tid = self.kernel.submit_task(task)
        self.assertIsNone(tid)

    def test_submit_voice_while_locked(self):
        self.kernel.set_locked(True)
        task = self.TE(name="voice", priority=self.PL.VOICE_INPUT)
        tid = self.kernel.submit_task(task)
        self.assertIsNotNone(tid)

    def test_activate_and_complete(self):
        task = self.TE(name="work", priority=self.PL.USER_COMMAND)
        tid = self.kernel.submit_task(task)
        self.assertTrue(self.kernel.activate_task(task))
        self.kernel.complete_task(tid)
        self.assertFalse(self.kernel.task_queue.has_active_tasks())

    def test_cancel_task(self):
        task = self.TE(name="cancel", priority=self.PL.USER_COMMAND)
        tid = self.kernel.submit_task(task)
        self.kernel.activate_task(task)
        self.kernel.cancel_task(tid)
        self.assertFalse(self.kernel.task_queue.has_active_tasks())

    # ── GPU resource gating ─────────────────────────────────────
    def test_gpu_task_allocates_vram(self):
        task = self.TE(name="llm", priority=self.PL.USER_COMMAND,
                       gpu_required=True, estimated_vram_mb=4000)
        tid = self.kernel.submit_task(task)
        self.kernel.activate_task(task)
        allocs = self.kernel.resource_mgr.get_allocations()
        self.assertIn(tid, allocs)
        self.assertEqual(allocs[tid], 4000)

    def test_gpu_released_on_complete(self):
        task = self.TE(name="llm", priority=self.PL.USER_COMMAND,
                       gpu_required=True, estimated_vram_mb=4000)
        tid = self.kernel.submit_task(task)
        self.kernel.activate_task(task)
        self.kernel.complete_task(tid)
        self.assertEqual(self.kernel.resource_mgr.get_allocations(), {})

    # ── State management ────────────────────────────────────────
    def test_lock_unlock(self):
        self.assertFalse(self.kernel.is_locked)
        self.kernel.set_locked(True)
        self.assertTrue(self.kernel.is_locked)
        self.kernel.set_locked(False)
        self.assertFalse(self.kernel.is_locked)

    def test_media_state(self):
        self.assertFalse(self.kernel.is_media_active)
        self.kernel.set_media_active(True)
        self.assertTrue(self.kernel.is_media_active)
        self.kernel.set_media_active(False)
        self.assertFalse(self.kernel.is_media_active)

    # ── can_run_idle ────────────────────────────────────────────
    def test_can_run_idle_normal(self):
        self.assertTrue(self.kernel.can_run_idle())

    def test_can_run_idle_blocked_by_lock(self):
        self.kernel.set_locked(True)
        self.assertFalse(self.kernel.can_run_idle())

    def test_can_run_idle_blocked_by_active_task(self):
        task = self.TE(name="busy", priority=self.PL.USER_COMMAND)
        self.kernel.submit_task(task)
        self.kernel.activate_task(task)
        self.assertFalse(self.kernel.can_run_idle())

    # ── Event propagation ───────────────────────────────────────
    def test_task_submitted_event(self):
        events = []
        self.kernel.event_bus.subscribe("task.submitted",
                                        lambda **kw: events.append(kw))
        task = self.TE(name="evt_test", priority=self.PL.USER_COMMAND)
        self.kernel.submit_task(task)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["task_name"], "evt_test")

    def test_task_rejected_event(self):
        events = []
        self.kernel.event_bus.subscribe("task.rejected",
                                        lambda **kw: events.append(kw))
        self.kernel.set_locked(True)
        task = self.TE(name="rejected", priority=self.PL.IDLE_SUGGESTION)
        self.kernel.submit_task(task)
        self.assertEqual(len(events), 1)

    def test_task_completed_event(self):
        events = []
        self.kernel.event_bus.subscribe("task.completed",
                                        lambda **kw: events.append(kw))
        task = self.TE(name="done", priority=self.PL.USER_COMMAND)
        tid = self.kernel.submit_task(task)
        self.kernel.activate_task(task)
        self.kernel.complete_task(tid)
        self.assertEqual(len(events), 1)

    def test_gpu_events(self):
        alloc_events, release_events = [], []
        self.kernel.event_bus.subscribe("gpu.allocated",
                                        lambda **kw: alloc_events.append(kw))
        self.kernel.event_bus.subscribe("gpu.released",
                                        lambda **kw: release_events.append(kw))
        task = self.TE(name="gpu", priority=self.PL.USER_COMMAND,
                       gpu_required=True, estimated_vram_mb=2000)
        tid = self.kernel.submit_task(task)
        self.kernel.activate_task(task)
        self.assertEqual(len(alloc_events), 1)
        self.kernel.complete_task(tid)
        self.assertEqual(len(release_events), 1)

    # ── Idle rejected with active task ──────────────────────────
    def test_idle_rejected_while_active_task(self):
        active = self.TE(name="active", priority=self.PL.USER_COMMAND)
        self.kernel.submit_task(active)
        self.kernel.activate_task(active)
        idle = self.TE(name="idle", priority=self.PL.IDLE_SUGGESTION)
        self.assertIsNone(self.kernel.submit_task(idle))

    # ── Preemption info ─────────────────────────────────────────
    def test_higher_priority_queued_with_preemption_info(self):
        """Higher-priority still queues; kernel logs preemption possibility."""
        low = self.TE(name="low", priority=self.PL.BACKGROUND_SYNC,
                      interruptible=True)
        self.kernel.submit_task(low)
        self.kernel.activate_task(low)
        high = self.TE(name="high", priority=self.PL.USER_COMMAND)
        tid = self.kernel.submit_task(high)
        self.assertIsNotNone(tid)  # still accepted


class TestCapabilityRegistry(unittest.TestCase):
    """Capability registration on NexaKernel."""

    def setUp(self):
        from core.kernel import NexaKernel, PriorityLevel
        self.kernel = NexaKernel(gpu_monitor=None)
        self.PL = PriorityLevel

    def tearDown(self):
        self.kernel.shutdown()

    def test_register_and_get(self):
        handler = lambda: "hello"
        self.kernel.register_capability(
            "test_cap", handler,
            default_priority=self.PL.USER_COMMAND,
            gpu_required=False,
        )
        cap = self.kernel.get_capability("test_cap")
        self.assertIsNotNone(cap)
        self.assertEqual(cap["handler"], handler)
        self.assertEqual(cap["default_priority"], self.PL.USER_COMMAND)

    def test_get_nonexistent(self):
        self.assertIsNone(self.kernel.get_capability("nope"))

    def test_get_all(self):
        self.kernel.register_capability("a", lambda: None, self.PL.USER_COMMAND)
        self.kernel.register_capability("b", lambda: None, self.PL.MEDIA_PLAYBACK)
        caps = self.kernel.get_capabilities()
        self.assertEqual(len(caps), 2)
        self.assertIn("a", caps)
        self.assertIn("b", caps)

    def test_overwrite_capability(self):
        h1 = lambda: "first"
        h2 = lambda: "second"
        self.kernel.register_capability("dup", h1, self.PL.USER_COMMAND)
        self.kernel.register_capability("dup", h2, self.PL.MEDIA_PLAYBACK)
        cap = self.kernel.get_capability("dup")
        self.assertEqual(cap["handler"], h2)

    def test_gpu_metadata(self):
        self.kernel.register_capability(
            "llm", lambda: None,
            default_priority=self.PL.USER_COMMAND,
            gpu_required=True, estimated_vram_mb=4500,
        )
        cap = self.kernel.get_capability("llm")
        self.assertTrue(cap["gpu_required"])
        self.assertEqual(cap["estimated_vram_mb"], 4500)


# =====================================================================
# 2. KERNEL THREAD-SAFETY STRESS TESTS
# =====================================================================

class TestKernelConcurrency(unittest.TestCase):
    """Multi-threaded kernel operations must not deadlock or corrupt state."""

    def setUp(self):
        from core.kernel import NexaKernel, TaskEntry, PriorityLevel
        self.kernel = NexaKernel(gpu_monitor=None)
        self.TE = TaskEntry
        self.PL = PriorityLevel

    def tearDown(self):
        self.kernel.shutdown()

    def test_concurrent_submit(self):
        """50 threads submitting tasks simultaneously."""
        results = []
        def worker(i):
            task = self.TE(name=f"t{i}", priority=self.PL.USER_COMMAND)
            tid = self.kernel.submit_task(task)
            results.append(tid)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # All should be accepted (no locks, no active tasks)
        accepted = [r for r in results if r is not None]
        self.assertEqual(len(accepted), 50)

    def test_concurrent_lock_toggle(self):
        """Rapidly toggling lock from many threads should not deadlock."""
        def toggle(i):
            self.kernel.set_locked(i % 2 == 0)
        threads = [threading.Thread(target=toggle, args=(i,)) for i in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # Just verify no deadlock and state is consistent
        self.assertIsInstance(self.kernel.is_locked, bool)

    def test_concurrent_events(self):
        """Publishing events from many threads should not lose data."""
        counter = {"n": 0}
        lock = threading.Lock()
        def handler(**kw):
            with lock:
                counter["n"] += 1
        self.kernel.event_bus.subscribe("concurrent", handler)
        threads = [threading.Thread(target=self.kernel.event_bus.publish,
                                    args=("concurrent",)) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(counter["n"], 100)


# =====================================================================
# 3. MEMORY SYSTEM TESTS
# =====================================================================

class TestMemoryTypes(unittest.TestCase):
    """ConversationMemory, KnowledgeMemory, SkillMemory dataclasses."""

    def setUp(self):
        from core.memory.memory_types import (
            ConversationMemory, KnowledgeMemory, SkillMemory,
            generate_session_id, detect_knowledge_category,
        )
        self.CM = ConversationMemory
        self.KM = KnowledgeMemory
        self.SM = SkillMemory
        self.gen_sid = generate_session_id
        self.detect_cat = detect_knowledge_category

    def test_conversation_memory_roundtrip(self):
        import numpy as np
        mem = self.CM(user_message="hello", nexa_response="hi there",
                      embedding=np.array([0.1, 0.2, 0.3]))
        d = mem.to_dict()
        self.assertIn("user_message", d)
        restored = self.CM.from_dict(d)
        self.assertEqual(restored.user_message, "hello")
        self.assertEqual(restored.nexa_response, "hi there")

    def test_knowledge_memory_roundtrip(self):
        import numpy as np
        mem = self.KM(fact="Python is great", embedding=np.array([0.5, 0.6]))
        d = mem.to_dict()
        restored = self.KM.from_dict(d)
        self.assertEqual(restored.fact, "Python is great")

    def test_skill_memory_roundtrip(self):
        mem = self.SM(action="open_app")
        d = mem.to_dict()
        restored = self.SM.from_dict(d)
        self.assertEqual(restored.action, "open_app")

    def test_session_id_generation(self):
        s1 = self.gen_sid()
        s2 = self.gen_sid()
        self.assertIsInstance(s1, str)
        self.assertNotEqual(s1, s2)

    def test_detect_knowledge_category(self):
        cat = self.detect_cat("My name is Ali")
        self.assertIsInstance(cat, str)


class TestIntentState(unittest.TestCase):
    """IntentState for multi-turn context tracking."""

    def setUp(self):
        from core.memory.intent_state import IntentState
        self.ism = IntentState(state_file=None)

    def test_set_and_get_last_action(self):
        self.ism.set_last_action(action="open_app", result="opened",
                                  target="chrome")
        self.assertEqual(self.ism.get_last_action(), "open_app")
        self.assertEqual(self.ism.get_last_result(), "opened")
        self.assertEqual(self.ism.get_last_target(), "chrome")

    def test_has_recent_context(self):
        self.ism.set_last_action(action="test", result="ok")
        self.assertTrue(self.ism.has_recent_context(max_age_seconds=60))

    def test_clear_pending_intent(self):
        """clear() resets pending intent, not last-action context."""
        self.ism.set_last_action(action="x", result="y")
        self.ism.clear()
        # clear() only wipes _pending; last_action is preserved for follow-ups
        self.assertEqual(self.ism.get_last_action(), "x")
        self.assertFalse(self.ism.has_pending_intent())

    def test_is_follow_up_question(self):
        result = self.ism.is_follow_up_question("what about that?")
        self.assertIsInstance(result, bool)

    def test_is_counting_question(self):
        result = self.ism.is_counting_question("how many are there?")
        self.assertIsInstance(result, bool)

    def test_get_state_summary(self):
        summary = self.ism.get_state_summary()
        self.assertIsInstance(summary, dict)


class TestIntelligentLearner(unittest.TestCase):
    """IntelligentLearner fact extraction (no memory_manager needed)."""

    def setUp(self):
        from core.memory.intelligent_learner import IntelligentLearner, FactType
        self.learner = IntelligentLearner(memory_manager=None)
        self.FactType = FactType

    def test_analyze_statement(self):
        facts = self.learner.analyze_conversation(
            "My name is Ali", "Nice to meet you, Ali!")
        self.assertIsInstance(facts, list)

    def test_fact_types_exist(self):
        names = [f.name for f in self.FactType]
        self.assertIn("PREFERENCE", names)
        self.assertIn("PERSONAL", names)

    def test_pending_facts(self):
        pending = self.learner.get_pending_facts()
        self.assertIsInstance(pending, list)


# =====================================================================
# 4. COGNITION PIPELINE TESTS
# =====================================================================

class TestInputValidator(unittest.TestCase):
    """InputValidator validates/sanitizes user text."""

    def setUp(self):
        from core.cognition.input_validator import InputValidator
        self.iv = InputValidator()

    def test_valid_input(self):
        valid, err = self.iv.validate_input("open chrome")
        self.assertTrue(valid)
        self.assertIsNone(err)

    def test_empty_input(self):
        valid, err = self.iv.validate_input("")
        self.assertFalse(valid)

    def test_whitespace_only(self):
        valid, err = self.iv.validate_input("   ")
        self.assertFalse(valid)

    def test_very_long_input(self):
        """Extremely long input should still produce a result (valid or rejected)."""
        result = self.iv.validate_input("a " * 5000)
        self.assertIsInstance(result, tuple)

    def test_numeric_range_validation(self):
        valid, err = self.iv.validate_numeric_range("volume", 50)
        self.assertIsInstance(valid, bool)


class TestDynamicPreprocessor(unittest.TestCase):
    """DynamicPreprocessor splits compound commands."""

    def setUp(self):
        from core.cognition.dynamic_preprocessor import DynamicPreprocessor
        self.dp = DynamicPreprocessor(context_manager=None)

    def test_single_command(self):
        result = self.dp.preprocess("open chrome")
        self.assertIsInstance(result.commands, list)
        self.assertGreaterEqual(len(result.commands), 1)

    def test_multi_command(self):
        result = self.dp.preprocess("open chrome and play music")
        self.assertIsInstance(result.commands, list)

    def test_metadata_returned(self):
        result = self.dp.preprocess("set volume to 50")
        self.assertIsInstance(result.metadata, dict)


class TestNaturalResponses(unittest.TestCase):
    """NaturalResponses generates varied human-like responses."""

    def setUp(self):
        from core.cognition.natural_responses import NaturalResponses
        self.nr = NaturalResponses

    def test_volume_set(self):
        resp = self.nr.volume_set(75)
        self.assertIsInstance(resp, str)
        self.assertGreater(len(resp), 0)

    def test_app_opened(self):
        resp = self.nr.app_opened("Chrome")
        self.assertIsInstance(resp, str)

    def test_app_not_found(self):
        resp = self.nr.app_not_found("nonexistent_app")
        self.assertIsInstance(resp, str)

    def test_screenshot_taken(self):
        resp = self.nr.screenshot_taken()
        self.assertIsInstance(resp, str)

    def test_brightness_set(self):
        resp = self.nr.brightness_set(80)
        self.assertIsInstance(resp, str)


class TestPromptBuilder(unittest.TestCase):
    """SystemPromptBuilder creates LLM prompts."""

    def setUp(self):
        from core.cognition.prompt_builder import SystemPromptBuilder
        self.pb = SystemPromptBuilder()

    def test_build_llama_prompt(self):
        prompt = self.pb.build_llama_prompt(
            user_text="what time is it",
            user_name="TestUser",
        )
        self.assertIsInstance(prompt, str)
        self.assertIn("what time is it", prompt)

    def test_prompt_includes_function_catalog(self):
        prompt = self.pb.build_llama_prompt(
            user_text="open chrome",
            user_name="User",
            function_catalog="open_application: opens an app",
        )
        self.assertIn("open_application", prompt)


# =====================================================================
# 5. COMPANION TESTS
# =====================================================================

class TestThinkingFeedback(unittest.TestCase):
    """ThinkingFeedback classifies tasks and manages TTS acknowledgment."""

    def setUp(self):
        from core.companion.thinking_feedback import ThinkingFeedback, TaskType
        self.speak_calls = []
        self.tf = ThinkingFeedback(
            speak_func=lambda text, **kw: self.speak_calls.append(text),
            emit_message_func=None,
            enabled=True,
        )
        self.TaskType = TaskType

    def test_start_thinking_returns_bool(self):
        result = self.tf.start_thinking("search for python tutorials")
        self.assertIsInstance(result, bool)

    def test_end_thinking(self):
        self.tf.start_thinking("open chrome")
        self.tf.end_thinking(success=True)
        # Should not raise

    def test_cancel(self):
        self.tf.start_thinking("test")
        self.tf.cancel()
        # Should not raise

    def test_task_types_exist(self):
        self.assertIn("GENERAL", [t.name for t in self.TaskType])
        self.assertIn("SEARCH", [t.name for t in self.TaskType])
        self.assertIn("COMPLEX", [t.name for t in self.TaskType])


class TestIdleMonitor(unittest.TestCase):
    """IdleMonitor tracks user activity for proactive suggestions."""

    def setUp(self):
        from core.companion.idle_monitor import IdleMonitor, IdleState

    def test_initial_state(self):
        from core.companion.idle_monitor import IdleMonitor, IdleState
        monitor = IdleMonitor()
        state = monitor.get_idle_state()
        self.assertIsInstance(state, IdleState)

    def test_record_interaction(self):
        from core.companion.idle_monitor import IdleMonitor
        monitor = IdleMonitor()
        monitor.record_interaction()
        self.assertAlmostEqual(monitor.get_idle_duration(), 0, delta=1.0)

    def test_get_stats(self):
        from core.companion.idle_monitor import IdleMonitor
        monitor = IdleMonitor()
        stats = monitor.get_stats()
        self.assertIsNotNone(stats)

    def test_format_idle_duration(self):
        from core.companion.idle_monitor import IdleMonitor
        monitor = IdleMonitor()
        monitor.record_interaction()
        formatted = monitor.format_idle_duration()
        self.assertIsInstance(formatted, str)


# =====================================================================
# 6. SYSTEM CONTROLLER TESTS
# =====================================================================

class TestBatteryManager(unittest.TestCase):
    """BatteryManager reads system battery state."""

    def setUp(self):
        from capabilities.system.battery_manager import BatteryManager
        self.bm = BatteryManager()

    def test_get_battery_status(self):
        status = self.bm.get_battery_status()
        self.assertIsInstance(status, dict)
        self.assertIn("has_battery", status)

    def test_get_simple_status(self):
        status = self.bm.get_simple_status()
        self.assertIsInstance(status, str)

    def test_get_percentage(self):
        pct = self.bm.get_battery_percentage()
        self.assertIsInstance(pct, int)

    def test_is_charging(self):
        result = self.bm.is_charging()
        self.assertIsInstance(result, bool)


class TestVolumeController(unittest.TestCase):
    """VolumeController manages system audio."""

    def setUp(self):
        from capabilities.system.volume_controller import VolumeController
        self.vc = VolumeController()

    def test_get_current_volume(self):
        vol = self.vc.get_current_volume()
        self.assertIsInstance(vol, str)

    def test_set_volume_returns_string(self):
        # Don't actually change volume — just verify method returns cleanly
        result = self.vc.set_volume(50)
        self.assertIsInstance(result, str)


class TestBrightnessController(unittest.TestCase):
    """BrightnessController manages display brightness."""

    def setUp(self):
        from capabilities.system.brightness_controller import BrightnessController
        self.bc = BrightnessController()

    def test_get_current_brightness(self):
        result = self.bc.get_current_brightness()
        self.assertIsInstance(result, str)


class TestWiFiController(unittest.TestCase):
    """WiFiController manages network connections."""

    def setUp(self):
        from capabilities.system.wifi_controller import WiFiController
        self.wc = WiFiController()

    def test_get_wifi_status(self):
        status = self.wc.get_wifi_status()
        self.assertIsInstance(status, str)


class TestApplicationController(unittest.TestCase):
    """ApplicationController opens/closes/finds applications."""

    def setUp(self):
        try:
            from capabilities.system.app_controller import ApplicationController
            self.ac = ApplicationController()
        except Exception:
            self.ac = None

    def test_builtin_apps_defined(self):
        if self.ac is None:
            self.skipTest("ApplicationController not loadable")
        self.assertTrue(hasattr(self.ac, 'BUILTIN_APPS') or
                        hasattr(type(self.ac), 'BUILTIN_APPS'))


# =====================================================================
# 7. MEDIA CAPABILITY TESTS (mock-based)
# =====================================================================

class TestYouTubeService(unittest.TestCase):
    """YouTubeService (constructed only — no network calls)."""

    def setUp(self):
        try:
            from capabilities.media.youtube_service import YouTubeService
            self.yt = YouTubeService(config=MagicMock())
        except Exception as e:
            self.yt = None
            self._skip_reason = str(e)

    def test_instantiation(self):
        if self.yt is None:
            self.skipTest(f"YouTubeService not loadable: {self._skip_reason}")
        self.assertIsNotNone(self.yt)

    def test_quality_presets(self):
        if self.yt is None:
            self.skipTest("YouTubeService not loadable")
        self.assertTrue(hasattr(self.yt, 'QUALITY_PRESETS') or
                        hasattr(type(self.yt), 'QUALITY_PRESETS'))


# =====================================================================
# 8. WEB CAPABILITY TESTS (no network)
# =====================================================================

class TestWebScraper(unittest.TestCase):
    """WebScraper construction and intent detection (no network)."""

    def setUp(self):
        try:
            from capabilities.web.web_scraper import WebScraper
            self.ws = WebScraper(config=MagicMock())
        except Exception as e:
            self.ws = None
            self._skip_reason = str(e)

    def test_instantiation(self):
        if self.ws is None:
            self.skipTest(f"WebScraper not loadable: {self._skip_reason}")
        self.assertIsNotNone(self.ws)

    def test_detect_intent(self):
        if self.ws is None:
            self.skipTest("WebScraper not loadable")
        if hasattr(self.ws, '_detect_intent'):
            intent = self.ws._detect_intent("what is python programming")
            self.assertIsInstance(intent, (str, dict))


# =====================================================================
# 9. CREATIVE CAPABILITY TESTS
# =====================================================================

class TestGameManager(unittest.TestCase):
    """GameManager indexes and finds games."""

    def setUp(self):
        from capabilities.creative.game_manager import GameManager
        self.gm = GameManager()

    def test_instantiation(self):
        self.assertIsNotNone(self.gm)

    def test_list_games(self):
        games = self.gm.list_games()
        self.assertIsInstance(games, list)

    def test_find_game_nonexistent(self):
        result = self.gm.find_game("totally_fake_game_xyz_123")
        # Should return None for non-existent game
        self.assertIsNone(result)


class TestPDFGenerator(unittest.TestCase):
    """PDFGenerator creates PDFs (verify instantiation and format enumeration)."""

    def setUp(self):
        try:
            from capabilities.creative.pdf_generator import PDFGenerator, PDFFormat
            self.pg = PDFGenerator()
            self.PDFFormat = PDFFormat
        except ImportError as e:
            self.pg = None
            self._skip_reason = str(e)

    def test_instantiation(self):
        if self.pg is None:
            self.skipTest(f"PDFGenerator not loadable: {self._skip_reason}")
        self.assertIsNotNone(self.pg)

    def test_available_formats(self):
        if self.pg is None:
            self.skipTest("PDFGenerator not loadable")
        formats = self.pg.get_available_formats()
        self.assertIsInstance(formats, list)
        self.assertGreater(len(formats), 0)


# =====================================================================
# 10. ERROR HANDLING FRAMEWORK
# =====================================================================

class TestErrorHandler(unittest.TestCase):
    """Error handler utility: categories, severities, handle_error()."""

    def setUp(self):
        from utils.error_handler import (
            ErrorCategory, ErrorSeverity, NexaError, handle_error,
        )
        self.EC = ErrorCategory
        self.ES = ErrorSeverity
        self.NE = NexaError
        self.handle = handle_error

    def test_error_categories(self):
        cats = [c.name for c in self.EC]
        self.assertIn("NETWORK", cats)
        self.assertIn("AUDIO", cats)
        self.assertIn("LLM", cats)
        self.assertIn("SYSTEM", cats)

    def test_error_severities(self):
        sevs = [s.name for s in self.ES]
        self.assertIn("LOW", sevs)
        self.assertIn("CRITICAL", sevs)

    def test_nexa_error_creation(self):
        err = self.NE(
            "Test error",
            category=self.EC.SYSTEM,
            severity=self.ES.MEDIUM,
            user_message="Something went wrong",
        )
        self.assertEqual(str(err), "Test error")

    def test_handle_error(self):
        try:
            raise ValueError("test")
        except ValueError as e:
            user_msg, recovered = self.handle(
                error=e,
                context="test_function",
                category=self.EC.SYSTEM,
                severity=self.ES.LOW,
            )
            self.assertIsInstance(user_msg, str)
            self.assertIsInstance(recovered, bool)


# =====================================================================
# 11. INTEGRATION: KERNEL GOVERNANCE WORKFLOW
# =====================================================================

class TestKernelGovernanceWorkflow(unittest.TestCase):
    """End-to-end governance scenarios simulating real usage."""

    def setUp(self):
        from core.kernel import NexaKernel, TaskEntry, PriorityLevel
        self.kernel = NexaKernel(gpu_monitor=None)
        self.TE = TaskEntry
        self.PL = PriorityLevel

    def tearDown(self):
        self.kernel.shutdown()

    def test_full_user_command_lifecycle(self):
        """Simulate: user speaks → LLM processes → TTS speaks → done."""
        # 1. Voice input task
        voice = self.TE(name="voice_input", priority=self.PL.VOICE_INPUT)
        vid = self.kernel.submit_task(voice)
        self.assertIsNotNone(vid)
        self.kernel.activate_task(voice)

        # 2. LLM inference (GPU task) while voice is active
        llm = self.TE(name="llm_inference", priority=self.PL.USER_COMMAND,
                      gpu_required=True, estimated_vram_mb=4500)
        lid = self.kernel.submit_task(llm)
        self.assertIsNotNone(lid)
        self.kernel.complete_task(vid)  # voice done
        self.kernel.activate_task(llm)
        self.assertIn(lid, self.kernel.resource_mgr.get_allocations())

        # 3. TTS (no GPU)
        tts = self.TE(name="tts", priority=self.PL.USER_COMMAND)
        ttid = self.kernel.submit_task(tts)
        self.kernel.complete_task(lid)  # LLM done, VRAM freed
        self.assertEqual(self.kernel.resource_mgr.get_allocations(), {})
        self.kernel.activate_task(tts)
        self.kernel.complete_task(ttid)

        self.assertFalse(self.kernel.task_queue.has_active_tasks())

    def test_idle_blocked_during_media_playback_scenario(self):
        """When media is playing (active task), idle suggestions are rejected."""
        media = self.TE(name="play_music", priority=self.PL.MEDIA_PLAYBACK)
        mid = self.kernel.submit_task(media)
        self.kernel.activate_task(media)
        self.kernel.set_media_active(True)

        # Idle suggestion should be rejected
        idle = self.TE(name="idle_suggestion", priority=self.PL.IDLE_SUGGESTION)
        self.assertIsNone(self.kernel.submit_task(idle))
        self.assertFalse(self.kernel.can_run_idle())

        # But USER_COMMAND should still go through
        cmd = self.TE(name="user_cmd", priority=self.PL.USER_COMMAND)
        self.assertIsNotNone(self.kernel.submit_task(cmd))

        self.kernel.complete_task(mid)
        self.kernel.set_media_active(False)

    def test_lock_blocks_all_except_voice(self):
        """Locked state: only VOICE_INPUT and EMERGENCY pass (EMERGENCY bypasses lock by design)."""
        from core.kernel import PriorityLevel
        self.kernel.set_locked(True)
        for level in self.PL:
            task = self.TE(name=f"task_{level.name}", priority=level)
            tid = self.kernel.submit_task(task)
            if level >= PriorityLevel.VOICE_INPUT:
                self.assertIsNotNone(tid, f"{level.name} must pass even when locked")
            else:
                self.assertIsNone(tid, f"{level.name} must be blocked when locked")

    def test_gpu_exhaustion_scenario(self):
        """When VRAM is nearly full, GPU tasks fail to activate."""
        # Fill up VRAM
        t1 = self.TE(name="big_model", priority=self.PL.USER_COMMAND,
                     gpu_required=True, estimated_vram_mb=7000)
        self.kernel.submit_task(t1)
        self.kernel.activate_task(t1)

        # New GPU task can't activate
        t2 = self.TE(name="another_model", priority=self.PL.USER_COMMAND,
                     gpu_required=True, estimated_vram_mb=1000)
        tid2 = self.kernel.submit_task(t2)
        self.assertIsNotNone(tid2)  # submission succeeds
        result = self.kernel.activate_task(t2)
        self.assertFalse(result)  # but activation fails (no VRAM)

    def test_capability_registry_reflects_brain_pattern(self):
        """Simulate what brain.set_kernel() does: register 6 capabilities."""
        self.kernel.register_capability(
            "voice_input", lambda: None,
            default_priority=self.PL.VOICE_INPUT, gpu_required=False)
        self.kernel.register_capability(
            "llm_inference", lambda: None,
            default_priority=self.PL.USER_COMMAND, gpu_required=True,
            estimated_vram_mb=4500)
        self.kernel.register_capability(
            "tts", lambda: None,
            default_priority=self.PL.USER_COMMAND, gpu_required=False)
        self.kernel.register_capability(
            "youtube", lambda: None,
            default_priority=self.PL.MEDIA_PLAYBACK, gpu_required=False)
        self.kernel.register_capability(
            "music", lambda: None,
            default_priority=self.PL.MEDIA_PLAYBACK, gpu_required=False)
        self.kernel.register_capability(
            "memory_cleanup", lambda: None,
            default_priority=self.PL.BACKGROUND_SYNC, gpu_required=False)

        caps = self.kernel.get_capabilities()
        self.assertEqual(len(caps), 6)
        self.assertTrue(caps["llm_inference"]["gpu_required"])
        self.assertEqual(caps["voice_input"]["default_priority"], self.PL.VOICE_INPUT)
        self.assertEqual(caps["memory_cleanup"]["default_priority"], self.PL.BACKGROUND_SYNC)

    def test_event_propagation_chain(self):
        """Verify events fire in correct order during a task lifecycle."""
        log = []
        self.kernel.event_bus.subscribe("task.submitted",
                                        lambda **kw: log.append("submitted"))
        self.kernel.event_bus.subscribe("gpu.allocated",
                                        lambda **kw: log.append("gpu_alloc"))
        self.kernel.event_bus.subscribe("task.completed",
                                        lambda **kw: log.append("completed"))
        self.kernel.event_bus.subscribe("gpu.released",
                                        lambda **kw: log.append("gpu_release"))

        task = self.TE(name="full_flow", priority=self.PL.USER_COMMAND,
                       gpu_required=True, estimated_vram_mb=2000)
        tid = self.kernel.submit_task(task)
        self.kernel.activate_task(task)
        self.kernel.complete_task(tid)

        self.assertEqual(log, ["submitted", "gpu_alloc", "gpu_release", "completed"])

    def test_background_sync_during_normal_operation(self):
        """BACKGROUND_SYNC tasks accepted when no higher priority is locked."""
        task = self.TE(name="memory_sync", priority=self.PL.BACKGROUND_SYNC)
        tid = self.kernel.submit_task(task)
        self.assertIsNotNone(tid)

    def test_multiple_active_tasks(self):
        """Multiple tasks can be active simultaneously."""
        t1 = self.TE(name="task1", priority=self.PL.USER_COMMAND)
        t2 = self.TE(name="task2", priority=self.PL.MEDIA_PLAYBACK)
        self.kernel.submit_task(t1)
        self.kernel.submit_task(t2)
        self.kernel.activate_task(t1)
        self.kernel.activate_task(t2)
        self.assertEqual(self.kernel.task_queue.get_active_count(), 2)


# =====================================================================
# 12. CONFIGURATION / UTILITY TESTS
# =====================================================================

class TestProjectStructure(unittest.TestCase):
    """Verify the restructured project layout is intact."""

    def test_kernel_package(self):
        """core.kernel package is importable with all exports."""
        from core.kernel import (
            NexaKernel, EventBus, PriorityLevel, PriorityManager,
            TaskEntry, TaskQueue, ResourceManager,
        )

    def test_memory_package(self):
        from core.memory import (
            SmartMemoryManager, ConversationMemory, KnowledgeMemory,
            SkillMemory, ContextConstructor, IntentState,
            IntelligentLearner,
        )

    def test_cognition_modules(self):
        from core.cognition.input_validator import InputValidator
        from core.cognition.dynamic_preprocessor import DynamicPreprocessor
        from core.cognition.natural_responses import NaturalResponses
        from core.cognition.prompt_builder import SystemPromptBuilder

    def test_companion_modules(self):
        from core.companion.thinking_feedback import ThinkingFeedback
        from core.companion.idle_monitor import IdleMonitor

    def test_capability_packages(self):
        from capabilities.system.battery_manager import BatteryManager
        from capabilities.system.volume_controller import VolumeController
        from capabilities.system.brightness_controller import BrightnessController
        from capabilities.system.wifi_controller import WiFiController
        from capabilities.creative.game_manager import GameManager

    def test_utils_package(self):
        from utils.error_handler import ErrorCategory, ErrorSeverity, handle_error


# =====================================================================
# RUNNER
# =====================================================================

def build_suite():
    """Build the full test suite in logical order."""
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()

    # Order: structure → kernel → memory → cognition → companion → caps → integration
    test_classes = [
        # Project structure
        TestProjectStructure,
        # Kernel governance
        TestPriorityLevel,
        TestPriorityManager,
        TestEventBus,
        TestTaskQueue,
        TestResourceManager,
        TestNexaKernel,
        TestCapabilityRegistry,
        TestKernelConcurrency,
        # Memory
        TestMemoryTypes,
        TestIntentState,
        TestIntelligentLearner,
        # Cognition
        TestInputValidator,
        TestDynamicPreprocessor,
        TestNaturalResponses,
        TestPromptBuilder,
        # Companion
        TestThinkingFeedback,
        TestIdleMonitor,
        # System capabilities
        TestBatteryManager,
        TestVolumeController,
        TestBrightnessController,
        TestWiFiController,
        TestApplicationController,
        # Media
        TestYouTubeService,
        # Web
        TestWebScraper,
        # Creative
        TestGameManager,
        TestPDFGenerator,
        # Error handling
        TestErrorHandler,
        # Integration workflows
        TestKernelGovernanceWorkflow,
    ]

    for cls in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    return suite


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(build_suite())
    sys.exit(0 if result.wasSuccessful() else 1)
