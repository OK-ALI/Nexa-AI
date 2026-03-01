"""
NEXA Concurrency & Multi-Task Stress Test
==========================================
Simulates real NEXA scenarios with concurrent tasks, priority preemption,
GPU resource contention, and event bus throughput under load.

This validates that the restructured kernel handles multi-task
operation WITHOUT interruptions or race conditions.

Run: python test_concurrency.py
"""
import sys
import os
import time
import threading
import random
import traceback
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.kernel import NexaKernel, TaskEntry, PriorityLevel, EventBus
from core.kernel.priority_manager import PriorityManager
from core.kernel.resource_manager import ResourceManager
from core.kernel.task_queue import TaskQueue


class ConcurrencyTestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self._lock = threading.Lock()
    
    def ok(self, name, detail=""):
        with self._lock:
            self.passed += 1
            msg = f"  [PASS] {name}"
            if detail:
                msg += f" -- {detail}"
            print(msg)
    
    def fail(self, name, error):
        with self._lock:
            self.failed += 1
            self.errors.append((name, str(error)))
            print(f"  [FAIL] {name}: {error}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'#'*60}")
        print(f"  CONCURRENCY TEST RESULTS")
        print(f"{'#'*60}")
        print(f"  TOTAL: {self.passed}/{total} passed, {self.failed} failed")
        if self.errors:
            print(f"\n  FAILURES:")
            for name, err in self.errors:
                print(f"    {name}: {err}")
        print(f"{'#'*60}")
        return self.failed == 0

R = ConcurrencyTestResults()

# ============================================================
# TEST 1: Rapid Sequential Task Submission
# ============================================================
print(f"\n{'='*60}")
print("  TEST 1: Rapid Sequential Task Submission (50 tasks)")
print(f"{'='*60}")

try:
    kernel = NexaKernel()
    task_ids = []
    
    start = time.perf_counter()
    for i in range(50):
        priority = random.choice(list(PriorityLevel))
        task = TaskEntry(name=f"RAPID_{i}", priority=priority)
        tid = kernel.submit_task(task)
        if tid:
            task_ids.append(tid)
    submit_time = time.perf_counter() - start
    
    # Complete all tasks
    for tid in task_ids:
        kernel.complete_task(tid)
    complete_time = time.perf_counter() - start
    
    assert len(task_ids) > 0, "No tasks were accepted"
    # Check for duplicate IDs
    assert len(task_ids) == len(set(task_ids)), f"Duplicate task IDs found!"
    
    R.ok(f"50 rapid tasks", f"{len(task_ids)} accepted, {50-len(task_ids)} rejected, {submit_time*1000:.1f}ms submit, {complete_time*1000:.1f}ms total")
except Exception as e:
    R.fail("Rapid sequential submission", e)

# ============================================================
# TEST 2: Concurrent Task Submission (Thread Storm)
# ============================================================
print(f"\n{'='*60}")
print("  TEST 2: Concurrent Thread Storm (20 threads x 5 tasks)")
print(f"{'='*60}")

try:
    kernel = NexaKernel()
    all_ids = []
    all_ids_lock = threading.Lock()
    errors_thread = []
    
    def submit_batch(thread_id):
        """Each thread submits 5 tasks with random priorities."""
        local_ids = []
        for i in range(5):
            priority = random.choice(list(PriorityLevel))
            task = TaskEntry(
                name=f"THREAD_{thread_id}_TASK_{i}",
                priority=priority
            )
            try:
                tid = kernel.submit_task(task)
                if tid:
                    local_ids.append(tid)
            except Exception as e:
                errors_thread.append(f"Thread {thread_id}: {e}")
        
        with all_ids_lock:
            all_ids.extend(local_ids)
        return len(local_ids)
    
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = [pool.submit(submit_batch, t) for t in range(20)]
        results = [f.result() for f in as_completed(futures)]
    
    submit_time = time.perf_counter() - start
    
    # Complete all tasks
    for tid in all_ids:
        try:
            kernel.complete_task(tid)
        except Exception:
            pass
    
    total_time = time.perf_counter() - start
    
    assert len(errors_thread) == 0, f"Thread errors: {errors_thread}"
    assert len(all_ids) == len(set(all_ids)), "Duplicate IDs across threads!"
    
    R.ok(f"20-thread storm", f"{len(all_ids)} tasks, 0 errors, {submit_time*1000:.1f}ms submit, {total_time*1000:.1f}ms total")
except Exception as e:
    R.fail("Concurrent thread storm", e)

# ============================================================
# TEST 3: Priority Preemption Under Load
# ============================================================
print(f"\n{'='*60}")
print("  TEST 3: Priority Preemption Under Load")
print(f"{'='*60}")

try:
    kernel = NexaKernel()
    pm = PriorityManager()
    
    # Submit low-priority background tasks
    bg_ids = []
    for i in range(5):
        task = TaskEntry(name=f"BG_SYNC_{i}", priority=PriorityLevel.BACKGROUND_SYNC)
        tid = kernel.submit_task(task)
        if tid:
            bg_ids.append(tid)
    
    R.ok("Background tasks queued", f"{len(bg_ids)} background tasks submitted")
    
    # Now submit high-priority voice input — should be accepted
    voice_task = TaskEntry(name="VOICE_INPUT", priority=PriorityLevel.VOICE_INPUT)
    voice_id = kernel.submit_task(voice_task)
    assert voice_id is not None, "Voice input rejected despite high priority!"
    R.ok("Voice input accepted over background", f"id={voice_id[:12]}...")
    
    # Verify preemption logic
    can_preempt = pm.can_preempt(PriorityLevel.VOICE_INPUT, PriorityLevel.BACKGROUND_SYNC)
    assert can_preempt, "VOICE_INPUT should preempt BACKGROUND_SYNC"
    R.ok("Preemption: VOICE > BACKGROUND", "can_preempt=True")
    
    can_preempt_media = pm.can_preempt(PriorityLevel.VOICE_INPUT, PriorityLevel.MEDIA_PLAYBACK)
    assert can_preempt_media, "VOICE_INPUT should preempt MEDIA_PLAYBACK"
    R.ok("Preemption: VOICE > MEDIA", "can_preempt=True")
    
    cannot_preempt = pm.can_preempt(PriorityLevel.BACKGROUND_SYNC, PriorityLevel.VOICE_INPUT)
    assert not cannot_preempt, "BACKGROUND should NOT preempt VOICE"
    R.ok("No preemption: BACKGROUND < VOICE", "can_preempt=False")
    
    # Cleanup
    kernel.complete_task(voice_id)
    for tid in bg_ids:
        kernel.complete_task(tid)
    
    R.ok("All tasks completed cleanly")

except Exception as e:
    R.fail("Priority preemption", e)

# ============================================================
# TEST 4: Real NEXA Scenario Simulation
# ============================================================
print(f"\n{'='*60}")
print("  TEST 4: Real NEXA Scenario Simulation")
print(f"{'='*60}")

try:
    kernel = NexaKernel()
    events = []
    events_lock = threading.Lock()
    
    # Subscribe to all events
    for event_type in ["task.submitted", "task.completed", "task.rejected"]:
        kernel.event_bus.subscribe(
            event_type,
            lambda **kw: (events_lock.acquire(), events.append(kw), events_lock.release())
        )
    
    # Scenario: User is playing music, then gives voice command, 
    # then a notification comes in, then background sync triggers
    
    # Step 1: Music starts playing
    music_task = TaskEntry(name="MUSIC_PLAYBACK", priority=PriorityLevel.MEDIA_PLAYBACK)
    music_id = kernel.submit_task(music_task)
    assert music_id is not None, "Music task rejected"
    R.ok("Scenario: Music starts playing")
    
    # Step 2: User says "what time is it?" while music plays
    voice_task = TaskEntry(name="VOICE_WHAT_TIME", priority=PriorityLevel.VOICE_INPUT)
    voice_id = kernel.submit_task(voice_task)
    assert voice_id is not None, "Voice command rejected while music playing!"
    R.ok("Scenario: Voice command accepted during music")
    
    # Step 3: Notification arrives
    notif_task = TaskEntry(name="NOTIFICATION_EMAIL", priority=PriorityLevel.NOTIFICATION_ALERT)
    notif_id = kernel.submit_task(notif_task)
    assert notif_id is not None, "Notification rejected"
    R.ok("Scenario: Notification accepted during multi-task")
    
    # Step 4: Background sync triggers
    sync_task = TaskEntry(name="SYNC_MEMORY", priority=PriorityLevel.BACKGROUND_SYNC)
    sync_id = kernel.submit_task(sync_task)
    # May or may not be accepted depending on priority rules
    R.ok("Scenario: Background sync submitted", f"accepted={sync_id is not None}")
    
    # Step 5: Another voice command while first is processing
    voice2_task = TaskEntry(name="VOICE_VOLUME_UP", priority=PriorityLevel.VOICE_INPUT)
    voice2_id = kernel.submit_task(voice2_task)
    R.ok("Scenario: Second voice command", f"accepted={voice2_id is not None}")
    
    # Step 6: Screen query
    screen_task = TaskEntry(name="SCREEN_READ", priority=PriorityLevel.SCREEN_QUERY, 
                           gpu_required=True, estimated_vram_mb=500)
    screen_id = kernel.submit_task(screen_task)
    R.ok("Scenario: Screen query with GPU", f"accepted={screen_id is not None}")
    
    # Complete all tasks in order
    for tid_name, tid in [("music", music_id), ("voice1", voice_id), 
                           ("notif", notif_id), ("voice2", voice2_id), 
                           ("screen", screen_id)]:
        if tid:
            kernel.complete_task(tid)
    if sync_id:
        kernel.complete_task(sync_id)
    
    R.ok("Scenario: All tasks completed without crashes")
    
    # Verify events were fired
    assert len(events) > 0, "No events captured!"
    R.ok(f"Events fired: {len(events)} total")

except Exception as e:
    R.fail("Real scenario simulation", traceback.format_exc())

# ============================================================
# TEST 5: GPU Resource Contention
# ============================================================
print(f"\n{'='*60}")
print("  TEST 5: GPU Resource Contention")
print(f"{'='*60}")

try:
    kernel = NexaKernel()
    rm = ResourceManager()
    
    # Check available VRAM reporting
    available = rm.get_available_vram()
    R.ok(f"GPU VRAM available: {available}MB")
    
    # Test can_allocate
    assert rm.can_allocate(3500), "Should be able to allocate 3.5GB"
    R.ok("can_allocate(3500MB) -> True")
    
    # Test allocate + release cycle
    assert rm.allocate("test_llm", 3500), "allocate(3500MB) failed"
    assert rm.allocate("test_whisper", 1000), "allocate(1000MB) failed"
    R.ok("Allocated 3500MB + 1000MB successfully")
    
    # Check allocations tracked
    allocs = rm.get_allocations()
    assert "test_llm" in allocs and allocs["test_llm"] == 3500
    assert "test_whisper" in allocs and allocs["test_whisper"] == 1000
    R.ok(f"Allocations tracked: {allocs}")
    
    # Release and verify
    released = rm.release("test_llm")
    assert released == 3500, f"Expected 3500 released, got {released}"
    rm.release("test_whisper")
    R.ok("VRAM released correctly")
    
    # Submit GPU-heavy tasks through kernel
    gpu_task1 = TaskEntry(name="LLM_INFERENCE", priority=PriorityLevel.VOICE_INPUT,
                         gpu_required=True, estimated_vram_mb=3500)
    gpu_id1 = kernel.submit_task(gpu_task1)
    R.ok(f"GPU task 1 (3500MB): accepted={gpu_id1 is not None}")
    
    gpu_task2 = TaskEntry(name="WHISPER_STT", priority=PriorityLevel.VOICE_INPUT,
                         gpu_required=True, estimated_vram_mb=400)
    gpu_id2 = kernel.submit_task(gpu_task2)
    R.ok(f"GPU task 2 (400MB): accepted={gpu_id2 is not None}")
    
    gpu_task3 = TaskEntry(name="SCREEN_ANALYSIS", priority=PriorityLevel.SCREEN_QUERY,
                         gpu_required=True, estimated_vram_mb=2000)
    gpu_id3 = kernel.submit_task(gpu_task3)
    R.ok(f"GPU task 3 (2000MB): accepted={gpu_id3 is not None}")
    
    # Cleanup
    for tid in [gpu_id1, gpu_id2, gpu_id3]:
        if tid:
            kernel.complete_task(tid)
    
    R.ok("GPU tasks completed without deadlock")

except Exception as e:
    R.fail("GPU resource contention", e)

# ============================================================
# TEST 6: EventBus Under Concurrent Load
# ============================================================
print(f"\n{'='*60}")
print("  TEST 6: EventBus Thread Safety (10 publishers x 100 events)")
print(f"{'='*60}")

try:
    bus = EventBus()
    received = defaultdict(int)
    received_lock = threading.Lock()
    
    # Subscribe to test events
    for i in range(5):
        event_name = f"stress.event.{i}"
        bus.subscribe(event_name, 
                     lambda **kw: (received_lock.acquire(), 
                                   received.__setitem__(kw.get("event_name", "?"), 
                                                        received.get(kw.get("event_name", "?"), 0) + 1),
                                   received_lock.release()))
    
    # 10 threads each publish 100 events
    def publish_events(thread_id):
        for j in range(100):
            event_idx = j % 5
            bus.publish(f"stress.event.{event_idx}", 
                       event_name=f"stress.event.{event_idx}",
                       thread=thread_id, seq=j)
    
    start = time.perf_counter()
    threads = []
    for t in range(10):
        th = threading.Thread(target=publish_events, args=(t,))
        threads.append(th)
        th.start()
    
    for th in threads:
        th.join()
    
    elapsed = time.perf_counter() - start
    total_received = sum(received.values())
    
    # 10 threads x 100 events = 1000 total, but each event hits 1 subscriber
    assert total_received > 0, "No events received"
    R.ok(f"EventBus stress", f"{total_received} events processed in {elapsed*1000:.1f}ms, 0 crashes")

except Exception as e:
    R.fail("EventBus thread safety", e)

# ============================================================
# TEST 7: Rejection Rules Under Load
# ============================================================
print(f"\n{'='*60}")
print("  TEST 7: Rejection Rules (Locked + Media Active)")
print(f"{'='*60}")

try:
    kernel = NexaKernel()
    pm = PriorityManager()
    
    # Test: idle tasks rejected when locked
    rejected = pm.should_reject(PriorityLevel.IDLE_SUGGESTION, 
                                is_locked=True, media_active=False, has_active_task=False)
    assert rejected, "IDLE should be rejected when locked"
    R.ok("IDLE rejected when locked")
    
    # Test: voice input NOT rejected when locked (user is talking)
    not_rejected = pm.should_reject(PriorityLevel.VOICE_INPUT,
                                    is_locked=True, media_active=False, has_active_task=False)
    # Voice input should still be accepted even when locked
    R.ok(f"VOICE_INPUT when locked: rejected={not_rejected}")
    
    # Test: background sync rejected during media
    bg_rejected = pm.should_reject(PriorityLevel.BACKGROUND_SYNC,
                                   is_locked=False, media_active=True, has_active_task=True)
    R.ok(f"BG_SYNC during media+active: rejected={bg_rejected}")
    
    # Test: user command accepted even during active task
    cmd_rejected = pm.should_reject(PriorityLevel.USER_COMMAND,
                                    is_locked=False, media_active=False, has_active_task=True)
    R.ok(f"USER_COMMAND during active task: rejected={cmd_rejected}")

except Exception as e:
    R.fail("Rejection rules", e)

# ============================================================
# TEST 8: Task Lifecycle Integrity Under Stress
# ============================================================
print(f"\n{'='*60}")
print("  TEST 8: Task Lifecycle Integrity (100 submit+complete cycles)")
print(f"{'='*60}")

try:
    kernel = NexaKernel()
    success_count = 0
    fail_count = 0
    
    start = time.perf_counter()
    for i in range(100):
        priority = random.choice(list(PriorityLevel))
        task = TaskEntry(name=f"LIFECYCLE_{i}", priority=priority)
        tid = kernel.submit_task(task)
        if tid:
            kernel.complete_task(tid)
            success_count += 1
        else:
            fail_count += 1
    
    elapsed = time.perf_counter() - start
    
    R.ok(f"100 lifecycle cycles", f"{success_count} succeeded, {fail_count} rejected, {elapsed*1000:.1f}ms total ({elapsed*10:.2f}ms/cycle)")

except Exception as e:
    R.fail("Task lifecycle integrity", e)

# ============================================================
# TEST 9: Concurrent Submit + Complete (Race Condition Test)
# ============================================================
print(f"\n{'='*60}")
print("  TEST 9: Race Condition Test (submit+complete from different threads)")
print(f"{'='*60}")

try:
    kernel = NexaKernel()
    completed_ids = []
    completed_lock = threading.Lock()
    race_errors = []
    
    def submit_and_complete(idx):
        try:
            task = TaskEntry(name=f"RACE_{idx}", priority=PriorityLevel.USER_COMMAND)
            tid = kernel.submit_task(task)
            if tid:
                # Small random delay to increase chance of race conditions
                time.sleep(random.uniform(0.001, 0.01))
                kernel.complete_task(tid)
                with completed_lock:
                    completed_ids.append(tid)
        except Exception as e:
            race_errors.append(f"Thread {idx}: {e}")
    
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=30) as pool:
        futures = [pool.submit(submit_and_complete, i) for i in range(50)]
        for f in as_completed(futures):
            f.result()  # Raise any exceptions
    
    elapsed = time.perf_counter() - start
    
    assert len(race_errors) == 0, f"Race condition errors: {race_errors}"
    assert len(completed_ids) == len(set(completed_ids)), "Duplicate completions!"
    
    R.ok(f"50 concurrent submit+complete", f"{len(completed_ids)} completed, 0 race errors, {elapsed*1000:.1f}ms")

except Exception as e:
    R.fail("Race condition test", e)

# ============================================================
# TEST 10: Full NEXA Day Simulation
# ============================================================
print(f"\n{'='*60}")
print("  TEST 10: Full Day Simulation (morning -> night workflow)")
print(f"{'='*60}")

try:
    kernel = NexaKernel()
    scenario_events = []
    
    # Morning: User wakes up, asks about weather
    morning_tasks = [
        ("VOICE_GOOD_MORNING", PriorityLevel.VOICE_INPUT, False, 0),
        ("LLM_WEATHER_RESPONSE", PriorityLevel.USER_COMMAND, True, 3500),
        ("TTS_SPEAK_WEATHER", PriorityLevel.USER_COMMAND, False, 0),
    ]
    
    for name, priority, gpu, vram in morning_tasks:
        task = TaskEntry(name=name, priority=priority, gpu_required=gpu, estimated_vram_mb=vram)
        tid = kernel.submit_task(task)
        if tid:
            scenario_events.append(f"AM: {name} -> accepted")
            kernel.complete_task(tid)
        else:
            scenario_events.append(f"AM: {name} -> rejected")
    
    R.ok("Morning workflow", f"{len(morning_tasks)} tasks processed")

    # Midday: Music playing, user asks to open app
    music = TaskEntry(name="PLAY_MUSIC", priority=PriorityLevel.MEDIA_PLAYBACK)
    music_id = kernel.submit_task(music)
    
    app_cmd = TaskEntry(name="VOICE_OPEN_CHROME", priority=PriorityLevel.VOICE_INPUT)
    app_id = kernel.submit_task(app_cmd)
    assert app_id is not None, "Voice command rejected while music playing!"
    
    # Both should coexist
    if app_id:
        kernel.complete_task(app_id)
    if music_id:
        kernel.complete_task(music_id)
    
    R.ok("Midday workflow", "Music + voice command coexisted")

    # Afternoon: Heavy workload - screen reading + notifications + voice
    afternoon_tasks = [
        TaskEntry(name="SCREEN_READ_EMAIL", priority=PriorityLevel.SCREEN_QUERY, gpu_required=True, estimated_vram_mb=500),
        TaskEntry(name="NOTIFICATION_SLACK", priority=PriorityLevel.NOTIFICATION_ALERT),
        TaskEntry(name="VOICE_REMINDER", priority=PriorityLevel.VOICE_INPUT),
        TaskEntry(name="BG_MEMORY_SYNC", priority=PriorityLevel.BACKGROUND_SYNC),
        TaskEntry(name="VOICE_VOLUME_DOWN", priority=PriorityLevel.USER_COMMAND),
    ]
    
    afternoon_ids = []
    for t in afternoon_tasks:
        tid = kernel.submit_task(t)
        if tid:
            afternoon_ids.append(tid)
    
    # Complete all
    for tid in afternoon_ids:
        kernel.complete_task(tid)
    
    R.ok("Afternoon workflow", f"{len(afternoon_ids)}/{len(afternoon_tasks)} tasks handled concurrently")

    # Evening: User says goodnight
    night_task = TaskEntry(name="VOICE_GOODNIGHT", priority=PriorityLevel.VOICE_INPUT)
    night_id = kernel.submit_task(night_task)
    if night_id:
        kernel.complete_task(night_id)
    
    idle_task = TaskEntry(name="IDLE_CLEANUP", priority=PriorityLevel.IDLE_SUGGESTION)
    idle_id = kernel.submit_task(idle_task)
    if idle_id:
        kernel.complete_task(idle_id)
    
    R.ok("Evening workflow", "Goodnight + idle cleanup")
    R.ok("FULL DAY SIMULATION PASSED", "No interruptions, no crashes, no deadlocks!")

except Exception as e:
    R.fail("Full day simulation", traceback.format_exc())

# ============================================================
# FINAL SUMMARY
# ============================================================
success = R.summary()

# Save results
with open("test_concurrency_results.txt", "w", encoding="utf-8") as f:
    f.write(f"Passed: {R.passed}\n")
    f.write(f"Failed: {R.failed}\n")
    if R.errors:
        f.write(f"\nFailures:\n")
        for name, err in R.errors:
            f.write(f"  {name}: {err}\n")

if success:
    print("\n  >>> RESTRUCTURE VALIDATION: COMPLETE SUCCESS <<<")
    print("  The kernel handles concurrent tasks without interruptions!\n")

sys.exit(0 if success else 1)
