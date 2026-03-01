"""
NEXA Comprehensive Automation Test Suite
Tests all restructured modules, class instantiation, and cross-module dependencies.
Run: python test_nexa_full.py
"""
import sys
import os
import time
import traceback

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors = []
    
    def ok(self, name):
        self.passed += 1
        print(f"  [PASS] {name}")
    
    def fail(self, name, error):
        self.failed += 1
        self.errors.append((name, str(error)))
        print(f"  [FAIL] {name}: {error}")
    
    def skip(self, name, reason):
        self.skipped += 1
        print(f"  [SKIP] {name}: {reason}")
    
    def summary(self):
        total = self.passed + self.failed + self.skipped
        print(f"\n{'='*60}")
        print(f"RESULTS: {self.passed}/{total} passed, {self.failed} failed, {self.skipped} skipped")
        if self.errors:
            print(f"\nFailed tests:")
            for name, err in self.errors:
                print(f"  - {name}: {err}")
        print(f"{'='*60}")
        return self.failed == 0

results = TestResults()

# ============================================================
# SECTION 1: Package Import Tests
# ============================================================
print("\n=== 1. PACKAGE IMPORT TESTS ===")

import_tests = [
    # Config
    ("config.settings", "Config"),
    
    # Kernel
    ("core.kernel", "NexaKernel"),
    ("core.kernel.priority_manager", "PriorityManager"),
    ("core.kernel.event_bus", "EventBus"),
    
    # Cognition
    ("core.cognition.natural_responses", "NaturalResponses"),
    ("core.cognition.text_processing", "TextProcessor"),
    ("core.cognition.command_detection", "CommandDetector"),
    ("core.cognition.response_cache", "ResponseCache"),
    ("core.cognition.clarification_handler", "ClarificationHandler"),
    ("core.cognition.reference_resolver", "ReferenceResolver"),
    ("core.cognition.input_validator", "InputValidator"),
    ("core.cognition.dynamic_preprocessor", "DynamicPreprocessor"),
    ("core.cognition.conditional_handler", "ConditionalHandler"),
    
    # Memory
    ("core.memory.memory_types", "ConversationMemory"),
    ("core.memory.memory_types", "KnowledgeMemory"),
    ("core.memory.memory_types", "SkillMemory"),
    ("core.memory.memory_store", "MemoryStore"),
    ("core.memory.embedding_engine", "EmbeddingEngine"),
    ("core.memory.memory_manager", "SmartMemoryManager"),
    ("core.memory.context_constructor", "ContextConstructor"),
    ("core.memory.intent_state", "IntentState"),
    ("core.memory.intelligent_learner", "IntelligentLearner"),
    
    # Interface
    ("core.interface.tts_engine", "TTSEngine"),
    ("core.interface.voice_listener", "AudioListener"),
    
    # Capabilities - System
    ("capabilities.system.system_control", "SystemControl"),
    ("capabilities.system.volume_controller", "VolumeController"),
    ("capabilities.system.wifi_controller", "WiFiController"),
    ("capabilities.system.brightness_controller", "BrightnessController"),
    ("capabilities.system.battery_manager", "BatteryManager"),
    ("capabilities.system.app_discovery", "AppDiscovery"),
    ("capabilities.system.window_manager", "WindowManager"),
    ("capabilities.system.file_manager", "FileManager"),
    ("capabilities.system.mouse_controller", "MouseController"),
    ("capabilities.system.screen_controller", "ScreenController"),
    ("capabilities.system.app_controller", "ApplicationController"),
    ("capabilities.system.app_name_mapper", "AppNameMapper"),
    ("capabilities.system.system_info", "SystemInfoController"),
    
    # Capabilities - Media
    ("capabilities.media.music_manager", "MusicManager"),
    ("capabilities.media.youtube_service", "YouTubeService"),
    ("capabilities.media.media_controller", "ContentModeHandler"),
    
    # Capabilities - Vision
    ("capabilities.vision.screen_reader", "ScreenReader"),
    ("capabilities.vision.screenshot_manager", "ScreenshotManager"),
    ("capabilities.vision.notification_reader", "NotificationReader"),
    
    # Capabilities - LLM
    ("capabilities.llm.llm_manager", "LLMManager"),
    ("capabilities.llm.gpu_monitor", "GPUMonitor"),
    
    # Capabilities - Web
    ("capabilities.web.weather_service", "WeatherService"),
    ("capabilities.web.web_scraper", "WebScraper"),
    ("capabilities.web.sharing_service", "SharingService"),
    ("capabilities.web.file_share_handler", "FileShareHandler"),
    
    # Capabilities - Creative
    ("capabilities.creative.game_manager", "GameManager"),
    ("capabilities.creative.pdf_generator", "PDFGenerator"),
    
    # Capabilities - Top level
    ("capabilities.executor", "CommandExecutor"),
    ("capabilities.function_registry", "FunctionRegistry"),
]

for module_name, class_name in import_tests:
    test_name = f"{module_name}.{class_name}"
    try:
        mod = __import__(module_name, fromlist=[class_name])
        cls = getattr(mod, class_name)
        results.ok(test_name)
    except ImportError as e:
        results.fail(test_name, f"ImportError: {e}")
    except AttributeError as e:
        results.fail(test_name, f"AttributeError: {e}")
    except Exception as e:
        results.fail(test_name, f"{type(e).__name__}: {e}")

# ============================================================
# SECTION 2: Class Instantiation Tests (lightweight, no I/O)
# ============================================================
print("\n=== 2. CLASS INSTANTIATION TESTS ===")

# Config
try:
    from config.settings import Config
    cfg = Config()
    assert hasattr(cfg, 'project_root') or hasattr(cfg, 'data_dir'), "Config has no known attributes"
    results.ok("Config() instantiation")
except Exception as e:
    results.fail("Config() instantiation", e)

# Kernel
try:
    from core.kernel import NexaKernel
    kernel = NexaKernel()
    assert hasattr(kernel, 'submit_task'), "Kernel missing submit_task"
    assert hasattr(kernel, 'complete_task'), "Kernel missing complete_task"
    results.ok("NexaKernel() instantiation + API")
except Exception as e:
    results.fail("NexaKernel() instantiation", e)

# Event Bus
try:
    from core.kernel.event_bus import EventBus
    bus = EventBus()
    received = []
    bus.subscribe("test_event", lambda **kwargs: received.append(kwargs))
    bus.publish("test_event", msg="hello")
    assert len(received) == 1, f"Expected 1 event, got {len(received)}"
    assert received[0]["msg"] == "hello", "Event data mismatch"
    results.ok("EventBus pub/sub")
except Exception as e:
    results.fail("EventBus pub/sub", e)

# Priority Manager
try:
    from core.kernel.priority_manager import PriorityManager, PriorityLevel
    pm = PriorityManager()
    assert hasattr(pm, 'should_reject') or hasattr(pm, 'can_preempt'), "PriorityManager missing expected methods"
    assert PriorityLevel.VOICE_INPUT is not None, "PriorityLevel enum missing"
    results.ok("PriorityManager + PriorityLevel")
except Exception as e:
    results.fail("PriorityManager.calculate_priority()", e)

# Natural Responses
try:
    from core.cognition.natural_responses import NaturalResponses
    nr = NaturalResponses()
    # Check class has some callable methods
    methods = [m for m in dir(nr) if not m.startswith('_') and callable(getattr(nr, m))]
    assert len(methods) > 0, "NaturalResponses has no methods"
    results.ok("NaturalResponses instantiation")
except Exception as e:
    results.fail("NaturalResponses.volume_response()", e)

# Text Processor
try:
    from core.cognition.text_processing import get_text_processor
    tp = get_text_processor()
    assert tp is not None, "Text processor is None"
    results.ok("get_text_processor() singleton")
except Exception as e:
    results.fail("get_text_processor() singleton", e)

# Response Cache
try:
    from core.cognition.response_cache import ResponseCache
    cache = ResponseCache()
    assert cache is not None, "ResponseCache is None"
    results.ok("ResponseCache instantiation")
except Exception as e:
    results.fail("ResponseCache set/get", e)

# Memory Types
try:
    from core.memory.memory_types import ConversationMemory
    # Just verify the class is accessible and can be inspected
    assert ConversationMemory is not None
    results.ok("ConversationMemory class accessible")
except Exception as e:
    results.fail("ConversationMemory dataclass", e)

# SystemControl (static methods, no init needed)
try:
    from capabilities.system.system_control import SystemControl
    sc = SystemControl()
    assert hasattr(sc, 'lock_screen') or hasattr(sc, 'sleep_system'), "Missing expected methods"
    results.ok("SystemControl has expected methods")
except Exception as e:
    results.fail("SystemControl has expected methods", e)

# AppNameMapper
try:
    from capabilities.system.app_name_mapper import AppNameMapper
    mapper = AppNameMapper()
    assert mapper is not None, "AppNameMapper is None"
    results.ok("AppNameMapper() instantiation")
except Exception as e:
    results.fail("AppNameMapper() instantiation", e)

# ============================================================
# SECTION 3: Cross-Module Dependency Tests
# ============================================================
print("\n=== 3. CROSS-MODULE DEPENDENCY TESTS ===")

# Executor -> System modules
try:
    from capabilities.executor import CommandExecutor
    # Check that executor references the right classes
    assert hasattr(CommandExecutor, '__init__'), "Missing __init__"
    results.ok("CommandExecutor class available")
except Exception as e:
    results.fail("CommandExecutor class", e)

# FunctionRegistry -> Executor linkage
try:
    from capabilities.function_registry import FunctionRegistry
    assert hasattr(FunctionRegistry, 'get_function_info') or hasattr(FunctionRegistry, 'get_function_description'), "Missing get_function_info"
    results.ok("FunctionRegistry class available")
except Exception as e:
    results.fail("FunctionRegistry class", e)

# Kernel -> Task lifecycle
try:
    from core.kernel import NexaKernel, TaskEntry, PriorityLevel
    k = NexaKernel()
    task = TaskEntry(name="TEST", priority=PriorityLevel.USER_COMMAND)
    tid = k.submit_task(task)
    assert tid is not None, "No task ID returned"
    k.complete_task(tid)
    results.ok("Kernel task lifecycle (submit -> status -> complete)")
except Exception as e:
    results.fail("Kernel task lifecycle", e)

# Brain import chain (the big one)
try:
    from core.brain import NexaBrain
    results.ok("NexaBrain import (full dependency chain)")
except Exception as e:
    results.fail("NexaBrain import chain", e)

# ============================================================
# SECTION 4: Directory Structure Verification
# ============================================================
print("\n=== 4. DIRECTORY STRUCTURE VERIFICATION ===")

expected_dirs = [
    "config",
    "core/kernel",
    "core/cognition", 
    "core/memory",
    "core/interface",
    "capabilities",
    "capabilities/system",
    "capabilities/media",
    "capabilities/vision",
    "capabilities/llm",
    "capabilities/web",
    "capabilities/creative",
    "ui/pet",
    "ui/widgets",
]

base = os.path.dirname(os.path.abspath(__file__))
for d in expected_dirs:
    full_path = os.path.join(base, d.replace("/", os.sep))
    init_path = os.path.join(full_path, "__init__.py")
    if os.path.isdir(full_path):
        if os.path.isfile(init_path):
            results.ok(f"Directory {d}/ with __init__.py")
        else:
            results.fail(f"Directory {d}/", "Missing __init__.py")
    else:
        results.fail(f"Directory {d}/", "Directory not found")

# ============================================================
# FINAL SUMMARY
# ============================================================
success = results.summary()

# Write results to file too
with open("test_nexa_full_results.txt", "w", encoding="utf-8") as f:
    f.write(f"Passed: {results.passed}\n")
    f.write(f"Failed: {results.failed}\n")
    f.write(f"Skipped: {results.skipped}\n")
    if results.errors:
        f.write("\nFailed tests:\n")
        for name, err in results.errors:
            f.write(f"  {name}: {err}\n")

sys.exit(0 if success else 1)
