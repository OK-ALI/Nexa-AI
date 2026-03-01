"""
Kernel verification — fully isolated from core/__init__.py.
Uses importlib to load kernel modules directly without triggering
the parent core package's heavy imports.
"""
import sys
import os
import importlib.util

base = os.path.dirname(os.path.abspath(__file__))

def load_module(name, path):
    """Load a Python module from a specific file path."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

# Load kernel modules directly to avoid core/__init__.py
pm_mod = load_module(
    "core.kernel.priority_manager",
    os.path.join(base, "core", "kernel", "priority_manager.py")
)
eb_mod = load_module(
    "core.kernel.event_bus",
    os.path.join(base, "core", "kernel", "event_bus.py")
)
tq_mod = load_module(
    "core.kernel.task_queue",
    os.path.join(base, "core", "kernel", "task_queue.py")
)
rm_mod = load_module(
    "core.kernel.resource_manager",
    os.path.join(base, "core", "kernel", "resource_manager.py")
)
k_mod = load_module(
    "core.kernel.kernel",
    os.path.join(base, "core", "kernel", "kernel.py")
)

PriorityLevel = pm_mod.PriorityLevel
PriorityManager = pm_mod.PriorityManager
EventBus = eb_mod.EventBus
TaskEntry = tq_mod.TaskEntry
TaskQueue = tq_mod.TaskQueue
ResourceManager = rm_mod.ResourceManager
NexaKernel = k_mod.NexaKernel

print("✅ All kernel imports OK (isolated)")

# Test 1: Kernel creation
k = NexaKernel()
assert k.is_locked == False
assert k.is_media_active == False
print("✅ Kernel created: locked=False, media=False")

# Test 2: Clean kernel allows idle
assert k.can_run_idle() == True
print("✅ Clean kernel -> can_run_idle: True")

# Test 3: Lock blocks idle
k.set_locked(True)
assert k.can_run_idle() == False
print("✅ Locked -> can_run_idle: False")

# Test 4: Unlock re-enables
k.set_locked(False)
assert k.can_run_idle() == True
print("✅ Unlocked -> can_run_idle: True")

# Test 5: Media blocks idle
k.set_media_active(True)
assert k.can_run_idle() == False
print("✅ Media active -> can_run_idle: False")

# Test 6: Idle rejected during media
t1 = TaskEntry(name="idle_during_media", priority=PriorityLevel.IDLE_SUGGESTION)
tid1 = k.submit_task(t1)
assert tid1 is None
print("✅ Idle task during media: REJECTED")

# Test 7: User command accepted during media
t2 = TaskEntry(name="user_cmd", priority=PriorityLevel.USER_COMMAND)
tid2 = k.submit_task(t2)
assert tid2 is not None
print(f"✅ User command during media: ACCEPTED ({tid2})")

# Test 8: Priority preemption
pm = PriorityManager()
assert pm.can_preempt(PriorityLevel.VOICE_INPUT, PriorityLevel.IDLE_SUGGESTION) == True
assert pm.can_preempt(PriorityLevel.IDLE_SUGGESTION, PriorityLevel.VOICE_INPUT) == False
assert pm.can_preempt(PriorityLevel.USER_COMMAND, PriorityLevel.MEDIA_PLAYBACK) == True
print("✅ Priority preemption: voice > idle, user > media")

# Test 9: Task lifecycle
k2 = NexaKernel()
t3 = TaskEntry(name="lifecycle_test", priority=PriorityLevel.IDLE_SUGGESTION)
tid3 = k2.submit_task(t3)
assert tid3 is not None
k2.activate_task(t3)
assert k2.task_queue.has_active_tasks() == True
k2.complete_task(tid3)
assert k2.task_queue.has_active_tasks() == False
print("✅ Task lifecycle: submit → activate → complete")

# Test 10: Idle rejected with active task
k3 = NexaKernel()
t4 = TaskEntry(name="active_cmd", priority=PriorityLevel.USER_COMMAND)
k3.submit_task(t4)
k3.activate_task(t4)
t5 = TaskEntry(name="idle_while_active", priority=PriorityLevel.IDLE_SUGGESTION)
tid5 = k3.submit_task(t5)
assert tid5 is None
print("✅ Idle rejected while task active")

# Test 11: Event bus
events = []
eb = EventBus()
eb.subscribe("test.event", lambda **kw: events.append(kw))
eb.publish("test.event", value=42)
assert len(events) == 1 and events[0]["value"] == 42
print("✅ Event bus pub/sub works")

# Test 12: Resource manager
rm = ResourceManager(total_vram_mb=8192, safe_threshold_mb=7372)
assert rm.can_allocate(3500) == True
assert rm.allocate("task_llm", 3500) == True
assert rm.can_allocate(4000) == False  # 3500+4000=7500 > 7372
assert rm.can_allocate(3800) == True   # 3500+3800=7300 <= 7372
rm.release("task_llm")
assert rm.can_allocate(7000) == True
print("✅ Resource manager VRAM gating works")

# Test 13: GPU allocation via kernel
k4 = NexaKernel()
t6 = TaskEntry(name="gpu_task", priority=PriorityLevel.USER_COMMAND, gpu_required=True, estimated_vram_mb=3500)
tid6 = k4.submit_task(t6)
assert tid6 is not None
ok = k4.activate_task(t6)
assert ok == True
k4.complete_task(tid6)
print("✅ GPU task: submit → allocate VRAM → activate → complete → release")

# Cleanup
k.shutdown()
k2.shutdown()
k3.shutdown()
k4.shutdown()

print("\n🎉 ALL 13 TESTS PASSED — Kernel is fully functional!")
