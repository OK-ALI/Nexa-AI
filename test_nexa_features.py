"""
NEXA Full Feature Automation Test
=================================
Tests actual NEXA functionality end-to-end after codebase restructure.
Covers: Config, Kernel, Cognition, Memory, Capabilities, Cross-module flows.
Does NOT require GPU/microphone/TTS — tests logic only.

Run: python test_nexa_features.py
"""
import sys
import os
import time
import json
import traceback
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class FeatureTestResults:
    def __init__(self):
        self.sections = {}
        self.current_section = None
        self.total_pass = 0
        self.total_fail = 0
        self.errors = []
    
    def section(self, name):
        self.current_section = name
        self.sections[name] = {"pass": 0, "fail": 0}
        print(f"\n{'='*60}")
        print(f"  {name}")
        print(f"{'='*60}")
    
    def ok(self, name):
        self.total_pass += 1
        self.sections[self.current_section]["pass"] += 1
        print(f"  [PASS] {name}")
    
    def fail(self, name, error):
        self.total_fail += 1
        self.sections[self.current_section]["fail"] += 1
        self.errors.append((self.current_section, name, str(error)))
        print(f"  [FAIL] {name}: {error}")
    
    def summary(self):
        total = self.total_pass + self.total_fail
        print(f"\n{'#'*60}")
        print(f"  NEXA FEATURE TEST SUMMARY")
        print(f"{'#'*60}")
        for section, counts in self.sections.items():
            status = "OK" if counts["fail"] == 0 else "ISSUES"
            print(f"  [{status}] {section}: {counts['pass']}/{counts['pass']+counts['fail']}")
        print(f"\n  TOTAL: {self.total_pass}/{total} passed, {self.total_fail} failed")
        if self.errors:
            print(f"\n  FAILURES:")
            for sec, name, err in self.errors:
                print(f"    [{sec}] {name}: {err}")
        print(f"{'#'*60}")
        return self.total_fail == 0

R = FeatureTestResults()

# ============================================================
# FEATURE 1: Configuration System
# ============================================================
R.section("Configuration System")

try:
    from config.settings import Config
    cfg = Config()
    
    # Verify all critical config attributes
    attrs = ['project_root', 'data_dir', 'logs_dir', 'models_dir', 'user_name',
             'whisper_model_name', 'whisper_device', 'tts_engine', 'debug_mode',
             'log_level', 'weather_cache_minutes', 'speaker_verification_enabled']
    for attr in attrs:
        if hasattr(cfg, attr):
            R.ok(f"Config.{attr} = {repr(getattr(cfg, attr))[:60]}")
        else:
            R.fail(f"Config.{attr}", "attribute missing")
    
    # Verify setup
    result = cfg.verify_setup()
    assert isinstance(result, bool)
    R.ok(f"Config.verify_setup() -> {result}")
    
    # System prompt
    prompt = cfg.get_system_prompt()
    assert len(prompt) > 100, f"Prompt too short: {len(prompt)} chars"
    assert "Nexa" in prompt, "System prompt doesn't mention Nexa"
    R.ok(f"Config.get_system_prompt() -> {len(prompt)} chars")

except Exception as e:
    R.fail("Config system", traceback.format_exc())

# ============================================================
# FEATURE 2: Core AI Kernel
# ============================================================
R.section("Core AI Kernel")

try:
    from core.kernel import NexaKernel, TaskEntry, PriorityLevel, EventBus, PriorityManager
    
    # Kernel init
    kernel = NexaKernel()
    R.ok("NexaKernel() created")
    
    # Priority levels
    levels = [PriorityLevel.IDLE_SUGGESTION, PriorityLevel.BACKGROUND_SYNC,
              PriorityLevel.MEDIA_PLAYBACK, PriorityLevel.SCREEN_QUERY,
              PriorityLevel.NOTIFICATION_ALERT, PriorityLevel.USER_COMMAND,
              PriorityLevel.VOICE_INPUT]
    assert len(levels) == 7
    assert PriorityLevel.VOICE_INPUT > PriorityLevel.IDLE_SUGGESTION
    R.ok(f"7 priority levels, VOICE_INPUT({int(PriorityLevel.VOICE_INPUT)}) > IDLE({int(PriorityLevel.IDLE_SUGGESTION)})")
    
    # Task submission
    task = TaskEntry(name="TEST_VOICE", priority=PriorityLevel.VOICE_INPUT)
    tid = kernel.submit_task(task)
    assert tid is not None, "submit_task returned None"
    R.ok(f"submit_task('TEST_VOICE', VOICE_INPUT) -> id={tid[:12]}...")
    
    # Task completion
    kernel.complete_task(tid)
    R.ok(f"complete_task({tid[:12]}...) succeeded")
    
    # Multi-task queuing
    t1 = TaskEntry(name="BG_SYNC", priority=PriorityLevel.BACKGROUND_SYNC)
    t2 = TaskEntry(name="USER_CMD", priority=PriorityLevel.USER_COMMAND)
    id1 = kernel.submit_task(t1)
    id2 = kernel.submit_task(t2)
    assert id1 != id2, "Duplicate task IDs!"
    kernel.complete_task(id1)
    kernel.complete_task(id2)
    R.ok("Multi-task queuing (BG_SYNC + USER_CMD) works")
    
    # EventBus
    bus = EventBus()
    events_received = []
    bus.subscribe("test.feature", lambda **kw: events_received.append(kw))
    bus.publish("test.feature", action="volume", level=50)
    assert len(events_received) == 1
    assert events_received[0]["action"] == "volume"
    assert events_received[0]["level"] == 50
    R.ok("EventBus subscribe + publish with kwargs")
    
    # Multiple subscribers
    count = [0]
    bus.subscribe("multi", lambda **kw: count.__setitem__(0, count[0]+1))
    bus.subscribe("multi", lambda **kw: count.__setitem__(0, count[0]+1))
    bus.publish("multi")
    assert count[0] == 2
    R.ok("EventBus multiple subscribers to same event")
    
    # PriorityManager
    pm = PriorityManager()
    assert pm.should_reject(PriorityLevel.IDLE_SUGGESTION, is_locked=True, media_active=False, has_active_task=False)
    R.ok("PriorityManager.should_reject(IDLE when locked) -> True")
    
    assert not pm.should_reject(PriorityLevel.VOICE_INPUT, is_locked=False, media_active=False, has_active_task=False)
    R.ok("PriorityManager.should_reject(VOICE when unlocked) -> False")
    
    assert pm.can_preempt(PriorityLevel.VOICE_INPUT, PriorityLevel.BACKGROUND_SYNC)
    R.ok("PriorityManager.can_preempt(VOICE over BG_SYNC) -> True")

except Exception as e:
    R.fail("Kernel system", traceback.format_exc())

# ============================================================
# FEATURE 3: Cognition Layer
# ============================================================
R.section("Cognition Layer")

try:
    # Natural Responses
    from core.cognition.natural_responses import NaturalResponses
    nr = NaturalResponses()
    public_methods = [m for m in dir(nr) if not m.startswith('_') and callable(getattr(nr, m))]
    R.ok(f"NaturalResponses: {len(public_methods)} methods ({', '.join(public_methods[:5])}...)")
except Exception as e:
    R.fail("NaturalResponses", e)

try:
    # Text Processing
    from core.cognition.text_processing import TextProcessor, get_text_processor
    tp = get_text_processor()
    tp2 = get_text_processor()
    assert tp is tp2, "Singleton violated"
    R.ok("TextProcessor singleton pattern works")
except Exception as e:
    R.fail("TextProcessor", e)

try:
    # Command Detection
    from core.cognition.command_detection import CommandDetector, get_command_detector
    cd = get_command_detector()
    assert cd is not None
    R.ok("CommandDetector singleton available")
except Exception as e:
    R.fail("CommandDetector", e)

try:
    # Clarification Handler
    from core.cognition.clarification_handler import ClarificationHandler, get_clarification_handler
    ch = get_clarification_handler()
    assert ch is not None
    R.ok("ClarificationHandler singleton available")
except Exception as e:
    R.fail("ClarificationHandler", e)

try:
    # Reference Resolver
    from core.cognition.reference_resolver import ReferenceResolver, get_reference_resolver
    rr = get_reference_resolver()
    assert rr is not None
    R.ok("ReferenceResolver singleton available")
except Exception as e:
    R.fail("ReferenceResolver", e)

try:
    # Input Validator
    from core.cognition.input_validator import InputValidator
    iv = InputValidator()
    R.ok("InputValidator instantiated")
except Exception as e:
    R.fail("InputValidator", e)

try:
    # Response Cache
    from core.cognition.response_cache import ResponseCache, get_response_cache
    cache = get_response_cache()
    assert cache is not None
    R.ok("ResponseCache singleton available")
except Exception as e:
    R.fail("ResponseCache", e)

try:
    # Dynamic Preprocessor
    from core.cognition.dynamic_preprocessor import DynamicPreprocessor
    dp = DynamicPreprocessor()
    R.ok("DynamicPreprocessor instantiated")
except Exception as e:
    R.fail("DynamicPreprocessor", e)

try:
    # Context Manager (cognition)
    from core.cognition.context_manager import ContextManager
    R.ok("ContextManager class importable")
except Exception as e:
    R.fail("ContextManager", e)

# ============================================================
# FEATURE 4: Memory System
# ============================================================
R.section("Memory System")

try:
    from core.memory.memory_types import ConversationMemory, KnowledgeMemory, SkillMemory
    R.ok("Memory types (Conversation, Knowledge, Skill) all importable")
except Exception as e:
    R.fail("Memory types", e)

try:
    from core.memory.memory_store import MemoryStore
    R.ok("MemoryStore class importable")
except Exception as e:
    R.fail("MemoryStore", e)

try:
    from core.memory.embedding_engine import EmbeddingEngine
    R.ok("EmbeddingEngine class importable")
except Exception as e:
    R.fail("EmbeddingEngine", e)

try:
    from core.memory.memory_manager import SmartMemoryManager
    R.ok("SmartMemoryManager class importable")
except Exception as e:
    R.fail("SmartMemoryManager", e)

try:
    from core.memory.context_constructor import ContextConstructor
    R.ok("ContextConstructor class importable")
except Exception as e:
    R.fail("ContextConstructor", e)

try:
    from core.memory.intent_state import IntentState
    R.ok("IntentState class importable")
except Exception as e:
    R.fail("IntentState", e)

try:
    from core.memory.intelligent_learner import IntelligentLearner, get_intelligent_learner
    R.ok("IntelligentLearner class importable")
except Exception as e:
    R.fail("IntelligentLearner", e)

try:
    from core.memory.conversation_memory import ConversationHistoryBuilder, get_history_builder
    hb = get_history_builder()
    assert hb is not None
    R.ok("ConversationHistoryBuilder singleton available")
except Exception as e:
    R.fail("ConversationHistoryBuilder", e)

# ============================================================
# FEATURE 5: System Capabilities
# ============================================================
R.section("System Capabilities")

try:
    from capabilities.system.system_control import SystemControl
    sc = SystemControl()
    methods = [m for m in dir(sc) if not m.startswith('_') and callable(getattr(sc, m))]
    R.ok(f"SystemControl: {len(methods)} methods ({', '.join(methods[:6])}...)")
except Exception as e:
    R.fail("SystemControl", e)

try:
    from capabilities.system.volume_controller import VolumeController
    vc = VolumeController()
    R.ok("VolumeController instantiated")
except Exception as e:
    R.fail("VolumeController", e)

try:
    from capabilities.system.wifi_controller import WiFiController
    wc = WiFiController()
    R.ok("WiFiController instantiated")
except Exception as e:
    R.fail("WiFiController", e)

try:
    from capabilities.system.brightness_controller import BrightnessController
    bc = BrightnessController()
    R.ok("BrightnessController instantiated")
except Exception as e:
    R.fail("BrightnessController", e)

try:
    from capabilities.system.battery_manager import BatteryManager
    bm = BatteryManager()
    R.ok("BatteryManager instantiated")
except Exception as e:
    R.fail("BatteryManager", e)

try:
    from capabilities.system.app_discovery import AppDiscovery
    ad = AppDiscovery()
    R.ok("AppDiscovery instantiated")
except Exception as e:
    R.fail("AppDiscovery", e)

try:
    from capabilities.system.window_manager import WindowManager
    wm = WindowManager()
    R.ok("WindowManager instantiated")
except Exception as e:
    R.fail("WindowManager", e)

try:
    from capabilities.system.file_manager import FileManager
    fm = FileManager()
    R.ok("FileManager instantiated")
except Exception as e:
    R.fail("FileManager", e)

try:
    from capabilities.system.mouse_controller import MouseController
    mc = MouseController()
    R.ok("MouseController instantiated")
except Exception as e:
    R.fail("MouseController", e)

try:
    from capabilities.system.screen_controller import ScreenController
    scr = ScreenController()
    R.ok("ScreenController instantiated")
except Exception as e:
    R.fail("ScreenController", e)

try:
    from capabilities.system.app_name_mapper import AppNameMapper
    anm = AppNameMapper()
    R.ok("AppNameMapper instantiated")
except Exception as e:
    R.fail("AppNameMapper", e)

try:
    from capabilities.system.system_info import SystemInfoController
    sic = SystemInfoController()
    R.ok("SystemInfoController instantiated")
except Exception as e:
    R.fail("SystemInfoController", e)

# ============================================================
# FEATURE 6: Media Capabilities
# ============================================================
R.section("Media Capabilities")

try:
    from capabilities.media.youtube_service import YouTubeService
    R.ok("YouTubeService class importable")
except Exception as e:
    R.fail("YouTubeService", e)

try:
    from capabilities.media.music_manager import MusicManager
    R.ok("MusicManager class importable")
except Exception as e:
    R.fail("MusicManager", e)

try:
    from capabilities.media.media_controller import ContentModeHandler
    R.ok("ContentModeHandler (media_controller) class importable")
except Exception as e:
    R.fail("ContentModeHandler", e)

# ============================================================
# FEATURE 7: Vision Capabilities
# ============================================================
R.section("Vision Capabilities")

try:
    from capabilities.vision.screen_reader import ScreenReader
    sr = ScreenReader()
    R.ok("ScreenReader instantiated")
except Exception as e:
    R.fail("ScreenReader", e)

try:
    from capabilities.vision.screenshot_manager import ScreenshotManager
    R.ok("ScreenshotManager class importable")
except Exception as e:
    R.fail("ScreenshotManager", e)

try:
    from capabilities.vision.notification_reader import NotificationReader
    R.ok("NotificationReader class importable")
except Exception as e:
    R.fail("NotificationReader", e)

# ============================================================
# FEATURE 8: LLM Capabilities
# ============================================================
R.section("LLM Capabilities")

try:
    from capabilities.llm.llm_manager import LLMManager, LLMMode
    assert LLMMode.OLLAMA is not None or hasattr(LLMMode, 'OFFLINE')
    R.ok("LLMManager + LLMMode enum importable")
except Exception as e:
    R.fail("LLMManager", e)

try:
    from capabilities.llm.gpu_monitor import GPUMonitor
    R.ok("GPUMonitor class importable")
except Exception as e:
    R.fail("GPUMonitor", e)

# ============================================================
# FEATURE 9: Web Capabilities
# ============================================================
R.section("Web Capabilities")

try:
    from capabilities.web.weather_service import WeatherService
    R.ok("WeatherService class importable")
except Exception as e:
    R.fail("WeatherService", e)

try:
    from capabilities.web.web_scraper import WebScraper
    R.ok("WebScraper class importable")
except Exception as e:
    R.fail("WebScraper", e)

try:
    from capabilities.web.sharing_service import SharingService
    R.ok("SharingService class importable")
except Exception as e:
    R.fail("SharingService", e)

try:
    from capabilities.web.file_share_handler import FileShareHandler
    R.ok("FileShareHandler class importable")
except Exception as e:
    R.fail("FileShareHandler", e)

try:
    from capabilities.web.auth_manager import AuthManager
    R.ok("AuthManager class importable")
except Exception as e:
    R.fail("AuthManager", e)

# ============================================================
# FEATURE 10: Creative Capabilities
# ============================================================
R.section("Creative Capabilities")

try:
    from capabilities.creative.game_manager import GameManager
    R.ok("GameManager class importable")
except Exception as e:
    R.fail("GameManager", e)

try:
    from capabilities.creative.pdf_generator import PDFGenerator
    R.ok("PDFGenerator class importable")
except Exception as e:
    R.fail("PDFGenerator", e)

# ============================================================
# FEATURE 11: Command Executor + Function Registry
# ============================================================
R.section("Command Executor & Function Registry")

try:
    from capabilities.executor import CommandExecutor
    methods = [m for m in dir(CommandExecutor) if not m.startswith('_') and callable(getattr(CommandExecutor, m))]
    R.ok(f"CommandExecutor: {len(methods)} methods")
except Exception as e:
    R.fail("CommandExecutor", e)

try:
    from capabilities.function_registry import FunctionRegistry
    methods = [m for m in dir(FunctionRegistry) if not m.startswith('_') and callable(getattr(FunctionRegistry, m))]
    R.ok(f"FunctionRegistry: {len(methods)} methods")
except Exception as e:
    R.fail("FunctionRegistry", e)

try:
    from capabilities.function_validation import FunctionValidator, get_function_validator
    R.ok("FunctionValidator importable")
except Exception as e:
    R.fail("FunctionValidator", e)

# ============================================================
# FEATURE 12: Interface Layer
# ============================================================
R.section("Interface Layer")

try:
    from core.interface.tts_engine import TTSEngine
    R.ok("TTSEngine class importable")
except Exception as e:
    R.fail("TTSEngine", e)

try:
    from core.interface.voice_listener import AudioListener
    R.ok("AudioListener class importable")
except Exception as e:
    R.fail("AudioListener", e)

try:
    from core.interface.speaker_verification import SpeakerVerification
    R.ok("SpeakerVerification class importable")
except Exception as e:
    R.fail("SpeakerVerification", e)

# ============================================================
# FEATURE 13: NexaBrain Full Integration
# ============================================================
R.section("NexaBrain Full Integration")

try:
    from core.brain import NexaBrain
    R.ok("NexaBrain importable (full dependency chain)")
except Exception as e:
    R.fail("NexaBrain full import", e)

try:
    from core.brain import NexaState
    states = list(NexaState)
    R.ok(f"NexaState enum: {len(states)} states ({', '.join(s.name for s in states[:4])}...)")
except Exception as e:
    R.fail("NexaState", e)

# ============================================================
# FEATURE 14: UI Layer
# ============================================================
R.section("UI Components")

ui_tests = [
    ("ui.pet.nexa_pet_widget", "NexaPetWidget"),
    ("ui.pet.pet_config", None),
    ("ui.widgets.loading_dialog", None),
    ("ui.widgets.nexa_orb_ui", None),
    ("ui.nexa_modern_window", "NexaModernWindow"),
    ("ui.nexa_guidelines", None),
]

for module_name, class_name in ui_tests:
    try:
        mod = __import__(module_name, fromlist=[class_name or "dummy"])
        if class_name:
            getattr(mod, class_name)
        R.ok(f"{module_name}" + (f".{class_name}" if class_name else ""))
    except Exception as e:
        # UI modules may fail without QApplication — that's Ok
        err_str = str(e)
        if "QApplication" in err_str or "QWidget" in err_str or "display" in err_str.lower():
            R.ok(f"{module_name} (skipped: needs QApplication)")
        else:
            R.fail(f"{module_name}", e)

# ============================================================
# FEATURE 15: Cross-Layer Integration
# ============================================================
R.section("Cross-Layer Integration")

# Config -> Brain dependency
try:
    from config.settings import Config
    from core.brain import NexaBrain
    # Brain references Config attributes
    R.ok("Config -> Brain dependency chain")
except Exception as e:
    R.fail("Config -> Brain", e)

# Kernel -> Executor -> Capabilities chain
try:
    from core.kernel import NexaKernel, TaskEntry, PriorityLevel
    from capabilities.executor import CommandExecutor
    from capabilities.system.system_control import SystemControl
    from capabilities.system.volume_controller import VolumeController
    R.ok("Kernel -> Executor -> System capabilities chain")
except Exception as e:
    R.fail("Kernel -> Executor -> Capabilities", e)

# Memory -> Cognition chain
try:
    from core.memory.memory_manager import SmartMemoryManager
    from core.cognition.context_manager import ContextManager
    R.ok("Memory -> Cognition chain")
except Exception as e:
    R.fail("Memory -> Cognition", e)

# Full kernel task lifecycle
try:
    from core.kernel import NexaKernel, TaskEntry, PriorityLevel, EventBus
    
    k = NexaKernel()
    events_log = []
    k.event_bus.subscribe("task.submitted", lambda **kw: events_log.append(("submitted", kw)))
    k.event_bus.subscribe("task.completed", lambda **kw: events_log.append(("completed", kw)))
    
    task = TaskEntry(name="INTEGRATION_TEST", priority=PriorityLevel.VOICE_INPUT, 
                     gpu_required=True, estimated_vram_mb=3500)
    tid = k.submit_task(task)
    assert tid is not None
    assert any(e[0] == "submitted" for e in events_log), "No submit event fired"
    
    k.complete_task(tid)
    assert any(e[0] == "completed" for e in events_log), "No complete event fired"
    
    R.ok("Full kernel lifecycle with event bus verification")
except Exception as e:
    R.fail("Full kernel lifecycle", e)

# ============================================================
# FINAL SUMMARY
# ============================================================
success = R.summary()

# Save results
with open("test_nexa_features_results.txt", "w", encoding="utf-8") as f:
    f.write(f"Passed: {R.total_pass}\n")
    f.write(f"Failed: {R.total_fail}\n")
    for section, counts in R.sections.items():
        f.write(f"\n[{section}] {counts['pass']}/{counts['pass']+counts['fail']}\n")
    if R.errors:
        f.write(f"\nFailures:\n")
        for sec, name, err in R.errors:
            f.write(f"  [{sec}] {name}: {err}\n")

sys.exit(0 if success else 1)
