"""
Nexa Brain - Central Intelligence and Orchestration
Manages reasoning, decision-making, and component coordination.
"""

import logging
import threading
import queue
import time
import json
import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

# import google.generativeai as genai  # REMOVED: Migrated to Llama 3.1 8B

from .config import Config
from .context_manager import ContextManager
from .executor import CommandExecutor
from .listener import AudioListener
from .tts import TTSEngine
from .llm_manager import LLMManager, LLMMode

# Optional: Coqui TTS for cloned voice
try:
    from .tts_coqui import CoquiTTSEngine
    COQUI_AVAILABLE = True
except ImportError:
    COQUI_AVAILABLE = False

# Import refactored utility modules
from .text_processing import TextProcessor, get_text_processor
from .function_validation import FunctionValidator, get_function_validator
from .command_detection import CommandDetector, get_command_detector
from .clarification_handler import ClarificationHandler, get_clarification_handler
from .response_cache import ResponseCache, get_response_cache
from .conversation_history import ConversationHistoryBuilder, get_history_builder
from .reference_resolver import ReferenceResolver, get_reference_resolver

# Import input validator (optional, can be disabled via feature flag)
try:
    from .input_validator import InputValidator
    INPUT_VALIDATOR_AVAILABLE = True
except ImportError:
    INPUT_VALIDATOR_AVAILABLE = False
    InputValidator = None

# Import conditional handler (optional, can be disabled via feature flag)
try:
    from .conditional_handler import ConditionalHandler
    CONDITIONAL_HANDLER_AVAILABLE = True
except ImportError:
    CONDITIONAL_HANDLER_AVAILABLE = False
    ConditionalHandler = None

# Import dynamic preprocessor (optional, can be disabled via feature flag)
try:
    from .dynamic_preprocessor import DynamicPreprocessor, PreprocessingResult
    DYNAMIC_PREPROCESSOR_AVAILABLE = True
except ImportError:
    DYNAMIC_PREPROCESSOR_AVAILABLE = False
    DynamicPreprocessor = None
    PreprocessingResult = None

# Import speaker enrollment (optional)
try:
    from .speaker_enrollment import SpeakerEnrollment
    SPEAKER_ENROLLMENT_AVAILABLE = True
except ImportError:
    SPEAKER_ENROLLMENT_AVAILABLE = False
    SpeakerEnrollment = None

# Import Companion Mode - Phase 28: Thinking Feedback (optional)
try:
    from .companion import ThinkingFeedback, init_thinking_feedback
    THINKING_FEEDBACK_AVAILABLE = True
except ImportError:
    THINKING_FEEDBACK_AVAILABLE = False
    ThinkingFeedback = None
    init_thinking_feedback = None

# Import Companion Mode - Phase 29: Proactive Engagement (optional)
try:
    from .companion import (
        IdleMonitor, IdleState, init_idle_monitor, get_idle_monitor,
        ProactiveEngine, init_proactive_engine, get_proactive_engine,
        PatternLearner, init_pattern_learner, get_pattern_learner
    )
    PROACTIVE_AVAILABLE = True
except ImportError:
    PROACTIVE_AVAILABLE = False
    IdleMonitor = None
    init_idle_monitor = None
    get_idle_monitor = None
    ProactiveEngine = None
    init_proactive_engine = None
    get_proactive_engine = None
    PatternLearner = None
    init_pattern_learner = None
    get_pattern_learner = None

logger = logging.getLogger(__name__)


class NexaState(Enum):
    """Nexa's operational states."""
    IDLE = "idle"
    LISTENING = "listening"
    RECOGNIZING = "recognizing"  # NEW: Speaker enrollment/verification state
    THINKING = "thinking"
    SPEAKING = "speaking"
    EXECUTING = "executing"
    CONTENT_MODE = "content_mode"  # NEW: Dedicated content editing & PDF generation
    ERROR = "error"


class NexaBrain:
    """
    The central orchestration hub for Nexa.
    Manages all AI reasoning, component coordination, and state transitions.
    """
    
    def __init__(self, config: Config):
        """
        Initialize Nexa Brain with configuration.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.state = NexaState.IDLE
        self.running = False
        
        # Initialize components
        self.context_manager = ContextManager(config)
        self.gpu_monitor = None  # Will be set by main.py via set_gpu_monitor()
        self.executor = CommandExecutor(config, self.context_manager, self.gpu_monitor)
        self.listener = AudioListener(config)
        
        # Initialize TTS Engine based on config
        # Options: 'kokoro' (default) or 'coqui' (cloned voice, better emotions)
        self.tts = self._create_tts_engine(config)
        
        # Set brain reference in executor (for Content Mode access)
        self.executor.brain = self
        
        # Initialize LLM Manager (Phase 24: 100% API-Free Llama 3.1 8B)
        # Pass executor for dynamic function catalog access
        self.llm_manager = LLMManager(config, executor=self.executor)
        
        # Connect llm_manager to screen_reader for offline vision (disabled until Phase 23)
        self.executor.screen_reader.llm_manager = self.llm_manager
        
        # Register LLM mode change callback (for verbal announcements)
        self.llm_manager.register_mode_callback(self._on_llm_mode_changed)
        
        # Initialize refactored utility modules
        self.text_processor = get_text_processor()
        self.function_validator = get_function_validator(self.executor, self.config)
        self.command_detector = get_command_detector()
        self.clarification_handler = get_clarification_handler(self.context_manager, self.executor)
        # Pass IntentState to response_cache for unified follow-up detection
        self.response_cache = get_response_cache(
            intent_state=self.context_manager.intent_state
        )
        self.history_builder = get_history_builder()
        self.reference_resolver = get_reference_resolver(self.context_manager, self.executor)
        
        # Initialize speaker enrollment (optional, for voice enrollment)
        self.speaker_enrollment = None
        self._setup_speaker_enrollment()
        
        # Initialize input validator (optional, can be disabled)
        # Feature flag: Set to False to disable edge case validation
        self.enable_input_validation = True
        self.input_validator = None
        if INPUT_VALIDATOR_AVAILABLE and self.enable_input_validation:
            self.input_validator = InputValidator()
            logger.info("✅ Input validator enabled (edge case handling)")
        else:
            logger.info("⚠️ Input validator disabled")
        
        # Initialize conditional handler (optional, can be disabled)
        # Feature flag: Set to False to disable conditional command handling
        self.enable_conditional_commands = True
        self.conditional_handler = None
        if CONDITIONAL_HANDLER_AVAILABLE and self.enable_conditional_commands:
            self.conditional_handler = ConditionalHandler(executor=self.executor)
            logger.info("✅ Conditional handler enabled (if-then logic)")
        else:
            logger.info("⚠️ Conditional handler disabled")
        
        # Initialize dynamic preprocessor (optional, can be disabled)
        # Feature flag: Set to False to disable dynamic preprocessing
        self.enable_dynamic_preprocessing = True
        self.dynamic_preprocessor = None
        if DYNAMIC_PREPROCESSOR_AVAILABLE and self.enable_dynamic_preprocessing:
            self.dynamic_preprocessor = DynamicPreprocessor(context_manager=self.context_manager)
            logger.info("✅ Dynamic preprocessor enabled (multi-step, pronouns, ambiguity detection)")
        else:
            logger.info("⚠️ Dynamic preprocessor disabled")
        
        # Initialize Companion Mode - Phase 28: Thinking Feedback
        # Provides immediate acknowledgment ("On it!", "Got it!") when processing starts
        # Feature flag: Set to False to disable thinking feedback
        self.enable_thinking_feedback = True
        self.thinking_feedback = None
        if THINKING_FEEDBACK_AVAILABLE and self.enable_thinking_feedback:
            # Create a wrapper function for TTS that matches expected signature
            # Signature: (text, ducking, silent) -> None
            def speak_for_thinking(text: str, ducking: bool = True, silent: bool = False):
                # silent=True keeps NEXA in THINKING state visually
                self.tts.speak(text, blocking=True, ducking=ducking, silent=silent)
            
            self.thinking_feedback = init_thinking_feedback(
                speak_func=speak_for_thinking,
                emit_message_func=self._emit_message,
                enabled=True
            )
            logger.info("✅ Thinking feedback enabled (Phase 28 - Companion Mode)")
        else:
            logger.info("⚠️ Thinking feedback disabled")
        
        # Initialize Companion Mode - Phase 29: Proactive Engagement
        # Enables idle detection and proactive suggestions
        # Feature flag: Set to False to disable proactive features
        self.enable_proactive = True
        self.idle_monitor = None
        self.proactive_engine = None
        self.pattern_learner = None
        self._proactive_check_interval = 60.0  # Check every 60 seconds
        self._last_proactive_check = 0.0
        
        if PROACTIVE_AVAILABLE and self.enable_proactive:
            try:
                # Initialize pattern learner first (stores learned patterns)
                self.pattern_learner = init_pattern_learner()
                
                # Initialize idle monitor (tracks user activity)
                self.idle_monitor = init_idle_monitor()
                
                # Initialize proactive engine with LLM generator
                self.proactive_engine = init_proactive_engine()
                
                # Set LLM generator for natural message generation
                if self.proactive_engine and self.llm_manager:
                    def llm_generator(prompt: str) -> str:
                        """Simple LLM wrapper for proactive engine."""
                        try:
                            # Use raw prompt mode for proactive messages
                            result = self.llm_manager._generate_with_llama(prompt, use_raw_prompt=True)
                            return result or ""
                        except Exception as e:
                            logger.error(f"Proactive LLM generation failed: {e}")
                            return ""
                    self.proactive_engine.set_llm_generator(llm_generator)
                    logger.info("✅ Proactive engine LLM generator connected")
                
                # Set up callbacks
                if self.idle_monitor:
                    self.idle_monitor.set_proactive_opportunity_callback(self._on_proactive_opportunity)
                
                logger.info("✅ Proactive engagement enabled (Phase 29 - Companion Mode)")
            except Exception as e:
                logger.warning(f"⚠️ Proactive initialization failed: {e}")
        else:
            logger.info("⚠️ Proactive engagement disabled")
        
        # Listening timeout timer - checks every 5 seconds if we should go IDLE
        self._listening_timeout_timer = None  # QTimer, set in start()
        self._listening_start_time = 0.0  # When LISTENING state started
        self._listening_timeout_duration = 60.0  # Seconds until timeout
        
        # Proactive check timer - checks every 60 seconds for proactive opportunities
        self._proactive_timer = None  # QTimer, set in start()
        self._proactive_timer_start = 0.0  # When proactive timer started
        self._proactive_interval = 60.0  # Seconds between proactive checks
        
        # Communication queues
        self.transcription_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.tts_queue = queue.Queue()
        
        # Event callbacks for UI
        self.state_callbacks = []
        self.message_callbacks = []
        self.audio_level_callbacks = []  # NEW: Callbacks for audio levels
        self.mode_callbacks = []  # NEW: Callbacks for mode changes (online/offline)
        
        # PHASE 3: Direct function call cache for instant responses
        # Maps normalized query patterns to executor functions for 0s response time
        self.quick_response_cache = {
            # Time queries
            r'what.*time': lambda: self.executor.get_current_time(),
            r'current.*time': lambda: self.executor.get_current_time(),
            r'tell.*time': lambda: self.executor.get_current_time(),
            
            # Battery queries
            r'battery.*level': lambda: self.executor.get_battery_percentage(),
            r'battery.*status': lambda: self.executor.get_battery_status(),
            r'how.*battery': lambda: self.executor.get_battery_status(),
            
            # Volume queries
            r'current.*volume': lambda: self.executor.get_current_volume(),
            r'volume.*level': lambda: self.executor.get_current_volume(),
            r'what.*volume': lambda: self.executor.get_current_volume(),
            
            # Brightness queries
            r'current.*brightness': lambda: self.executor.get_current_brightness(),
            r'brightness.*level': lambda: self.executor.get_current_brightness(),
            r'what.*brightness': lambda: self.executor.get_current_brightness(),
            
            # WiFi queries
            r'wifi.*status': lambda: self.executor.get_wifi_status(),
            r'internet.*connect': lambda: self.executor.get_wifi_status(),
        }
        
        # Processing thread
        self.brain_thread: Optional[threading.Thread] = None
        
        # Connect music manager signals for auto-announcements
        self._connect_music_signals()
        
        # PERFORMANCE: Full LLM warm-up with system prompt (first command = instant!)
        # This runs AFTER brain is fully initialized so function catalog is ready
        self.llm_manager.full_warmup()
        
        logger.info("Nexa Brain initialized successfully")
    
    def _connect_music_signals(self):
        """Connect music manager signals for auto-announcements."""
        try:
            music_manager = self.executor.music_manager
            
            # Connect auto-advance signal to announce track changes (only for auto-advance, not user requests)
            music_manager.on_auto_advance.connect(self._announce_song_change)
            
            logger.info("✅ Music auto-announcements enabled")
        except Exception as e:
            logger.warning(f"⚠️ Failed to connect music signals: {e}")
    
    def _announce_song_change(self, song_name: str):
        """
        Announce song change when music auto-advances.
        
        Args:
            song_name: Formatted song name (e.g., "Title by Artist")
        """
        try:
            # Only announce if auto-advance (don't re-announce user-requested songs)
            announcement = f"Now playing {song_name}"
            logger.info(f"🎵 Auto-announcement: {announcement}")
            
            # Use TTS to announce (without ducking music too much)
            self.tts.speak(announcement)
        except Exception as e:
            logger.error(f"❌ Failed to announce song change: {e}")
    
    def _create_tts_engine(self, config):
        """
        Factory method to create the appropriate TTS engine based on config.
        
        Options:
        - 'kokoro': Default, fast, lightweight (82M params)
        - 'coqui': Cloned af_heart voice via XTTS, better emotional range (1.8GB model)
        
        Set TTS_ENGINE environment variable or config.tts_engine to switch.
        
        Returns:
            TTSEngine or CoquiTTSEngine instance
        """
        engine_type = getattr(config, 'tts_engine', 'kokoro').lower()
        
        if engine_type == 'coqui':
            if COQUI_AVAILABLE:
                # Check if reference audio exists
                ref_audio = config.voice_dir / "af_heart_reference.wav"
                if ref_audio.exists():
                    logger.info("🎤 Using Coqui XTTS with cloned af_heart voice")
                    return CoquiTTSEngine(config)
                else:
                    logger.warning(f"⚠️ Coqui reference audio not found: {ref_audio}")
                    logger.info("   Run: python test_coqui_clone.py to generate it")
                    logger.info("   Falling back to Kokoro TTS")
                    return TTSEngine(config)
            else:
                logger.warning("⚠️ Coqui TTS not installed, falling back to Kokoro")
                logger.info("   Install with: uv pip install coqui-tts")
                return TTSEngine(config)
        else:
            # Default: Kokoro
            logger.info("🎤 Using Kokoro TTS with af_heart voice")
            return TTSEngine(config)
    
    def _setup_speaker_enrollment(self):
        """Initialize speaker enrollment system (optional)."""
        if not SPEAKER_ENROLLMENT_AVAILABLE:
            logger.debug("Speaker enrollment module not available (optional feature)")
            return
        
        try:
            # Only initialize if speaker verification is enabled
            if not getattr(self.config, 'speaker_verification_enabled', False):
                logger.debug("Speaker enrollment disabled (speaker verification not enabled)")
                return
            
            # Check if listener has speaker verifier
            if not hasattr(self.listener, 'speaker_verifier') or self.listener.speaker_verifier is None:
                logger.warning("⚠️ Speaker verification not initialized in listener")
                return
            
            logger.info("🔄 Setting up speaker enrollment system...")
            
            # Create enrollment instance with required components
            self.speaker_enrollment = SpeakerEnrollment(
                speaker_verification=self.listener.speaker_verifier,
                audio_listener=self.listener,
                tts_engine=self.tts
            )
            
            # Connect enrollment to listener (so listener can process enrollment audio)
            self.listener.speaker_enrollment = self.speaker_enrollment
            
            logger.info("✅ Speaker enrollment ready!")
            
        except Exception as e:
            logger.error(f"Failed to setup speaker enrollment: {e}")
            logger.warning("   Continuing without enrollment capability")
            self.speaker_enrollment = None
    
    def switch_tts_engine(self, engine_type: str) -> bool:
        """
        Switch TTS engine at runtime.
        
        Args:
            engine_type: 'kokoro' or 'coqui'
            
        Returns:
            True if switch successful, False otherwise
        """
        engine_type = engine_type.lower().strip()
        
        if engine_type not in ('kokoro', 'coqui'):
            logger.error(f"❌ Unknown TTS engine: {engine_type}. Use 'kokoro' or 'coqui'")
            return False
        
        # Save callbacks from current engine
        start_cb = self.tts.speaking_start_callback
        end_cb = self.tts.speaking_end_callback
        text_cb = self.tts.response_text_callback
        music_mgr = getattr(self.tts, 'music_manager', None)
        
        # Cleanup old engine
        try:
            self.tts.cleanup()
        except:
            pass
        
        # Update config
        self.config.tts_engine = engine_type
        
        # Create new engine
        self.tts = self._create_tts_engine(self.config)
        
        # Restore callbacks
        self.tts.speaking_start_callback = start_cb
        self.tts.speaking_end_callback = end_cb
        self.tts.response_text_callback = text_cb
        if music_mgr:
            self.tts.music_manager = music_mgr
        
        logger.info(f"✅ Switched to {engine_type} TTS engine")
        return True
    
    def get_tts_engine_name(self) -> str:
        """Get the name of the current TTS engine."""
        if hasattr(self.tts, '__class__'):
            return self.tts.__class__.__name__
        return "Unknown"
    
    def _is_content_mode_active(self) -> bool:
        """
        Check if Content Mode window is currently open and visible.
        
        Returns:
            bool: True if Content Mode is active, False otherwise
        """
        # If exit is in progress, consider Content Mode inactive
        if hasattr(self.executor, '_content_mode_exiting') and self.executor._content_mode_exiting:
            return False
        
        return (hasattr(self.executor, 'content_window') 
                and self.executor.content_window is not None
                and self.executor.content_window.isVisible())
    
    def _speak_enrollment_prompt(self, text: str):
        """
        Callback for enrollment system to speak prompts.
        
        Args:
            text: Text to speak
        """
        logger.info(f"📢 Enrollment prompt: {text}")
        self._speak_response(text)
    
    def _on_enrollment_complete(self, success: bool, profile_name: str):
        """
        Callback when enrollment process completes.
        
        Args:
            success: Whether enrollment succeeded
            profile_name: Name of the enrolled profile
        """
        if success:
            response = f"Voice profile '{profile_name}' enrolled successfully! I will now recognize only your voice."
            logger.info(f"✅ {response}")
        else:
            response = "Voice enrollment failed. Please try again or check the logs for details."
            logger.error(f"❌ {response}")
        
        self._emit_message("nexa", response)
        self._speak_response(response)
    
    def _check_screen_privacy_consent(self) -> bool:
        """
        Check if user has given consent for screen analysis.
        First-time users will be asked for consent.
        
        Returns:
            True if consent given, False if consent needed
        """
        # Check if user has already given consent
        consent = self.context_manager.user_preferences.get('screen_analysis_consent', None)
        
        if consent is None:
            # First time - need to ask for consent
            return False
        
        return consent
    
    def _grant_screen_privacy_consent(self):
        """Grant screen analysis consent and save to preferences."""
        self.context_manager.user_preferences['screen_analysis_consent'] = True
        self.context_manager._save_preferences()
        logger.info("✅ Screen analysis consent granted")
    
    def start(self):
        """Start Nexa Brain and all sub-components."""
        if self.running:
            logger.warning("Brain already running")
            return
        
        self.running = True
        
        # Connect music manager to listener for ducking support
        self.listener.music_manager = self.executor.music_manager
        logger.debug("✅ Music ducking connected to listener")
        
        # Connect intent state to listener for wake word bypass on follow-ups
        self.listener.intent_state = self.context_manager.intent_state
        logger.debug("✅ Intent state connected to listener")
        
        # Connect music manager to TTS for ducking during speech
        self.tts.music_manager = self.executor.music_manager
        logger.debug("✅ Music ducking connected to TTS")
        
        # Connect TTS state callbacks to track RESPONDING state accurately
        self.tts.speaking_start_callback = self._on_tts_start
        self.tts.speaking_end_callback = self._on_tts_end
        logger.debug("✅ TTS state callbacks connected")
        
        # Start processing thread
        self.brain_thread = threading.Thread(
            target=self._processing_loop,
            name="NexaBrainThread",
            daemon=True
        )
        self.brain_thread.start()
        
        # Connect listener to transcription queue
        self.listener.set_transcription_callback(self._on_transcription)
        
        # Connect listener to audio level callback (for UI updates)
        self.listener.set_audio_level_callback(self._on_audio_level_update)
        
        # Connect listener state callback (for enrollment/verification states)
        self.listener.state_callback = self._on_listener_state_change
        
        # Connect speaker rejection callback (for voice authentication feedback)
        self.listener.speaker_rejection_callback = self._on_speaker_rejected
        
        # Start listening timeout timer (checks every 5 seconds)
        from PySide6.QtCore import QTimer
        self._listening_timeout_timer = QTimer()
        self._listening_timeout_timer.timeout.connect(self._check_listening_timeout)
        self._listening_timeout_timer.start(5000)  # Check every 5 seconds
        logger.info("⏱️ Listening timeout timer started (60s timeout, checks every 5s)")
        
        # Start proactive check timer (checks every 60 seconds)
        if self.enable_proactive and PROACTIVE_AVAILABLE:
            import time
            self._proactive_timer = QTimer()
            self._proactive_timer.timeout.connect(self._check_proactive_opportunity)
            self._proactive_timer.start(int(self._proactive_interval * 1000))
            self._proactive_timer_start = time.time()
            logger.info(f"💜 Proactive timer started ({self._proactive_interval:.0f}s interval)")
        
        logger.info("Nexa Brain started")
        self._change_state(NexaState.IDLE)
        
        # MODE AWARENESS: Announce current mode on startup
        current_mode = self.llm_manager.current_mode.value if self.llm_manager.current_mode else "unknown"
        mode_display = "online" if current_mode == "online" else "offline"
        
        logger.info(f"🤖 Running in {mode_display.upper()} mode")
        
        # Announce limitations if in offline mode
        if mode_display == "offline":
            logger.info("⚠️  Offline mode limitations:")
            logger.info("   • No vision/screenshot analysis")
            logger.info("   • Enhanced NLP (Llama 3.1 8B)")
            logger.info("   • Advanced reasoning with lower hallucinations")
            logger.info("💡 Switch to online mode for internet-dependent features (vision, web search, weather)")
    
    def shutdown(self):
        """Gracefully shutdown all components and free GPU memory."""
        logger.info("Initiating Nexa Brain shutdown...")
        logger.info("🎮 Unloading ALL AI models to free GPU VRAM for games/other apps...")
        self.running = False
        
        # Stop components and unload GPU models
        logger.info("🧹 Stopping listener and unloading Whisper/DeepFilterNet from GPU...")
        self.listener.stop()  # This now unloads Whisper, DeepFilterNet, Silero VAD
        
        logger.info("🧹 Stopping TTS and unloading Kokoro model...")
        self.tts.stop()
        if hasattr(self.tts, 'cleanup'):
            self.tts.cleanup()  # Unload Kokoro model
        
        # Cleanup speaker verification if enabled
        if hasattr(self.listener, 'speaker_verifier') and self.listener.speaker_verifier:
            if hasattr(self.listener.speaker_verifier, 'cleanup'):
                logger.info("🧹 Unloading SpeechBrain model from GPU...")
                self.listener.speaker_verifier.cleanup()
        
        # === CRITICAL: Unload Ollama/Llama model ===
        if hasattr(self, 'llm_manager') and self.llm_manager:
            logger.info("🧹 Unloading Llama 3.1 8B from Ollama...")
            self.llm_manager.cleanup()
        
        # Wait for thread to finish
        if self.brain_thread and self.brain_thread.is_alive():
            self.brain_thread.join(timeout=2.0)
        
        # Final CUDA cache clear
        try:
            import torch
            import gc
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                logger.info("✅ All GPU VRAM freed - safe to run games!")
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Error in final CUDA cleanup: {e}")
        
        logger.info("🎮 Nexa Brain shutdown complete - GPU memory released!")
    
    def _processing_loop(self):
        """Main processing loop for handling transcriptions and generating responses."""
        logger.info("Brain processing loop started")
        
        while self.running:
            try:
                # Get transcription with timeout
                transcription = self.transcription_queue.get(timeout=0.5)
                
                if transcription:
                    logger.info(f"🤔 Processing: \"{transcription}\"")
                    
                    # Clear any accumulated items in queue (prevent stale commands from piling up)
                    discarded_count = 0
                    while not self.transcription_queue.empty():
                        try:
                            old_item = self.transcription_queue.get_nowait()
                            discarded_count += 1
                            logger.warning(f"⏭️ Skipped queued item: \"{old_item}\"")
                        except queue.Empty:
                            break
                    
                    if discarded_count > 0:
                        logger.info(f"🗑️ Cleared {discarded_count} stale queue items")
                    
                    self._process_user_input(transcription)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in processing loop: {e}", exc_info=True)
                self._change_state(NexaState.ERROR)
    
    def _on_transcription(self, text: str):
        """
        Callback for when audio is transcribed.
        Processes all transcriptions - no wake word required.
        
        Args:
            text: Transcribed text from user
        """
        if text and text.strip():
            import time
            
            # Reset proactive listening flag when user speaks
            # This ensures the 30s proactive timeout stops
            if self.listener and self.listener.proactive_listening:
                logger.info("💜 User responded to proactive - resetting proactive mode")
                self.listener.proactive_listening = False
            
            # Log timer reset
            logger.info(f"🎤 User spoke: '{text[:50]}{'...' if len(text) > 50 else ''}' - LISTENING timer RESET to {self._listening_timeout_duration:.0f}s")
            
            logger.debug(f"📥 Received: {text}")
            
            # Process ALL transcriptions without wake word requirement
            text_lower = text.lower()
            
            # Handle pause/resume commands
            if "stop listening" in text_lower or "pause listening" in text_lower:
                logger.info("🛑 User requested to stop listening")
                self.listener.pause_for_user()
                response = "I've stopped listening. Say 'start listening' when you need me again."
                self._emit_message("nexa", response)
                self._speak_response(response)
                return
            
            if "start listening" in text_lower or "resume listening" in text_lower:
                logger.info("▶️ User requested to start listening")
                self.listener.resume_for_user()
                response = "I'm listening again. How can I help?"
                self._emit_message("nexa", response)
                self._speak_response(response)
                return
            
            # ===== WAKE WORD CONTROL =====
            # Enable/disable wake word mode
            if "enable wake word" in text_lower or "turn on wake word" in text_lower or "activate wake word" in text_lower:
                logger.info("🔔 User requested to enable wake word mode")
                self.listener.enable_wake_word(True)
                response = "Wake word mode enabled. Say 'Nexa' before each command."
                self._emit_message("nexa", response)
                self._speak_response(response)
                return
            
            if "disable wake word" in text_lower or "turn off wake word" in text_lower or "deactivate wake word" in text_lower or "always listen" in text_lower:
                logger.info("🔊 User requested to disable wake word mode")
                self.listener.enable_wake_word(False)
                response = "Wake word mode disabled. I'll listen to all your commands directly."
                self._emit_message("nexa", response)
                self._speak_response(response)
                return
            
            # ===== SPEAKER ENROLLMENT COMMANDS =====
            # Handle voice enrollment commands
            if self.speaker_enrollment:
                # Enroll new voice profile
                if "enroll my voice" in text_lower or "set up voice recognition" in text_lower or "register my voice" in text_lower:
                    logger.info("🎤 User requested voice enrollment")
                    response = "Starting voice enrollment. I'll guide you through the process."
                    self._emit_message("nexa", response)
                    self._speak_response(response)
                    # Start enrollment process (will use TTS callbacks)
                    self.speaker_enrollment.start_enrollment()
                    return
                
                # Check if currently enrolling (process enrollment audio)
                if self.speaker_enrollment.is_enrolling:
                    logger.debug(f"📝 Enrollment in progress - current step: {self.speaker_enrollment.current_prompt_index + 1}/{self.speaker_enrollment.num_samples}")
                    # The enrollment system handles its own audio capture via listener
                    # Just ignore transcriptions during enrollment (except cancel command)
                    if "cancel" in text_lower or "stop enrollment" in text_lower:
                        logger.info("🛑 User cancelled enrollment")
                        self.speaker_enrollment.cancel_enrollment()
                        response = "Voice enrollment cancelled."
                        self._emit_message("nexa", response)
                        self._speak_response(response)
                    return
                
                # Reset/delete voice profile
                if "reset voice profile" in text_lower or "delete voice profile" in text_lower or "remove my voice" in text_lower:
                    logger.info("🗑️ User requested voice profile deletion")
                    if self.listener.speaker_verifier:
                        success = self.listener.speaker_verifier.delete_profile("user_primary")
                        if success:
                            response = "Voice profile deleted. You'll need to enroll again to use speaker verification."
                        else:
                            response = "Failed to delete voice profile. It may not exist."
                    else:
                        response = "Speaker verification is not enabled."
                    self._emit_message("nexa", response)
                    self._speak_response(response)
                    return
                
                # Check voice profile status
                if "check voice profile" in text_lower or "voice profile status" in text_lower:
                    logger.info("📊 User requested voice profile status")
                    self.speaker_enrollment.check_voice_profile("user_primary")
                    return
                
                # NEW: Add voice samples to existing profile
                if "add voice samples" in text_lower or "improve voice recognition" in text_lower or "add more samples" in text_lower:
                    logger.info("🔄 User requested to add voice samples")
                    response = "I'll add more samples to your existing voice profile to improve recognition."
                    self._emit_message("nexa", response)
                    self._speak_response(response)
                    # Add 3 new samples to existing profile
                    self.speaker_enrollment.add_voice_samples(num_new_samples=3)
                    return
                
                # NEW: Re-enroll (replace existing profile)
                if "re-enroll voice" in text_lower or "re-enroll my voice" in text_lower or "redo voice enrollment" in text_lower:
                    logger.info("🔄 User requested to re-enroll voice (replace existing)")
                    # Delete old profile first
                    if self.listener.speaker_verifier:
                        self.listener.speaker_verifier.delete_profile("user_primary")
                    response = "I'll create a new voice profile from scratch. This will replace your existing profile."
                    self._emit_message("nexa", response)
                    self._speak_response(response)
                    # Start fresh enrollment
                    self.speaker_enrollment.start_enrollment()
                    return
                
                # Disable speaker verification
                if "disable speaker verification" in text_lower or "turn off voice recognition" in text_lower:
                    logger.info("🔇 User requested to disable speaker verification")
                    if self.listener.speaker_verifier:
                        self.listener.speaker_verifier.enabled = False
                        response = "Speaker verification disabled. I'll respond to all voices now."
                    else:
                        response = "Speaker verification was not enabled."
                    self._emit_message("nexa", response)
                    self._speak_response(response)
                    return
                
                # Enable speaker verification
                if "enable speaker verification" in text_lower or "turn on voice recognition" in text_lower:
                    logger.info("🔊 User requested to enable speaker verification")
                    if self.listener.speaker_verifier:
                        if self.listener.speaker_verifier.has_profile("user_primary"):
                            self.listener.speaker_verifier.enabled = True
                            response = "Speaker verification enabled. I'll only respond to your voice."
                        else:
                            response = "Please enroll your voice first by saying 'enroll my voice'."
                    else:
                        response = "Speaker verification is not available. Check configuration."
                    self._emit_message("nexa", response)
                    self._speak_response(response)
                    return
            # ===== END SPEAKER ENROLLMENT COMMANDS =====
            
            # Process the transcription
            cleaned_text = text.strip()
            
            # Prevent queue buildup: Skip if already processing something (except commands)
            if self.state == NexaState.THINKING or self.state == NexaState.EXECUTING:
                logger.warning(f"⏸️ Already busy - ignoring: '{cleaned_text}'")
                return
            
            # If we're in IDLE and received a valid transcription (wake word passed),
            # wake up with a natural response and transition to LISTENING
            if self.state == NexaState.IDLE:
                logger.info("🎙️ Wake word detected while IDLE - waking up!")
                self._change_state(NexaState.LISTENING)
                
                # Set listener to active mode (no wake word needed now)
                if self.listener:
                    self.listener.set_passive_mode(False)
                    self.listener.record_valid_command()
                
                # If wake word was said alone (no command), give a wake-up response
                if not cleaned_text or cleaned_text.lower() in ['nexa', 'next', 'necks', 'hey nexa']:
                    import random
                    wake_responses = [
                        "I'm here! What do you need?",
                        "Yes? I'm listening.",
                        "Hey! What can I do for you?",
                        "I'm awake! How can I help?",
                        "Right here! What's up?",
                    ]
                    response = random.choice(wake_responses)
                    logger.info(f"💬 Wake-up response: {response}")
                    self._emit_message("nexa", response)
                    self._speak_response(response)
                    return  # Don't queue empty/wake-word-only text
            
            logger.debug(f"📤 Queued: \"{cleaned_text}\"")
            self.transcription_queue.put(cleaned_text)
            self._emit_message("user", cleaned_text)
    
    def _on_audio_level_update(self, audio_level: float, confidence: float, is_listening: bool):
        """
        Callback for audio level updates from listener.
        Forwards to UI callbacks for visualization.
        
        Args:
            audio_level: Audio amplitude (0.0 to 1.0)
            confidence: Voice detection confidence (0.0 to 1.0)
            is_listening: Whether actively listening
        """
        # Forward to all registered UI callbacks
        for callback in self.audio_level_callbacks:
            try:
                callback(audio_level, confidence, is_listening)
            except Exception as e:
                logger.debug(f"Audio level callback error: {e}")
    
    def _on_listener_state_change(self, state: str, message: str = ""):
        """
        Callback for listener state changes (e.g., RECOGNIZING during enrollment).
        
        Args:
            state: State name (e.g., "recognizing", "listening", "wake_word")
            message: Optional descriptive message
        """
        try:
            # Handle wake_word state specially - play acknowledgment sound AND update pet
            if state.lower() == "wake_word":
                logger.info("🔔 Wake word detected - Nexa is listening...")
                
                # First, set state to LISTENING so pet updates
                self._set_state(NexaState.LISTENING)
                
                # Play a quick TTS acknowledgment to let user know Nexa heard them
                try:
                    self.speak("Yes?", skip_thinking=True)  # Quick acknowledgment
                except Exception as tts_error:
                    logger.debug(f"Could not play wake word acknowledgment: {tts_error}")
                
                return
            
            # Convert string to NexaState enum
            state_map = {
                "idle": NexaState.IDLE,
                "listening": NexaState.LISTENING,
                "recognizing": NexaState.RECOGNIZING,
                "thinking": NexaState.THINKING,
                "speaking": NexaState.SPEAKING,
                "executing": NexaState.EXECUTING,
                "error": NexaState.ERROR
            }
            
            nexa_state = state_map.get(state.lower(), NexaState.IDLE)
            logger.debug(f"🔄 Listener state change: {state} → {nexa_state.value}")
            
            # Update brain state (will notify UI)
            self._change_state(nexa_state)
            
        except Exception as e:
            logger.error(f"Error handling listener state change: {e}")
    
    def _on_speaker_rejected(self, similarity: float):
        """
        Callback for when an unknown speaker is rejected by verification.
        
        Args:
            similarity: Similarity score (0.0 to 1.0)
        """
        try:
            # CRITICAL FIX: Don't interrupt active TTS (causes "Already speaking" warning)
            # If TTS is currently speaking, skip rejection message
            if self.tts.is_speaking:
                logger.debug(f"🔒 Speaker rejected ({similarity*100:.1f}%) but TTS is active - skipping rejection message")
                return
            
            # Generate rejection message
            similarity_percent = similarity * 100
            
            # Vary message based on similarity
            if similarity_percent < 40:
                message = "I don't recognize your voice. Please enroll your voice first by saying 'enroll my voice'."
            elif similarity_percent < 60:
                message = f"Your voice doesn't match my records. Voice match is only {similarity_percent:.0f}%. Please try speaking more clearly, or enroll again if needed."
            else:
                message = f"Your voice is close but I'm not certain it's you. Match is {similarity_percent:.0f}%. Try speaking more naturally, or say 'enroll my voice' to improve recognition."
            
            logger.info(f"🔒 Speaker rejected ({similarity_percent:.1f}% match) - providing feedback")
            
            # Speak rejection message with ducking
            self._change_state(NexaState.SPEAKING)
            self.tts.speak(message, ducking=True)
            
            # Return to listening
            self._change_state(NexaState.LISTENING)
            
        except Exception as e:
            logger.error(f"Error handling speaker rejection: {e}")
    
    def _detect_compound_commands(self, user_text: str) -> List[str]:
        """
        Detect if user input contains multiple commands to be executed sequentially (ENHANCED).
        Now handles 3+ command sequences and sequential information queries.
        
        Delegates to TextProcessor for the actual logic.
        
        Args:
            user_text: User's input
            
        Returns:
            List of individual commands (single item if not compound)
        """
        return self.text_processor.detect_compound_commands(user_text)
    
    def _execute_compound_commands(self, commands: List[str]) -> str:
        """
        Execute multiple commands sequentially and aggregate results.
        
        Args:
            commands: List of individual commands
            
        Returns:
            Aggregated response
        """
        results = []
        
        for i, cmd in enumerate(commands, 1):
            logger.info(f"🔧 Executing command {i}/{len(commands)}: {cmd}")
            
            try:
                # Temporarily disable compound command detection to prevent infinite loop
                original_text = cmd
                
                # Process each command individually
                # We manually call the AI processing logic but skip compound detection
                response = self._process_single_ai_call(original_text)
                results.append(response)
                
                logger.info(f"✅ Command {i} completed: {response[:50]}")
                
            except Exception as e:
                logger.error(f"❌ Command {i} failed: {e}")
                results.append(f"Command failed")
        
        # Aggregate results into a single response
        if len(results) == 1:
            return results[0]
        elif len(results) == 2:
            return f"{results[0]}. {results[1]}"
        else:
            # For 3+ commands, use a concise format
            summary_results = [r.split('.')[0] if '.' in r else r for r in results]
            return ". ".join(summary_results) + "."
    
    def _process_conditional_command(self, user_text: str) -> str:
        """
        Process a conditional command (if-then logic).
        
        Args:
            user_text: Command with conditional (e.g., "if battery low, close chrome")
            
        Returns:
            Result of action execution or condition not met message
        """
        try:
            # Parse the conditional
            parsed = self.conditional_handler.parse_conditional(user_text)
            
            if not parsed:
                logger.warning(f"⚠️ Failed to parse conditional: {user_text}")
                return "I couldn't understand that conditional command."
            
            condition = parsed['condition']
            action = parsed['action']
            
            logger.info(f"🔍 Condition: {condition}")
            logger.info(f"🎯 Action: {action}")
            
            # Evaluate the condition
            is_true, explanation = self.conditional_handler.evaluate_condition(condition)
            
            if is_true:
                # Condition met - execute the action
                logger.info(f"✅ Condition TRUE: {explanation}")
                logger.info(f"🚀 Executing action: {action}")
                
                # Process the action command through AI
                return self._process_with_ai(action)
            else:
                # Condition not met - inform user
                logger.info(f"❌ Condition FALSE: {explanation}")
                return f"Condition not met: {explanation}"
                
        except Exception as e:
            logger.error(f"❌ Error processing conditional: {e}", exc_info=True)
            return "Sorry, I encountered an error processing that conditional command."
    
    def _process_single_ai_call(self, user_text: str) -> str:
        """
        Process a single command with AI (bypasses compound detection).
        This is a simplified version of _process_with_ai for sequential command execution.
        
        Args:
            user_text: Single command to process
            
        Returns:
            Response from command execution
        """
        # DYNAMIC PREPROCESSING: Apply to sequential commands too
        if self.dynamic_preprocessor and self.enable_dynamic_preprocessing:
            preprocessing_result = self.dynamic_preprocessor.preprocess(user_text)
            
            # Handle nested multi-step: If preprocessing detects multi-step within sequential processing,
            # recursively process each sub-command
            if len(preprocessing_result.commands) > 1:
                logger.info(f"🔗 Nested multi-step detected in sequential processing: {len(preprocessing_result.commands)} commands")
                # Recursively handle each sub-command
                sub_results = []
                for sub_cmd in preprocessing_result.commands:
                    sub_result = self._process_single_ai_call(sub_cmd)
                    sub_results.append(sub_result)
                # Aggregate and return
                return ". ".join(sub_results)
            
            # Single command from preprocessing
            if preprocessing_result.commands:
                user_text = preprocessing_result.commands[0]
        
        # PREPROCESSING: Apply standalone ordinal resolution first (auto-lists if needed)
        user_text = self._resolve_standalone_ordinal(user_text)
        
        # Then apply pronoun resolution and normalization (same as main pipeline)
        # This ensures "open chrome and maximize it" works correctly
        user_text = self._resolve_pronouns(user_text)
        user_text = self._normalize_window_variations(user_text)
        
        logger.debug(f"🔧 [SEQUENTIAL] After preprocessing: {user_text}")
        
        # We'll skip history and pending actions for sequential commands to keep them fast
        screen_context_text = ""
        history_text = ""
        pending_action_text = ""
        
        # Get current mode
        is_offline = (self.llm_manager.current_mode == LLMMode.OFFLINE)
        
        # Build minimal prompt for quick execution
        if is_offline:
            function_catalog = self.executor.function_registry.get_catalog(format_type="simple")
            
            system_prompt = f"""You are Nexa, created by Ali Adil Waseem. User: {self.config.user_name}
Address the user respectfully as "Sir" or "Boss" occasionally in your responses. Never use their personal name.

Functions: {function_catalog}

For commands: {{"function_call": {{"name": "function_name", "parameters": {{}}}}, "response": "Done"}}
For talk: {{"response": "your reply"}}

User: {user_text}"""
        else:
            # Online mode - use abbreviated prompt
            system_prompt = f"""You are Nexa, created by Ali Adil Waseem. User: {self.config.user_name}.
Address the user respectfully as "Sir" or "Boss" occasionally in your responses. Never use their personal name.

Analyze this request and return JSON:
{{
    "action": "system_command",
    "intent": "description",
    "windows_command": "COMMAND_NAME",
    "response": "brief confirmation"
}}

Available commands: VOLUME_SET:level, BRIGHTNESS_SET:level, OPEN_APP:name, CLOSE_APP:name, WIFI_LIST, LIST_GAMES, SCREENSHOT, etc.

User: {user_text}"""
        
        # Get AI response
        response_text, mode_used = self.llm_manager.generate_response(
            system_prompt,
            temperature=0.3,
            max_output_tokens=150
        )
        
        logger.info(f"🤖 [SEQUENTIAL] AI Response: {response_text[:200]}")
        
        # Parse and execute
        return self._quick_parse_and_execute(response_text, mode_used, user_text)
    
    def _quick_parse_and_execute(self, response_text: str, mode_used: 'LLMMode', user_text: str) -> str:
        """
        Quick parse and execute for sequential commands (simplified version).
        
        Args:
            response_text: AI response
            mode_used: Mode that was used
            user_text: Original user text
            
        Returns:
            Execution result
        """
        # Strip markdown blocks
        cleaned_response = response_text
        if '```json' in response_text or '```' in response_text:
            cleaned_response = re.sub(r'```json\s*', '', response_text)
            cleaned_response = re.sub(r'```\s*', '', cleaned_response)
            cleaned_response = cleaned_response.strip()
        
        # Try to extract and parse JSON
        if '{' in cleaned_response:
            try:
                start_idx = cleaned_response.find('{')
                if start_idx != -1:
                    potential_json = cleaned_response[start_idx:]
                    response_data = json.loads(potential_json)
                    
                    # Dynamic function calling (Gemma3 / offline mode)
                    if "function_call" in response_data:
                        func_call = response_data["function_call"]
                        func_name = func_call.get("name", "")
                        func_params = func_call.get("parameters", {})
                        user_response = response_data.get("response", "Done")
                        
                        logger.info(f"🔧 [SEQUENTIAL] Calling function: {func_name} with params: {func_params}")
                        
                        # VALIDATION: Validate function call before execution (CR-12, CR-13, CR-14)
                        is_valid, error_msg = self.validate_function_call(func_name, func_params)
                        if not is_valid:
                            logger.error(f"❌ [SEQUENTIAL] Validation failed: {error_msg}")
                            return error_msg
                        
                        try:
                            result = self.executor.function_registry.call(func_name, func_params)
                            
                            # PHASE 29: Record activity for pattern learning
                            self._record_activity_pattern(func_name, "command")
                            
                            # CRITICAL: Store this action in context for next command in sequence
                            # This enables "open chrome and maximize it" to work
                            self.context_manager.push_action(
                                action=func_name,
                                data=func_params,
                                result=result
                            )
                            
                            logger.info(f"✅ [SEQUENTIAL] Function result: {result}")
                            
                            # Return the result from the executor, not just the user message
                            if result and "Error" not in result:
                                return result
                            else:
                                return user_response
                        except Exception as e:
                            logger.error(f"❌ [SEQUENTIAL] Function call failed: {e}")
                            return f"{user_response}, but there was an issue"
                    
                    # Conversation only
                    elif "response" in response_data and "action" not in response_data:
                        return response_data.get("response", "Done")
                    
                    # Hardcoded keyword system (Legacy / online mode)
                    elif response_data.get('action') == 'system_command':
                        windows_command = response_data.get('windows_command', '')
                        user_response = response_data.get('response', 'Done')
                        
                        # Execute command using the same logic as main execution
                        # We'll just handle the most common sequential commands
                        if windows_command.startswith('VOLUME_SET:'):
                            level = int(windows_command.split(':')[1])
                            self.executor.set_volume(level)
                            return user_response
                        
                        elif windows_command.startswith('BRIGHTNESS_SET:'):
                            level = int(windows_command.split(':')[1])
                            self.executor.set_brightness(level)
                            return user_response
                        
                        elif windows_command.startswith('VOLUME_UP:'):
                            amount = int(windows_command.split(':')[1]) if ':' in windows_command else 10
                            self.executor.increase_volume(amount)
                            return user_response
                        
                        elif windows_command.startswith('VOLUME_DOWN:'):
                            amount = int(windows_command.split(':')[1]) if ':' in windows_command else 10
                            self.executor.decrease_volume(amount)
                            return user_response
                        
                        elif windows_command.startswith('BRIGHTNESS_UP:'):
                            amount = int(windows_command.split(':')[1]) if ':' in windows_command else 10
                            self.executor.increase_brightness(amount)
                            return user_response
                        
                        elif windows_command.startswith('BRIGHTNESS_DOWN:'):
                            amount = int(windows_command.split(':')[1]) if ':' in windows_command else 10
                            self.executor.decrease_brightness(amount)
                            return user_response
                        
                        elif windows_command.startswith('OPEN_APP:'):
                            app_name = windows_command.replace('OPEN_APP:', '').strip()
                            self.executor.open_application(app_name)
                            return user_response
                        
                        elif windows_command == 'SCREENSHOT':
                            self.executor.take_screenshot()
                            return user_response
                        
                        elif windows_command == 'LIST_GAMES':
                            result = self.executor.list_games()
                            return result
                        
                        else:
                            # Generic command execution
                            return user_response
            
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Quick parse failed: {e}")
                return "Done"
        
        # Fallback - just return the text
        return response_text if len(response_text) < 100 else "Done"
    
    def _process_user_input(self, user_text: str):
        """
        Process user input and generate response.
        Uses Llama 3.1 8B for intent recognition and command execution.
        
        Args:
            user_text: User's transcribed speech
        """
        logger.debug(f"🎯 Processing: {user_text[:50]}")
        self._change_state(NexaState.THINKING)
        
        # PHASE 29 - Record user interaction for idle tracking
        self._record_user_interaction()
        
        # CRITICAL FIX: Pause listener during processing to prevent double commands
        # Without this, listener continues recording during LLM processing and captures
        # TTS audio/noise as "new commands" (causing 0.0% false detections)
        # Keep music at listening volume (15%) during thinking for better UX
        self.listener.pause_listening(for_tts=False)
        logger.debug("🔇 Listener paused for brain processing (music stays at 15%)")
        
        # PHASE 28 - COMPANION MODE: Immediate acknowledgment
        # Speak a quick "On it!" or similar phrase BEFORE starting LLM processing
        # This makes NEXA feel responsive and alive (user knows we heard them)
        if self.thinking_feedback:
            try:
                self.thinking_feedback.start_thinking(user_text)
            except Exception as e:
                logger.warning(f"Thinking feedback error: {e}")
        
        response = None
        
        try:
            # === DIRECT PATTERN MATCHING FOR CRITICAL COMMANDS ===
            # These bypass LLM for instant, reliable execution
            user_lower = user_text.lower().strip()
            
            # Exit/Shutdown commands - must be handled directly (not via LLM)
            exit_patterns = ['exit', 'quit', 'close', 'shutdown', 'goodbye', 'bye', 'good bye']
            if any(user_lower == pattern or user_lower.startswith(pattern + ' ') for pattern in exit_patterns):
                logger.info(f"🚪 Direct exit command detected: '{user_text}'")
                response = self.executor.exit_nexa()
                self._emit_message("nexa", response)
                # Store exit interaction in memory
                self.context_manager.add_interaction(user_text, response, success=True)
                return  # Don't continue processing, app is shutting down
            
            # Use AI to understand intent and execute commands
            logger.debug("Calling _process_with_ai()...")
            response = self._process_with_ai(user_text)
            
            logger.debug(f"✅ Response ready ({len(response) if response else 0} chars)")
            
            if not response:
                logger.error("❌ Empty AI response!")
                response = "I didn't understand that. Can you try again?"
            
            # Store complete interaction in Smart Memory (with full response)
            self.context_manager.add_interaction(user_text, response, success=True)
            logger.debug("💾 Stored interaction in Smart Memory")
            
            # PHASE 28: End thinking feedback before speaking response
            if self.thinking_feedback:
                self.thinking_feedback.end_thinking(success=True)
            
            # CRITICAL: Stop any ongoing TTS (e.g. thinking feedback progress update)
            # before starting the actual response to prevent race conditions
            if self.tts.is_speaking():
                logger.info("🛑 Stopping thinking feedback TTS before response")
                self.tts.stop()
                time.sleep(0.1)  # Brief pause to let audio channel fully release
            
            # Emit response message and speak
            logger.debug(f"Emitting response to UI")
            self._emit_message("nexa", response)
            logger.info(f"🗣️ Starting TTS: {response[:50]}...")
            self._speak_response(response)
            logger.info(f"✅ TTS completed")
        
        except Exception as e:
            logger.error(f"❌ EXCEPTION in _process_user_input: {e}", exc_info=True)
            
            # PHASE 28: End thinking feedback on error
            if self.thinking_feedback:
                self.thinking_feedback.end_thinking(success=False)
            
            error_response = "I'm sorry, I encountered an error processing that request."
            self._emit_message("nexa", error_response)
            try:
                self._speak_response(error_response)
            except Exception as e2:
                logger.error(f"❌ EXCEPTION in error _speak_response: {e2}", exc_info=True)
        
        finally:
            # CRITICAL FIX: Always resume listener after processing (even on error)
            # This ensures listener is ready for next command
            self.listener.resume_listening()
            logger.debug("🔊 Listener resumed after brain processing")
        
        logger.info("🎯 Finished processing user input")
        
        # 🔥 MEMORY MANAGEMENT: Force garbage collection after command
        # Ensures all unused objects are freed immediately
        try:
            import gc
            gc.collect()
            logger.debug("🧹 Garbage collection completed")
        except Exception as e:
            logger.debug(f"Could not run garbage collection: {e}")
        
        # Note: State is set to IDLE by _speak_response() after TTS completes
    
    def _process_with_ai(self, user_text: str) -> str:
        """
        Process user request with AI for intent recognition and execution.
        AI determines if it's a system command or conversation.
        
        Args:
            user_text: User input
            
        Returns:
            Response to user
        """
        try:
            # EDGE CASE VALIDATION: Validate input before any processing
            if self.input_validator and self.enable_input_validation:
                is_valid, error_message = self.input_validator.validate_input(user_text)
                if not is_valid:
                    logger.warning(f"⚠️ Invalid input detected: {error_message}")
                    return error_message
            
            # STAGE 0: Check if user is responding to a clarification question
            clarification_reformulated = self._check_clarification_response(user_text)
            if clarification_reformulated:
                # User answered clarification - process the reformulated command
                logger.info(f"📝 Processing clarification answer: '{clarification_reformulated}'")
                user_text = clarification_reformulated
            
            # STAGE 0.5: Check if user is responding to a pending intent (e.g., play_music asking for song name)
            has_pending = self.context_manager.has_pending_follow_up()
            logger.info(f"🎯 STAGE 0.5 - Checking pending follow-up: {has_pending}")
            
            if has_pending:
                logger.info(f"🎯 Pending follow-up detected! Processing: '{user_text}'")
                pending_result = self._handle_pending_intent(user_text)
                
                # Special case: proactive context - inject context into user_text for LLM
                if isinstance(pending_result, tuple) and pending_result[0] == "__PROACTIVE_CONTEXT__":
                    user_text = pending_result[1]  # Use contextualized input
                    logger.info(f"💜 Proactive context injected: '{user_text}'")
                    # Continue to normal LLM processing with context
                elif pending_result:
                    logger.info(f"✅ Pending intent handled: {pending_result[:50]}...")
                    return pending_result
                else:
                    # None means "pass to normal LLM" - not an error
                    logger.info(f"🔄 Pending intent passed to LLM for: '{user_text}'")
            
            # PHASE 3 OPTIMIZATION: Check quick response cache for instant 0s answers
            normalized_input = user_text.lower().strip()
            for pattern, executor_func in self.quick_response_cache.items():
                if re.search(pattern, normalized_input):
                    logger.info(f"⚡ CACHE HIT: Instant response for '{user_text}'")
                    try:
                        result = executor_func()
                        logger.info(f"⚡ Cache result: {result}")
                        return result
                    except Exception as e:
                        logger.warning(f"⚠️ Cache execution failed: {e} - falling back to AI")
                        break
            
            # DYNAMIC PREPROCESSING: Apply intelligent preprocessing (multi-step, ambiguity, pronouns)
            # This runs BEFORE other preprocessing to provide guaranteed behavior
            if self.dynamic_preprocessor and self.enable_dynamic_preprocessing:
                preprocessing_result = self.dynamic_preprocessor.preprocess(user_text)
                
                # Check if clarification is needed
                if preprocessing_result.needs_clarification:
                    logger.info(f"❓ Dynamic preprocessor detected ambiguity")
                    return preprocessing_result.clarification_question
                
                # Get preprocessed commands
                preprocessed_commands = preprocessing_result.commands
                
                # Log transformations
                if preprocessing_result.metadata.get('transformations'):
                    logger.info(f"🔧 Dynamic preprocessing applied: {preprocessing_result.metadata['transformations']}")
                
                # If multi-step commands detected, execute them sequentially
                if len(preprocessed_commands) > 1:
                    logger.info(f"🔗 Dynamic multi-step detected: {len(preprocessed_commands)} commands")
                    return self._execute_compound_commands(preprocessed_commands)
                
                # Single command - use the preprocessed version
                if len(preprocessed_commands) == 1:
                    user_text = preprocessed_commands[0]
                    logger.debug(f"🔧 Using dynamically preprocessed command: '{user_text}'")
            
            # PHASE 17: Sequential Commands - Check for compound commands (fallback for compatibility)
            # This is kept for backward compatibility but dynamic preprocessor should handle it first
            compound_commands = self._detect_compound_commands(user_text)
            if len(compound_commands) > 1:
                logger.info(f"🔗 Sequential commands detected (fallback): {len(compound_commands)} commands")
                return self._execute_compound_commands(compound_commands)
            
            # CONDITIONAL COMMANDS: Check for if-then logic
            if self.conditional_handler and self.enable_conditional_commands:
                if self.conditional_handler.detect_conditional(user_text):
                    logger.info(f"🔀 Conditional command detected: {user_text}")
                    return self._process_conditional_command(user_text)
            
            # PREPROCESSING STAGE 0.5: Resolve standalone ordinals (auto-list if needed)
            # This converts "launch the first one" → auto-lists games → "launch TEKKEN 8"
            user_text = self._resolve_standalone_ordinal(user_text)
            
            # PREPROCESSING STAGE 1: Resolve pronouns and references (AFTER standalone ordinal)
            # This converts "close it" → "close chrome" using context
            user_text = self._resolve_pronouns(user_text)
            
            # PREPROCESSING STAGE 2: Normalize natural language variations
            # This converts "make bigger" → "maximize"
            user_text = self._normalize_window_variations(user_text)
            
            logger.debug(f"🤖 Asking AI (after preprocessing): {user_text}")
            
            # MODE SWITCHING: Explicit detection for "go online/offline" commands
            # This must run BEFORE vision checks to allow mode switching
            mode_switch_result = self._detect_mode_switch_command(user_text)
            if mode_switch_result:
                return mode_switch_result
            
            # PHASE 24: Vision features completely disabled until Phase 23 (PaddleOCR-VL)
            if self._detect_vision_request(user_text):
                logger.info(f"👁️ Vision request detected but vision disabled (Phase 24): {user_text}")
                return ("Vision features are currently disabled. "
                        "Phase 23 will add offline vision capabilities using PaddleOCR-VL. "
                        "For now, I can help you with all other system commands and conversations!")
            
            # Get current mode for context building
            current_mode = self.llm_manager.current_mode
            is_offline = (current_mode == LLMMode.OFFLINE)
            
            # QUICK-FOLLOWUP CACHE CHECK: If user asked a short follow-up such as
            # "how many?" or "what are they?", try to answer from cached last action
            try:
                last_action_entry = self.context_manager.get_last_action()
                last_action_name = ''
                last_result = ''
                if isinstance(last_action_entry, dict):
                    last_action_name = last_action_entry.get('action', '')
                    last_result = last_action_entry.get('result', '') or last_action_entry.get('data', {})
                elif isinstance(last_action_entry, tuple) or isinstance(last_action_entry, list):
                    # legacy tuple: (action, data)
                    last_action_name = last_action_entry[0] if len(last_action_entry) > 0 else ''
                    last_result = last_action_entry[1] if len(last_action_entry) > 1 else ''

                if last_action_name and (self._is_counting_question(user_text) or self._is_listing_question(user_text)):
                    cached = self._answer_from_cache(user_text, last_action_name, last_result)
                    if cached:
                        logger.info(f"⚡ Quick cache answer for follow-up: {cached}")
                        return cached
            except Exception:
                # Don't let cache check crash the main flow
                logger.exception("Error during quick follow-up cache check")
            
            # Get recent conversation history for context (increased from 5 to 10 for better context retention)
            recent_history = self.context_manager.get_recent_context(max_interactions=10)
            history_text = ""
            
            # Unified history for Llama 3.1 (Both Online/Offline)
            # Llama 3.1 handles context well, but we use the optimized builder for consistency
            history_text = self._build_llama_history(recent_history)
            
            # Check if there's a pending action awaiting confirmation
            pending_action_text = ""
            if self.context_manager.has_pending_action():
                pending = self.context_manager.pending_action
                pending_action_text = f"\n\nPENDING ACTION (awaiting confirmation):\n"
                pending_action_text += f"Type: {pending.get('type', 'unknown')}\n"
                pending_action_text += f"Details: {pending.get('data', {})}\n"
                pending_action_text += "If user says 'yes', 'do it', 'go ahead', 'continue', 'sure', 'okay' → Execute the pending action.\n"
                pending_action_text += "If user says 'no', 'cancel', 'nevermind' → Clear the pending action and respond naturally.\n"
            
            # Check if there's recent screen analysis for context
            screen_context_text = ""
            if self.context_manager.has_screen_analysis_context():
                screen_analysis = self.context_manager.get_last_screen_analysis()
                screen_context_text = f"\n\nRECENT SCREEN ANALYSIS (available for answering follow-up questions):\n"
                screen_context_text += f"Type: {screen_analysis.get('type', 'unknown')}\n"
                screen_context_text += f"Content: {screen_analysis.get('result', '')[:500]}...\n"  # Truncate for context window
                screen_context_text += "Use this to answer questions like 'what does it do?', 'explain that code', 'what's the error?', etc.\n"
            
            # MEMORY PRE-FETCH: Auto-query memory for personal/relationship questions
            # This ensures the LLM has the info BEFORE it needs to decide to call a function
            memory_context_text = self._prefetch_memory_context(user_text)
            
            # Build system prompt for intent recognition
            # Check current mode to optimize prompt length
            current_mode = self.llm_manager.current_mode
            is_offline = (current_mode == LLMMode.OFFLINE)
            
            # Use DYNAMIC FUNCTION CALLING for Llama 3.1
            if True:  # Always use this format for Llama 3.1
                # Get function catalog
                function_catalog = self.executor.function_registry.get_catalog(format_type="detailed")
                
                system_prompt = f"""You are Nexa, Windows AI assistant. User: {self.config.user_name}{history_text}{pending_action_text}{screen_context_text}{memory_context_text}
Address the user respectfully as "Sir" or "Boss" occasionally in your responses. Never use their personal name.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ OFFLINE MODE AWARENESS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You are currently running in OFFLINE mode with the following capabilities:
• NO vision/screenshot analysis (text-only, cannot see screen)
• ENHANCED reasoning (Llama 3.1 8B with superior NLP and function calling)
• LARGER context (128K token window for better conversation memory)
• STRONG reference resolution (excellent at handling pronouns and follow-ups)

✅ What WORKS in offline mode:
- Open/close applications by name
- Window management (minimize, maximize, close, switch)
- List running apps, installed apps, games
- System information (battery, CPU, RAM)
- Complex multi-step commands (e.g., "open chrome and maximize it")
- Natural conversations with context awareness
- Follow-up questions about previous interactions

❌ What requires ONLINE mode (Phase 24 - Single Model Architecture):
- Vision/screenshot analysis (temporary - Phase 23 will add offline vision)
- Web search (requires internet connection)
- Weather data (requires API access)
- Email checking (requires internet)

SAME MODEL (Llama 3.1 8B) for both online and offline - only feature availability changes.

If user requests features not available offline, politely inform them:
"This feature requires online mode (internet connection). I can help with [alternative] instead."
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AVAILABLE FUNCTIONS:
{function_catalog}

RESPONSE FORMAT:
For system actions (JSON):
{{
    "function_call": {{
        "name": "function_name",
        "parameters": {{"param": value}}
    }},
    "response": "what to say to user"
}}

For conversation (JSON):
{{
    "response": "your conversational response"
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL ERROR HANDLING RULES (PREVENT HALLUCINATIONS):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ RULE 0 - NEVER CLAIM SUCCESS PREMATURELY:
✗ NEVER say "Opening XYZ" until you KNOW it will work
✗ NEVER say "Done!" before function executes
✓ Use cautious language: "Let me open XYZ", "I'll try to open XYZ"
✓ Let the SYSTEM report success/failure, not you

VALIDATION BEFORE RESPONDING:
When opening apps, closing windows, or modifying things that might not exist:
✓ Response: "Let me check if XYZ is available"
✓ Response: "I'll try to open XYZ"
✗ Response: "Opening XYZ" (too confident - might not exist!)

ERROR AWARENESS:
If you suspect something won't work (typo, app name looks weird, etc.):
✓ Ask for confirmation: "I don't see XYZ installed. Did you mean ABC?"
✓ Suggest alternatives: "XYZ not found. Try 'list applications'?"
✗ Don't proceed blindly and fail silently

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL COMMAND PARSING RULES (Follow these BEFORE choosing a function):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RULE 1 - MULTI-STEP COMMANDS:
If the command contains connecting words like "and", "then", or commas, it is MULTIPLE commands:
✓ "open chrome and maximize it" → TWO commands: (1) open chrome, (2) maximize chrome
✓ "set volume to 50 then close chrome" → TWO commands: (1) set volume 50, (2) close chrome
✓ "list games, launch the first one" → TWO commands: (1) list games, (2) launch first game
✗ DO NOT execute multi-step commands as single function!

RULE 2 - PRONOUN RESOLUTION:
If command uses "it", "that", "them", "this" - resolve to the actual target:
✓ After "open chrome" → "close it" means "close chrome"
✓ After "list games" → "launch the first one" means "launch [first game from list]"
✓ After "open notepad" → "maximize it" means "maximize notepad"
✗ DO NOT pass pronouns to functions - always resolve them first!

RULE 3 - AMBIGUITY DETECTION:
If command is missing critical information, ASK for clarification:
✓ "open" (open WHAT?) → ask "What would you like me to open?"
✓ "close" (close WHAT?) → ask "Which application should I close?"
✓ "set volume" (to WHAT level?) → ask "What volume level?"
✗ DO NOT guess or assume - always ask when uncertain!

RULE 4 - CONTEXT AWARENESS:
Use conversation history to resolve references:
✓ If last action was "opened chrome" → "make it bigger" = maximize chrome window
✓ If last query was "list games" → "how many?" = count from previous list
✓ If user just asked "what time" → "thanks" = conversational response (no function)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ RULE 5 - MEMORY vs SYSTEM COMMANDS (CRITICAL!):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
These are DIFFERENT! Choose the right function based on INTENT:

MEMORY QUESTIONS (→ what_do_you_know) - Asking about USER'S PREFERENCES/PERSONAL INFO:
Keywords: "like", "prefer", "love", "favorite", "enjoy", "do I", "did I tell you", "remember", "friend", "who is", "about"
✓ "What games do I LIKE?" → what_do_you_know(topic="games I like")
✓ "What apps do I PREFER?" → what_do_you_know(topic="apps I prefer")
✓ "What music do I ENJOY?" → what_do_you_know(topic="music I enjoy")
✓ "What's my favorite color?" → what_do_you_know(topic="favorite color")
✓ "What's my favorite food?" → what_do_you_know(topic="favorite food")
✓ "When is my birthday?" → what_do_you_know(topic="birthday")
✓ "What did I tell you about my work?" → what_do_you_know(topic="my work")
✓ "Do you remember what I like?" → what_do_you_know(topic="what I like")
✓ "What do you know about me?" → what_do_you_know(topic="about me")
✓ "Who is my best friend?" → what_do_you_know(topic="best friend")
✓ "Tell me about my best friend" → what_do_you_know(topic="best friend")
✓ "What do you know about [person]?" → what_do_you_know(topic="[person name]")
✓ "Who is [person]?" → what_do_you_know(topic="[person name]")
✓ "What do you know about my friends?" → what_do_you_know(topic="friends")

SYSTEM COMMANDS (→ list_games, list_apps, play_music, etc.) - Asking about PC/SYSTEM:
Keywords: "list", "show", "installed", "are installed", "launch", "open", "play"
✓ "List games" → list_games() - shows installed games on PC
✓ "List apps" → list_apps() - shows installed applications
✓ "Show my music" → list_music() - shows music library
✓ "What games are installed?" → list_games()
✓ "Play music" → play_music()
✓ "Open Chrome" → open_application()

⚠️ KEY DISTINCTION - Same topic, different intent:
"What games do I LIKE?" = MEMORY (personal preference) → what_do_you_know
"What games do I HAVE?" = SYSTEM (installed on PC) → list_games
"What music do I LIKE?" = MEMORY (personal taste) → what_do_you_know
"List my music" = SYSTEM (files on PC) → list_music
"What apps do I USE most?" = MEMORY (usage habits) → what_do_you_know
"What apps are running?" = SYSTEM (current processes) → list_apps

The pattern: If asking about feelings/preferences/personal info → what_do_you_know
             If asking about system state/installed/running things → system function

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP-BY-STEP REASONING (Think through EACH command like this):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP 1 - ANALYZE COMMAND STRUCTURE:
[ ] Is this a multi-step command? (contains "and", "then", comma)
[ ] Does it use pronouns? ("it", "that", "them", "this")
[ ] Is information missing? (no target, no value, unclear intent)
[ ] Is this a follow-up question? ("how many?", "what about?", "and that?")

STEP 2 - CHECK CONTEXT:
[ ] What was the last command executed?
[ ] What app/window was last mentioned?
[ ] What list was recently shown?
[ ] Is there pending action from conversation?

STEP 3 - RESOLVE REFERENCES:
[ ] Replace pronouns with actual targets from context
[ ] Resolve "the app", "the window", "the game" to specific names
[ ] Resolve ordinals like "first one", "second game" using last list

STEP 4 - VALIDATE:
[ ] Do I have all required information?
[ ] Is the target valid and specific?
[ ] Can this command be executed?
[ ] Should I ask for clarification?

STEP 5 - SELECT FUNCTION:
Now choose the appropriate function and extract parameters.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ENHANCED EXAMPLES (showing reasoning):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Example 1 - Multi-step command:
User: "open chrome and maximize it"
Analysis: Contains "and" → TWO commands
Step 1: "open chrome"
Step 2: "maximize it" → "it" = chrome (from step 1)
Response: {{"function_call": {{"name": "open_application", "parameters": {{"app_name": "chrome"}}}}, "response": "Opening Chrome and will maximize it"}}

Example 2 - Pronoun resolution:
Context: Last action was "opened notepad"
User: "close it"
Analysis: "it" refers to "notepad" (last opened app)
Response: {{"function_call": {{"name": "close_application", "parameters": {{"app_name": "notepad"}}}}, "response": "Closing Notepad"}}

Example 3 - Ambiguous command (needs clarification):
User: "open"
Analysis: Missing target - WHAT to open?
Response: {{"response": "What would you like me to open?"}}

Example 4 - Follow-up question:
Context: Just executed "list games" which returned 5 games
User: "how many?"
Analysis: Asking about count from previous list
Response: {{"response": "You have 5 games installed"}}

Example 5 - Context-dependent:
Context: Last action was "maximize chrome window"
User: "make it smaller"
Analysis: "it" = chrome window, "smaller" = opposite of maximize = minimize
Response: {{"function_call": {{"name": "minimize_window", "parameters": {{"app_name": "chrome"}}}}, "response": "Minimizing Chrome"}}

Example 6 - Simple conversation:
User: "how are you?"
Analysis: Conversational query, no function needed
Response: {{"response": "I'm doing well, thanks!"}}

Example 7 - Time query:
User: "what time?"
Analysis: Simple function call, no ambiguity
Response: {{"function_call": {{"name": "get_current_time", "parameters": {{}}}}, "response": "Let me check"}}

Example 8 - Volume control:
User: "set volume to 50"
Analysis: Clear target (volume) and value (50)
Response: {{"function_call": {{"name": "set_volume", "parameters": {{"level": 50}}}}, "response": "Setting volume to 50%"}}

Example 9 - Music playback (CRITICAL: ASK WHAT TO PLAY):
User: "play some music"
Analysis: User wants music but didn't specify what - ASK for clarification
Response: {{"response": "What would you like me to play?"}}

Example 10 - Play specific song:
User: "play bohemian rhapsody"
Analysis: Play specific song by name
Response: {{"function_call": {{"name": "play_music", "parameters": {{"song_name": "bohemian rhapsody"}}}}, "response": "Playing Bohemian Rhapsody"}}

Example 11 - Pause music:
User: "pause the music"
Analysis: Pause currently playing music
Response: {{"function_call": {{"name": "pause_music", "parameters": {{}}}}, "response": "Pausing music"}}

Example 12 - Resume music:
User: "resume music"
Analysis: Resume paused music
Response: {{"function_call": {{"name": "resume_music", "parameters": {{}}}}, "response": "Resuming playback"}}

Example 13 - Next song:
User: "next song"
Analysis: Skip to next track
Response: {{"function_call": {{"name": "next_song", "parameters": {{}}}}, "response": "Playing next song"}}

Example 14 - Summarize content (Content Mode):
User: "summarize the content"
Analysis: Use refine_text with mode="summarize" - NOT a separate function!
Response: {{"function_call": {{"name": "refine_text", "parameters": {{"mode": "summarize"}}}}, "response": "Summarizing the content..."}}

Example 15 - Make text formal (Content Mode):
User: "make it more formal"
Analysis: Use refine_text with mode="formal"
Response: {{"function_call": {{"name": "refine_text", "parameters": {{"mode": "formal"}}}}, "response": "Making it more formal..."}}

Example 16 - Fix grammar (Content Mode):
User: "fix the grammar"
Analysis: Use refine_text with mode="grammar_only"
Response: {{"function_call": {{"name": "refine_text", "parameters": {{"mode": "grammar_only"}}}}, "response": "Fixing grammar errors..."}}

Example 17 - Extract key terms (Study Tool):
User: "extract key terms from this"
Analysis: Use refine_text with mode="extract_terms"
Response: {{"function_call": {{"name": "refine_text", "parameters": {{"mode": "extract_terms"}}}}, "response": "Extracting key terms..."}}

Example 18 - Create flashcards (Study Tool):
User: "make flashcards"
Analysis: Use refine_text with mode="flashcards"
Response: {{"function_call": {{"name": "refine_text", "parameters": {{"mode": "flashcards"}}}}, "response": "Creating flashcards..."}}

Example 19 - Paraphrase text (Writing Enhancement):
User: "paraphrase this"
Analysis: Use refine_text with mode="paraphrase"
Response: {{"function_call": {{"name": "refine_text", "parameters": {{"mode": "paraphrase"}}}}, "response": "Paraphrasing the text..."}}

Example 20 - Create outline (Organization):
User: "create an outline"
Analysis: Use refine_text with mode="outline"
Response: {{"function_call": {{"name": "refine_text", "parameters": {{"mode": "outline"}}}}, "response": "Creating outline structure..."}}

Example 21 - Memory recall for relationships:
User: "What do you know about my best friend?"
Analysis: Question about personal relationship → MUST use what_do_you_know
Response: {{"function_call": {{"name": "what_do_you_know", "parameters": {{"topic": "best friend"}}}}, "response": "Let me check my memory..."}}

Example 22 - Memory recall for a person:
User: "Who is [person name]?"
Analysis: Asking about a specific person → MUST check memory first
Response: {{"function_call": {{"name": "what_do_you_know", "parameters": {{"topic": "[person name]"}}}}, "response": "Let me recall what I know..."}}

Example 23 - Memory recall for friends:
User: "Tell me about my friends"
Analysis: Asking about relationships → MUST use what_do_you_know
Response: {{"function_call": {{"name": "what_do_you_know", "parameters": {{"topic": "friends"}}}}, "response": "Let me check what I know about your friends..."}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 CRITICAL: MEMORY QUERIES - ALWAYS CHECK BEFORE SAYING "I DON'T KNOW"!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
When user asks about ANY of these topics, ALWAYS call what_do_you_know FIRST:
• Personal info: "my birthday", "where I live", "my university", "about me"
• Relationships: "my friend", "my best friend", "who is [name]", "about [person]"
• Preferences: "what I like", "my favorite X", "what I love/hate"
• Stored facts: "do you know", "do you remember", "tell me about"

✗ NEVER say "I don't know" or "I don't have information" without checking memory first!
✓ ALWAYS call what_do_you_know for personal/relationship/preference questions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ CRITICAL: DO NOT INVENT FUNCTION NAMES!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✗ WRONG: "summarize_text", "extract_terms", "create_flashcards", "paraphrase_text"
✓ RIGHT: Use "refine_text" with appropriate mode parameter for ALL text operations
✓ RIGHT: ONLY use function names from the AVAILABLE FUNCTIONS list above
✓ RIGHT: If you're not sure → check the function list → it's complete!

The function list above is COMPLETE and ACCURATE. If a function isn't listed, IT DOESN'T EXIST.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IMPORTANT REMINDERS:
- ALWAYS return valid JSON (no extra text)
- NO markdown formatting in responses
- Keep responses SHORT (1-2 sentences)
- When uncertain → ASK, don't guess
- Multi-step → handle first command, note second for sequential execution
- Pronouns → ALWAYS resolve using context
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

User: {user_text}"""
            else:
                # Full detailed prompt for Gemini (online mode)
                system_prompt = f"""You are Nexa, an AI assistant for Windows with full desktop control capabilities.
User name: {self.config.user_name}{history_text}{pending_action_text}{screen_context_text}
Address the user respectfully as "Sir" or "Boss" occasionally in your responses. Never use their personal name.

IMPORTANT CONVERSATIONAL RULES:
- Keep responses SHORT and NATURAL (1-2 sentences max for conversation)
- When asked "what can you do?", give BRIEF overview: "I can control your computer - open apps, manage windows, adjust settings, check battery, read notifications, and more. What would you like me to do?"
- NO markdown formatting (no **, *, bullets) - speak naturally
- Be concise and friendly

When the user asks you to perform a system action or needs real-time information, respond with JSON:
{{"action": "system_command", "intent": "describe what user wants", "windows_command": "KEYWORD or command", "response": "what to say to user"}}

AVAILABLE KEYWORDS (use these for native functions):
- ASK_TIME - Get current time/date
- CHECK_MODE - Check if Nexa is online or offline. When user asks "are you online?" or "what mode?", use this command.
- STOP_LISTENING - Pause voice recognition (user says "stop listening")
- START_LISTENING - Resume voice recognition (user says "start listening")
- OPEN_APP:appname - Launch application (automatically finds installed apps)
- LIST_APPS - List currently running applications (background processes)
- LIST_INSTALLED_APPS - List all installed applications on the system
- LIST_INSTALLED_APPS:keyword - Search installed apps by keyword (e.g., LIST_INSTALLED_APPS:video)
- REFRESH_APPS - Re-scan for newly installed applications
- APP_RUNNING:appname - Check if specific app is running
- CLOSE_APP:appname - Close/terminate application
- SEARCH_WEB:query - Search web using default browser
- VOLUME_UP:amount - Increase volume by % (e.g., VOLUME_UP:10)
- VOLUME_DOWN:amount - Decrease volume by % (e.g., VOLUME_DOWN:10)
- VOLUME_SET:level - Set volume to % (e.g., VOLUME_SET:50)
- VOLUME_MUTE - Mute volume
- VOLUME_UNMUTE - Unmute volume
- BRIGHTNESS_UP:amount - Increase brightness by % (e.g., BRIGHTNESS_UP:10)
- BRIGHTNESS_DOWN:amount - Decrease brightness by % (e.g., BRIGHTNESS_DOWN:10)
- BRIGHTNESS_SET:level - Set brightness to % (e.g., BRIGHTNESS_SET:70)
- WIFI_STATUS - Check WiFi connection status and get network name
- WIFI_DISCONNECT - Disconnect from WiFi
- WIFI_CONNECT:ActualNetworkName - Connect to specific WiFi network. IMPORTANT: Replace 'ActualNetworkName' with real network name from WIFI_PROFILES, NOT the literal word 'networkname'!
- WIFI_LIST - List available WiFi networks
- WIFI_PROFILES - Get saved WiFi network profiles (use this to find last used network for reconnection)
- SMART_SELECT:query - Find and select text using AI vision (e.g., SMART_SELECT:find the email)
- SMART_COPY:query - Find text and copy it (e.g., SMART_COPY:copy the price)
- SMART_DELETE:query - Find text and delete it (e.g., SMART_DELETE:delete word hello)
- READ_SCREEN - Read all text visible on screen using OCR
- DESCRIBE_SCREEN - Get AI visual description of screen content
- SCREEN_ANALYZE - Combined OCR + AI vision analysis of screen (comprehensive understanding)
- SELECT_ALL - Select all text (Ctrl+A)
- COPY_SELECTED - Copy selected text (Ctrl+C)
- PASTE - Paste clipboard content (Ctrl+V)
- CUT_SELECTED - Cut selected text (Ctrl+X)
- DELETE_SELECTED - Delete selected text (Delete key)
- WINDOW_MINIMIZE:identifier - Minimize a window (e.g., WINDOW_MINIMIZE:chrome)
- WINDOW_MAXIMIZE:identifier - Maximize a window (e.g., WINDOW_MAXIMIZE:notepad)
- WINDOW_RESTORE:identifier - Restore window to normal size
- WINDOW_HIDE:identifier - Hide a window (keeps process running)
- WINDOW_SHOW:identifier - Show a hidden window
- WINDOW_ACTIVE - Get currently active window title
- WINDOW_STATE:identifier - Get window state (minimized/maximized/normal)
- BATTERY_STATUS - Get full battery status (charging, percentage, time remaining)
- BATTERY_PERCENT - Get battery percentage only
- BATTERY_CHARGING - Check if battery is charging
- BATTERY_TIME - Get battery time remaining
- NOTIFICATIONS_READ - Read notifications from Action Center
- NOTIFICATIONS_CHECK - Quick check if notifications exist
- SCREENSHOT - Take a screenshot and save to Pictures/Nexa Screenshots
- SCREENSHOT_CLIPBOARD - Take screenshot and copy to clipboard
- SCREENSHOTS_FOLDER - Open screenshots folder in File Explorer
- SCREENSHOTS_COUNT - Get number of screenshots taken
- LAUNCH_GAME:gamename - Launch a game from Steam, Epic, GOG, or standalone (e.g., LAUNCH_GAME:Counter-Strike)
- LIST_GAMES - List all detected games from all platforms
- LIST_GAMES:platform - List games from specific platform (Steam, Epic, GOG, Standalone)
- OPEN_FOLDER:foldername - Open a folder in File Explorer (e.g., OPEN_FOLDER:downloads)
- FIND_FOLDER:foldername - Find folder location by name
- PLAY_MUSIC - Play random music from library
- PLAY_MUSIC:songname - Play specific song by name (e.g., PLAY_MUSIC:Bohemian Rhapsody)
- PAUSE_MUSIC - Pause currently playing music
- RESUME_MUSIC - Resume paused music
- STOP_MUSIC - Stop music playback completely
- NEXT_SONG - Play next song in library
- PREVIOUS_SONG - Play previous song in library
- WHATS_PLAYING - Get currently playing song information
- LIST_MUSIC - List all songs in music library
- MUSIC_STATS - Get music library statistics (total songs, artists, duration)
- SUGGEST_MUSIC - Suggest random songs from library
- SUGGEST_MUSIC:similar - Suggest songs similar to currently playing track

EXAMPLES:
User: "what time is it?" → {{"action": "system_command", "intent": "check time", "windows_command": "ASK_TIME", "response": "Let me check"}}
User: "are you online?" → {{"action": "system_command", "intent": "check connection mode", "windows_command": "CHECK_MODE", "response": "Let me check"}}
User: "what mode are you in?" → {{"action": "system_command", "intent": "check mode", "windows_command": "CHECK_MODE", "response": "Checking"}}
User: "open calculator" → {{"action": "system_command", "intent": "launch calculator", "windows_command": "OPEN_APP:calculator", "response": "Opening calculator"}}
User: "open chrome" → {{"action": "system_command", "intent": "launch browser", "windows_command": "OPEN_APP:chrome", "response": "Opening Chrome"}}
User: "what apps are running?" → {{"action": "system_command", "intent": "list running apps", "windows_command": "LIST_APPS", "response": "Let me check"}}
User: "list installed applications" → {{"action": "system_command", "intent": "list installed apps", "windows_command": "LIST_INSTALLED_APPS", "response": "Let me check what's installed"}}
User: "what applications do I have?" → {{"action": "system_command", "intent": "list installed apps", "windows_command": "LIST_INSTALLED_APPS", "response": "Let me check"}}
User: "show my apps" → {{"action": "system_command", "intent": "list installed apps", "windows_command": "LIST_INSTALLED_APPS", "response": "Here are your installed apps"}}
User: "find video apps" → {{"action": "system_command", "intent": "search installed apps", "windows_command": "LIST_INSTALLED_APPS:video", "response": "Looking for video apps"}}
User: "refresh app list" → {{"action": "system_command", "intent": "rescan apps", "windows_command": "REFRESH_APPS", "response": "Rescanning for applications"}}
User: "is chrome running?" → {{"action": "system_command", "intent": "check if app running", "windows_command": "APP_RUNNING:chrome", "response": "Checking"}}
User: "close calculator" → {{"action": "system_command", "intent": "close app", "windows_command": "CLOSE_APP:calculator", "response": "Closing calculator"}}
User: "search for python tutorials" → {{"action": "system_command", "intent": "web search", "windows_command": "SEARCH_WEB:python tutorials", "response": "Searching for python tutorials"}}
User: "turn up volume" → {{"action": "system_command", "intent": "increase volume", "windows_command": "VOLUME_UP:10", "response": "Increasing volume"}}
User: "set brightness to 80" → {{"action": "system_command", "intent": "set brightness", "windows_command": "BRIGHTNESS_SET:80", "response": "Setting brightness"}}
User: "disconnect wifi" → {{"action": "system_command", "intent": "disconnect wifi", "windows_command": "WIFI_DISCONNECT", "response": "Disconnecting WiFi"}}
User: "find and select the email address" → {{"action": "system_command", "intent": "smart text selection", "windows_command": "SMART_SELECT:find the email address", "response": "Finding and selecting"}}
User: "copy the word budget" → {{"action": "system_command", "intent": "smart copy", "windows_command": "SMART_COPY:copy the word budget", "response": "Copying"}}
User: "what text is on screen?" → {{"action": "system_command", "intent": "read screen", "windows_command": "READ_SCREEN", "response": "Reading screen"}}
User: "select all" → {{"action": "system_command", "intent": "select all text", "windows_command": "SELECT_ALL", "response": "Selecting all"}}
User: "paste that" → {{"action": "system_command", "intent": "paste", "windows_command": "PASTE", "response": "Pasting"}}
User: "minimize chrome" → {{"action": "system_command", "intent": "minimize window", "windows_command": "WINDOW_MINIMIZE:chrome", "response": "Minimizing Chrome"}}
User: "minimize the chrome window" → {{"action": "system_command", "intent": "minimize window", "windows_command": "WINDOW_MINIMIZE:chrome", "response": "Minimizing Chrome"}}
User: "minimize google chrome" → {{"action": "system_command", "intent": "minimize window", "windows_command": "WINDOW_MINIMIZE:chrome", "response": "Minimizing Chrome"}}
User: "can you minimize chrome?" → {{"action": "system_command", "intent": "minimize window", "windows_command": "WINDOW_MINIMIZE:chrome", "response": "Minimizing Chrome"}}
User: "make chrome smaller" → {{"action": "system_command", "intent": "minimize window", "windows_command": "WINDOW_MINIMIZE:chrome", "response": "Minimizing Chrome"}}
User: "hide chrome" → {{"action": "system_command", "intent": "minimize window", "windows_command": "WINDOW_MINIMIZE:chrome", "response": "Minimizing Chrome"}}
User: "minimize this window" → {{"action": "system_command", "intent": "minimize window", "windows_command": "WINDOW_MINIMIZE:active", "response": "Minimizing window"}}
User: "minimize active window" → {{"action": "system_command", "intent": "minimize window", "windows_command": "WINDOW_MINIMIZE:active", "response": "Minimizing window"}}
User: "maximize chrome" → {{"action": "system_command", "intent": "maximize window", "windows_command": "WINDOW_MAXIMIZE:chrome", "response": "Maximizing Chrome"}}
User: "make chrome fullscreen" → {{"action": "system_command", "intent": "maximize window", "windows_command": "WINDOW_MAXIMIZE:chrome", "response": "Maximizing Chrome"}}
User: "make chrome full screen" → {{"action": "system_command", "intent": "maximize window", "windows_command": "WINDOW_MAXIMIZE:chrome", "response": "Maximizing Chrome"}}
User: "make chrome bigger" → {{"action": "system_command", "intent": "maximize window", "windows_command": "WINDOW_MAXIMIZE:chrome", "response": "Maximizing Chrome"}}
User: "maximize the window" → {{"action": "system_command", "intent": "maximize window", "windows_command": "WINDOW_MAXIMIZE:active", "response": "Maximizing window"}}
User: "expand chrome" → {{"action": "system_command", "intent": "maximize window", "windows_command": "WINDOW_MAXIMIZE:chrome", "response": "Maximizing Chrome"}}
User: "maximize this window" → {{"action": "system_command", "intent": "maximize window", "windows_command": "WINDOW_MAXIMIZE:active", "response": "Maximizing window"}}
User: "hide notepad" → {{"action": "system_command", "intent": "hide window", "windows_command": "WINDOW_HIDE:notepad", "response": "Hiding Notepad"}}
User: "what window is active?" → {{"action": "system_command", "intent": "get active window", "windows_command": "WINDOW_ACTIVE", "response": "Checking"}}
User: "restore calculator" → {{"action": "system_command", "intent": "restore window", "windows_command": "WINDOW_RESTORE:calculator", "response": "Restoring calculator"}}
User: "what's my battery status?" → {{"action": "system_command", "intent": "check battery", "windows_command": "BATTERY_STATUS", "response": "Checking battery"}}
User: "is my laptop charging?" → {{"action": "system_command", "intent": "check charging", "windows_command": "BATTERY_CHARGING", "response": "Checking charging status"}}
User: "battery percentage" → {{"action": "system_command", "intent": "battery level", "windows_command": "BATTERY_PERCENT", "response": "Checking battery level"}}
User: "how much battery time left?" → {{"action": "system_command", "intent": "battery time", "windows_command": "BATTERY_TIME", "response": "Checking time remaining"}}
User: "read my notifications" → {{"action": "system_command", "intent": "read notifications", "windows_command": "NOTIFICATIONS_READ", "response": "Reading notifications"}}
User: "check notifications" → {{"action": "system_command", "intent": "check notifications", "windows_command": "NOTIFICATIONS_CHECK", "response": "Checking for notifications"}}
User: "any notifications?" → {{"action": "system_command", "intent": "check notifications", "windows_command": "NOTIFICATIONS_CHECK", "response": "Let me check"}}
User: "take a screenshot" → {{"action": "system_command", "intent": "capture screen", "windows_command": "SCREENSHOT", "response": "Taking screenshot"}}
User: "screenshot this" → {{"action": "system_command", "intent": "capture screen", "windows_command": "SCREENSHOT", "response": "Capturing screen"}}
User: "screenshot and copy" → {{"action": "system_command", "intent": "screenshot to clipboard", "windows_command": "SCREENSHOT_CLIPBOARD", "response": "Taking screenshot and copying to clipboard"}}
User: "open screenshots folder" → {{"action": "system_command", "intent": "open screenshots", "windows_command": "SCREENSHOTS_FOLDER", "response": "Opening screenshots folder"}}

Game Management Examples (Phase 12):
User: "launch counter strike" → {{"action": "system_command", "intent": "launch game", "windows_command": "LAUNCH_GAME:counter strike", "response": "Launching Counter-Strike"}}
User: "open fortnite" → {{"action": "system_command", "intent": "launch game", "windows_command": "LAUNCH_GAME:fortnite", "response": "Launching Fortnite"}}
User: "start gta 5" → {{"action": "system_command", "intent": "launch game", "windows_command": "LAUNCH_GAME:gta 5", "response": "Starting GTA 5"}}
User: "play valorant" → {{"action": "system_command", "intent": "launch game", "windows_command": "LAUNCH_GAME:valorant", "response": "Launching Valorant"}}
User: "list my games" → {{"action": "system_command", "intent": "list all games", "windows_command": "LIST_GAMES", "response": "Listing your games"}}
User: "what games do I have?" → {{"action": "system_command", "intent": "list games", "windows_command": "LIST_GAMES", "response": "Checking your games"}}
User: "show my steam games" → {{"action": "system_command", "intent": "list steam games", "windows_command": "LIST_GAMES:Steam", "response": "Listing Steam games"}}
User: "list epic games" → {{"action": "system_command", "intent": "list epic games", "windows_command": "LIST_GAMES:Epic", "response": "Listing Epic games"}}

Music Control Examples:
User: "play some music" → {{"action": "system_command", "intent": "play random music", "windows_command": "PLAY_MUSIC", "response": "Playing a random song"}}
User: "play random song" → {{"action": "system_command", "intent": "play music", "windows_command": "PLAY_MUSIC", "response": "Playing music"}}
User: "play bohemian rhapsody" → {{"action": "system_command", "intent": "play specific song", "windows_command": "PLAY_MUSIC:bohemian rhapsody", "response": "Playing Bohemian Rhapsody"}}
User: "play this song" → {{"action": "system_command", "intent": "play music", "windows_command": "PLAY_MUSIC", "response": "Playing a song"}}
User: "pause music" → {{"action": "system_command", "intent": "pause playback", "windows_command": "PAUSE_MUSIC", "response": "Pausing music"}}
User: "pause the song" → {{"action": "system_command", "intent": "pause music", "windows_command": "PAUSE_MUSIC", "response": "Pausing"}}
User: "resume music" → {{"action": "system_command", "intent": "resume playback", "windows_command": "RESUME_MUSIC", "response": "Resuming music"}}
User: "continue playing" → {{"action": "system_command", "intent": "resume music", "windows_command": "RESUME_MUSIC", "response": "Continuing"}}
User: "stop music" → {{"action": "system_command", "intent": "stop playback", "windows_command": "STOP_MUSIC", "response": "Stopping music"}}
User: "next song" → {{"action": "system_command", "intent": "skip to next", "windows_command": "NEXT_SONG", "response": "Playing next song"}}
User: "skip this song" → {{"action": "system_command", "intent": "next song", "windows_command": "NEXT_SONG", "response": "Skipping"}}
User: "previous song" → {{"action": "system_command", "intent": "go to previous", "windows_command": "PREVIOUS_SONG", "response": "Playing previous song"}}
User: "what's playing?" → {{"action": "system_command", "intent": "current track info", "windows_command": "WHATS_PLAYING", "response": "Checking"}}
User: "what song is this?" → {{"action": "system_command", "intent": "identify song", "windows_command": "WHATS_PLAYING", "response": "Let me check"}}
User: "list my music" → {{"action": "system_command", "intent": "list songs", "windows_command": "LIST_MUSIC", "response": "Listing your music"}}
User: "show my songs" → {{"action": "system_command", "intent": "display music library", "windows_command": "LIST_MUSIC", "response": "Showing songs"}}
User: "how many songs do I have?" → {{"action": "system_command", "intent": "music library stats", "windows_command": "MUSIC_STATS", "response": "Checking your library"}}
User: "suggest some music" → {{"action": "system_command", "intent": "get music suggestions", "windows_command": "SUGGEST_MUSIC", "response": "Let me suggest some songs"}}
User: "what should I listen to?" → {{"action": "system_command", "intent": "music recommendations", "windows_command": "SUGGEST_MUSIC", "response": "I have some suggestions"}}
User: "recommend something similar" → {{"action": "system_command", "intent": "similar music", "windows_command": "SUGGEST_MUSIC:similar", "response": "Finding similar songs"}}
User: "suggest music like this" → {{"action": "system_command", "intent": "suggest based on current", "windows_command": "SUGGEST_MUSIC:similar", "response": "Suggesting similar songs"}}

Folder Management Examples (Phase 12):
User: "open downloads folder" → {{"action": "system_command", "intent": "open folder", "windows_command": "OPEN_FOLDER:downloads", "response": "Opening downloads folder"}}
User: "find documents folder" → {{"action": "system_command", "intent": "find folder", "windows_command": "FIND_FOLDER:documents", "response": "Finding documents folder"}}
User: "open my pictures" → {{"action": "system_command", "intent": "open folder", "windows_command": "OPEN_FOLDER:pictures", "response": "Opening pictures folder"}}
User: "where is my projects folder?" → {{"action": "system_command", "intent": "find folder", "windows_command": "FIND_FOLDER:projects", "response": "Looking for projects folder"}}
User: "show me desktop folder" → {{"action": "system_command", "intent": "open folder", "windows_command": "OPEN_FOLDER:desktop", "response": "Opening desktop folder"}}

Screen Analysis Examples (Phase 8):
User: "what's on my screen?" → {{"action": "system_command", "intent": "describe screen content", "windows_command": "DESCRIBE_SCREEN", "response": "Let me look at your screen"}}
User: "what am I looking at?" → {{"action": "system_command", "intent": "analyze screen", "windows_command": "DESCRIBE_SCREEN", "response": "Analyzing what's visible"}}
User: "describe this window" → {{"action": "system_command", "intent": "describe screen", "windows_command": "DESCRIBE_SCREEN", "response": "Describing the window"}}
User: "read what's visible" → {{"action": "system_command", "intent": "read screen text", "windows_command": "READ_SCREEN", "response": "Reading the screen"}}
User: "what does this say?" → {{"action": "system_command", "intent": "read text on screen", "windows_command": "READ_SCREEN", "response": "Reading the text"}}
User: "read this screen" → {{"action": "system_command", "intent": "extract screen text", "windows_command": "READ_SCREEN", "response": "Extracting text"}}
User: "analyze this screen" → {{"action": "system_command", "intent": "comprehensive screen analysis", "windows_command": "SCREEN_ANALYZE", "response": "Analyzing screen content"}}
User: "what's this about?" → {{"action": "system_command", "intent": "understand screen content", "windows_command": "SCREEN_ANALYZE", "response": "Let me analyze this"}}
User: "tell me about this" → {{"action": "system_command", "intent": "explain screen content", "windows_command": "SCREEN_ANALYZE", "response": "Analyzing"}}
User: "summarize what's visible" → {{"action": "system_command", "intent": "summarize screen", "windows_command": "SCREEN_ANALYZE", "response": "Summarizing screen content"}}

Auto-Detection Examples (when context is unclear):
User: "what's that?" → {{"action": "conversation", "intent": "clarification_or_screen_analysis", "response": "I'm not sure what you're referring to. Would you like me to analyze what's on your screen?"}}
User: "what is this?" → {{"action": "conversation", "intent": "clarification_or_screen_analysis", "response": "Would you like me to look at what's on your screen?"}}
User: "explain this" → {{"action": "conversation", "intent": "needs_context", "response": "I need more context. Should I analyze what's visible on your screen?"}}
User: "help me understand this" → {{"action": "conversation", "intent": "needs_context", "response": "Should I look at your screen to help you understand?"}}
User: "what does it do?" → {{"action": "conversation", "intent": "needs_context", "response": "I need more information. Would you like me to analyze what's on your screen?"}}


WiFi Management Examples:
User: "disconnect wifi" → {{"action": "system_command", "intent": "disconnect from wifi", "windows_command": "WIFI_DISCONNECT", "response": "Disconnecting from WiFi"}}
User: "what's my wifi status?" → {{"action": "system_command", "intent": "check wifi status", "windows_command": "WIFI_STATUS", "response": "Checking WiFi"}}
User: "show available wifi networks" → {{"action": "system_command", "intent": "list wifi networks", "windows_command": "WIFI_LIST", "response": "Scanning for networks"}}
User: "what wifi networks are nearby?" → {{"action": "system_command", "intent": "list wifi networks", "windows_command": "WIFI_LIST", "response": "Let me scan"}}
User: "list wifi connections" → {{"action": "system_command", "intent": "list wifi networks", "windows_command": "WIFI_LIST", "response": "Checking available networks"}}
User: "show my saved wifi networks" → {{"action": "system_command", "intent": "get wifi profiles", "windows_command": "WIFI_PROFILES", "response": "Checking saved networks"}}
User: "connect to HomeNetwork" → {{"action": "system_command", "intent": "connect to specific wifi", "windows_command": "WIFI_CONNECT:HomeNetwork", "response": "Connecting to HomeNetwork"}}
User: "connect to the Office5G network" → {{"action": "system_command", "intent": "connect to specific wifi", "windows_command": "WIFI_CONNECT:Office5G", "response": "Connecting to Office5G"}}
User: "go online" → {{"action": "system_command", "intent": "connect to wifi", "windows_command": "WIFI_PROFILES", "response": "Let me connect you to WiFi"}}
User: "connect to wifi" → {{"action": "system_command", "intent": "reconnect to wifi", "windows_command": "WIFI_PROFILES", "response": "Reconnecting to WiFi"}}

IMPORTANT WiFi Connection Rules:
- When user says "connect to [NetworkName]" → Extract the exact network name and use WIFI_CONNECT:NetworkName
- Network names are case-sensitive and must match exactly
- User can say: "connect to X", "connect me to X", "join X network", "switch to X wifi"
- Examples: "connect to HomeWiFi" → WIFI_CONNECT:HomeWiFi, "join Office5G" → WIFI_CONNECT:Office5G

CRITICAL WiFi Reconnection Workflow:
When user says "turn on wifi", "connect to wifi", "reconnect wifi", or "go online":
Step 1: ALWAYS use WIFI_PROFILES first to get the last used/saved network name
Step 2: Extract the actual network name from the response (e.g., "Last used network: MyHomeWiFi" → use "MyHomeWiFi")
Step 3: Then use WIFI_CONNECT:MyHomeWiFi with the actual network name
NEVER use WIFI_CONNECT:networkname literally - "networkname" is just a placeholder!

IMPORTANT: "go online" means connect to WiFi so full features can work. User cannot access internet-based features without WiFi connection!

Example workflow:
User says "connect to wifi" or "go online" → 
Response 1: {{"action": "system_command", "intent": "check saved wifi profiles", "windows_command": "WIFI_PROFILES", "response": "Let me check your saved networks"}}
Then after getting "Last used network: HomeNetwork" →
Response 2: {{"action": "system_command", "intent": "connect to wifi", "windows_command": "WIFI_CONNECT:HomeNetwork", "response": "Connecting to WiFi"}}

For normal conversation (jokes, questions about topics, explanations), respond WITHOUT JSON - just natural text.

User request: {user_text}"""

            # ⏱️ TIMING: Start LLM generation
            import time
            start_llm = time.time()
            logger.debug(f"⏱️ Starting LLM generation...")
            
            # Get AI response using LLM Manager (auto-fallback to offline if needed)
            response_text, mode_used = self.llm_manager.generate_response(
                system_prompt,
                temperature=0.3,
                max_output_tokens=200
            )
            
            # ⏱️ TIMING: LLM generation complete
            time_llm = time.time() - start_llm
            logger.info(f"⏱️ LLM generation took {time_llm:.3f}s")
            
            # Store the mode that was actually used for this response
            self.llm_manager.current_mode = mode_used
            
            # CRITICAL FIX: Remove "Nexa:" prefix if Gemma3 adds it
            if response_text.startswith("Nexa:"):
                response_text = response_text[5:].strip()
            
            # Log mode and response
            logger.debug(f"🤖 Mode: {mode_used.value}")
            logger.info(f"💬 Nexa: {response_text[:150]}{'...' if len(response_text) > 150 else ''}")
            
            # ⏱️ TIMING: Start JSON parsing
            start_parse = time.time()
            
            # Notify user if switched to offline mode
            if mode_used == LLMMode.OFFLINE and self.llm_manager.current_mode != LLMMode.OFFLINE:
                offline_notice = "I'm currently offline. Basic features are available. "
                response_text = offline_notice + response_text
            
            # CRITICAL FIX: If Llama3 mentions being in offline mode unnecessarily
            # Only trigger if response is too verbose about the mode itself
            if mode_used == LLMMode.OFFLINE and '{' not in response_text:
                # Check for overly verbose mode explanations (not in JSON responses)
                hallucination_detected = False
                response_lower = response_text.lower()
                
                # Pattern 1: Unnecessarily mentions being in offline mode
                if ("offline mode" in response_lower and "llama" in response_lower) or \
                   ("using llama" in response_lower) or \
                   ("i'm ready to assist you in offline mode" in response_lower) or \
                   ("this is a plain text response" in response_lower):
                    hallucination_detected = True
                
                # Pattern 2: Asks for user request instead of answering
                if "please provide a user request" in response_lower or \
                   "provide a user request or input" in response_lower:
                    hallucination_detected = True
                
                if hallucination_detected:
                    logger.warning(f"🔴 Llama3 gave verbose mode explanation - simplifying")
                    logger.warning(f"   Original response: {response_text[:100]}")
                    
                    # Check what user actually asked
                    if "game" in user_text.lower():
                        response_text = "Let me check your games."
                    elif "how are you" in user_text.lower():
                        response_text = "I'm doing great, thanks for asking!"
                    else:
                        response_text = "I'm here and ready to help."
            
            # Check for simple confirmation responses (yes, no, continue, etc.)
            user_lower = user_text.lower().strip()
            confirmation_words = ['yes', 'yeah', 'yep', 'sure', 'okay', 'ok', 'do it', 'go ahead', 'continue', 'proceed']
            rejection_words = ['no', 'nope', 'cancel', 'stop', 'nevermind', 'never mind', 'don\'t']
            
            # Check if user is confirming a pending action
            if self.context_manager.has_pending_action():
                is_confirmation = any(word in user_lower for word in confirmation_words)
                is_rejection = any(word in user_lower for word in rejection_words)
                
                if is_confirmation:
                    # User confirmed - execute pending action
                    pending = self.context_manager.get_pending_action()
                    logger.info(f"✅ User confirmed pending action: {pending}")
                    
                    action_data = pending.get('data', {})
                    action_type = pending.get('type', '')
                    windows_command = action_data.get('command', '')
                    
                    # Check if this is a screen analysis action - grant consent
                    if action_type == 'screen_analysis':
                        self._grant_screen_privacy_consent()
                        logger.info("✅ Screen analysis consent granted permanently")
                    
                    if windows_command:
                        # Re-execute the command
                        logger.info(f"🔄 Executing confirmed action: {windows_command}")
                        # Create a JSON response to trigger command execution
                        response_text = f'{{"action": "system_command", "intent": "execute confirmed action", "windows_command": "{windows_command}", "response": "Done!"}}'
                    else:
                        return "I'll proceed with that."
                
                elif is_rejection:
                    # User rejected - clear pending action
                    self.context_manager.clear_pending_action()
                    logger.info("❌ User rejected pending action")
                    return "Okay, I won't do that."
            
            # Check if it's a system command (JSON response)
            # Handle NEW function calling format for Gemma3 OR old keyword format for Gemini
            import json
            # Note: re is imported at module level (line 11)
            
            json_match = None
            
            # CRITICAL FIX: Strip markdown code blocks (Gemma3 wraps JSON in ```json blocks)
            cleaned_response = response_text
            if '```json' in response_text or '```' in response_text:
                # Remove markdown code block markers
                cleaned_response = re.sub(r'```json\s*', '', response_text)
                cleaned_response = re.sub(r'```\s*', '', cleaned_response)
                cleaned_response = cleaned_response.strip()
                logger.debug(f"🧹 Stripped markdown blocks: {cleaned_response[:100]}")
            
            # Try to extract JSON from response
            if '{' in cleaned_response:
                # Look for ANY JSON response (function_call, action, or just response)
                if '"function_call"' in cleaned_response or '"action"' in cleaned_response or '"response"' in cleaned_response:
                    # Try to find complete JSON object (handle nested braces)
                    # Use a more robust pattern that handles nested objects
                    try:
                        # Find the first { and try to parse from there
                        start_idx = cleaned_response.find('{')
                        if start_idx != -1:
                            # Try to parse the JSON starting from first brace
                            potential_json = cleaned_response[start_idx:]
                            # Attempt to load it - json.loads will validate structure
                            test_parse = json.loads(potential_json)
                            json_match = potential_json
                            logger.debug(f"✅ Extracted complete JSON object")
                    except json.JSONDecodeError:
                        # Fallback to regex pattern for simple cases
                        json_pattern = r'\{[^{}]*(?:"function_call"|"action"|"response")[^{}]*\}'
                        matches = re.findall(json_pattern, cleaned_response, re.DOTALL | re.MULTILINE)
                        if matches:
                            json_match = matches[0]
                            logger.debug(f"✅ Extracted JSON via regex: {json_match[:100]}")
                    
                    if not json_match and cleaned_response.strip().startswith('{'):
                        json_match = cleaned_response.strip()
            
            if json_match:
                try:
                    response_data = json.loads(json_match)
                    
                    # ⏱️ TIMING: JSON parsing complete
                    time_parse = time.time() - start_parse
                    logger.debug(f"⏱️ JSON parsing took {time_parse:.3f}s")
                    logger.debug(f"✅ JSON parsed successfully: {list(response_data.keys())}")
                    
                    # NEW: Dynamic function calling (Gemma3)
                    if "function_call" in response_data:
                        func_call = response_data["function_call"]
                        func_name = func_call.get("name", "")
                        func_params = func_call.get("parameters", {})
                        user_response = response_data.get("response", "Done!")
                        
                        # CRITICAL FIX: If user_response is empty, set a default
                        if not user_response or user_response.strip() == "":
                            user_response = "Processing..."
                            logger.debug(f"⚠️ Empty user_response, using default: '{user_response}'")
                        
                        logger.info(f"🔧 Dynamic function call detected")
                        logger.info(f"   Function: {func_name}")
                        logger.info(f"   Parameters: {func_params}")
                        logger.info(f"   User message: {user_response[:50]}")
                        
                        # COMPREHENSIVE VALIDATION (CR-12, CR-13, CR-14): Validate before execution
                        is_valid, error_msg = self.validate_function_call(func_name, func_params)
                        if not is_valid:
                            logger.error(f"❌ VALIDATION FAILED: {error_msg}")
                            return error_msg
                        
                        # VALIDATION 7: Unclear/vague command detection (CR-14)
                        # If AI picked a fallback function with no context, user command was likely unclear
                        last_action_result = self.context_manager.get_last_action()
                        if isinstance(last_action_result, dict):
                            last_action = last_action_result.get('action', '')
                        else:
                            last_action, _ = last_action_result
                        
                        # Check for unclear commands - AI falls back to get_current_time when confused
                        unclear_indicators = [
                            (func_name == 'get_current_time' and not last_action),  # Time query without context
                            (func_name == 'get_current_time' and 'time' not in user_text.lower() and 'date' not in user_text.lower()),  # Not a time query
                        ]
                        
                        # Check if user command was vague
                        vague_commands = ['do the thing', 'do it', 'do that', 'go ahead', 'you know', 'the usual', 'same as before']
                        is_vague = any(vague.lower() in user_text.lower() for vague in vague_commands)
                        
                        if is_vague and func_name == 'get_current_time':
                            logger.warning(f"⚠️ UNCLEAR COMMAND DETECTED: '{user_text}' resulted in fallback function")
                            return ("I'm not sure what you'd like me to do. Could you be more specific? "
                                   "For example, you can ask me to open an app, play music, take a screenshot, or control windows.")
                        
                        # ⏱️ TIMING: Start function execution
                        start_exec = time.time()
                        
                        # 🧠 DYNAMIC FOLLOW-UP DETECTION (Universal - works for ALL commands)
                        last_action_result = self.context_manager.get_last_action()
                        
                        # Handle both tuple (legacy) and dict (new action stack) formats
                        if isinstance(last_action_result, dict):
                            last_action = last_action_result.get('action', '')
                            last_data = last_action_result.get('data', {})
                        else:
                            last_action, last_data = last_action_result
                        
                        is_follow_up = False
                        
                        logger.info(f"🔍 Follow-up check: last_action={last_action}, user_text='{user_text[:50]}'")
                        
                        # Detect if current request is a follow-up to last action
                        if last_action:
                            user_text_lower = user_text.lower()
                            
                            # Universal follow-up patterns (EXPANDED: 17 → 50+ patterns for better NLP coverage)
                            follow_up_patterns = [
                                # Original patterns (17)
                                "what are those", "what are they", "which ones", "what games",
                                "what apps", "tell me", "list them", "show them", "what's on it",
                                "which", "what networks", "what folders", "what are the",
                                "tell me their names", "give me details", "more details",
                                "elaborate", "expand", "full list", "all of them",
                                
                                # NEW: Variations and natural language additions (33 more)
                                "what were they", "which were those", "show names", "game list",
                                "app list", "list names", "their names", "the names", "name them",
                                "what are the names", "give me the names", "show me the list",
                                "full details", "complete list", "everything", "all items",
                                "what did you find", "what was found", "show results",
                                "the results", "those items", "these items", "the list",
                                "tell me the list", "enumerate them", "count them",
                                "how many", "what's the count", "quantity", "total number",
                                "show all", "display all", "list all", "give me all"
                            ]
                            
                            # METHOD 1: Pattern-based detection (FAST - no LLM call)
                            matched_pattern = None
                            for pattern in follow_up_patterns:
                                if pattern in user_text_lower:
                                    matched_pattern = pattern
                                    break
                            
                            if matched_pattern:
                                logger.info(f"🔗 Follow-up detected (pattern)! '{matched_pattern}', Last action: {last_action}")
                                is_follow_up = True
                            else:
                                # METHOD 2: AI-based detection (SMART - uses LLM when patterns fail)
                                # CRITICAL: Only use AI detection for ambiguous/short queries
                                # Skip for clear new commands (open, close, list, set, etc.)
                                word_count = len(user_text.split())
                                
                                # Pre-filter: Skip AI check if query contains clear action verbs
                                action_verbs = ['open', 'close', 'launch', 'start', 'stop', 'list', 
                                              'show', 'set', 'change', 'increase', 'decrease', 
                                              'take', 'search', 'find', 'get', 'check']
                                has_action_verb = any(verb in user_text_lower for verb in action_verbs)
                                
                                # Only use AI detection if:
                                # 1. Offline mode (online has better context)
                                # 2. Short query (<12 words)
                                # 3. No clear action verb (might be vague follow-up like "what were they?")
                                if (self.llm_manager.current_mode == LLMMode.OFFLINE and 
                                    word_count < 12 and 
                                    not has_action_verb):
                                    logger.info(f"🤖 Trying smart follow-up detection (ambiguous query)...")
                                    last_result_preview = str(last_data.get('result', ''))[:100] if last_data else ""
                                    
                                    # Get available functions dynamically from registry
                                    available_funcs = list(self.executor.function_registry.functions.keys())
                                    
                                    is_follow_up = self.llm_manager.is_follow_up_question(
                                        user_text=user_text,
                                        last_action=last_action,
                                        last_result=last_result_preview,
                                        available_functions=available_funcs
                                    )
                                else:
                                    logger.debug(f"   Skipping AI check: clear_action={has_action_verb}, words={word_count}")
                            
                            # ENHANCED FOLLOW-UP CORRECTION LOGIC
                            # If follow-up detected, verify function makes sense with last action
                            if is_follow_up and last_action:
                                # Get categories of both functions
                                detected_category = self._get_function_category(func_name)
                                last_action_category = self._get_function_category(last_action)
                                
                                logger.debug(f"🔍 Follow-up validation: {func_name} ({detected_category}) vs {last_action} ({last_action_category})")
                                
                                # Determine if correction is needed
                                needs_correction = False
                                
                                # RULE 0: If query explicitly asks for a NEW operation (not follow-up), don't correct
                                # Check for queries that are clearly new commands, not follow-ups
                                explicit_new_queries = [
                                    'what apps', 'which apps', 'list apps', 'running apps',
                                    'what wifi', 'which wifi', 'list wifi', 'wifi networks',
                                    'what games', 'which games', 'list games', 'available games',
                                    'list all', 'show all', 'get all', 'what are all'
                                ]
                                is_explicit_new = any(pattern in user_text_lower for pattern in explicit_new_queries)
                                
                                if is_explicit_new:
                                    # This is a new query, not a follow-up to previous action
                                    # EXCEPTION: Only correct if same domain (e.g., "what apps" after "list apps")
                                    same_domain = (
                                        ('apps' in user_text_lower or 'running' in user_text_lower) and 
                                        func_name == 'get_running_applications' and 
                                        last_action == 'get_running_applications'
                                    ) or (
                                        ('wifi' in user_text_lower or 'network' in user_text_lower) and
                                        func_name == 'list_wifi_networks' and
                                        last_action == 'list_wifi_networks'
                                    ) or (
                                        ('game' in user_text_lower) and
                                        func_name == 'list_games' and
                                        last_action == 'list_games'
                                    )
                                    
                                    if same_domain:
                                        logger.info(f"✓ Same-domain follow-up - allowing correction")
                                    else:
                                        logger.info(f"✓ Query is explicit new command, not a follow-up - no correction needed")
                                        needs_correction = False
                                
                                # RULE 1: If AI picked default/fallback function (get_current_time), always correct
                                elif func_name == "get_current_time":
                                    needs_correction = True
                                    logger.info(f"⚠️ Follow-up used default function - correcting")
                                
                                # RULE 2: If last action was info query, follow-up should be same function
                                # (e.g., "list games" → "what are they?" should re-call list_games)
                                elif last_action_category == 'info_query' and func_name != last_action:
                                    # Exception: If new function is also info query in same domain, allow it
                                    # (e.g., "list games" → "how many?" could use different function)
                                    if detected_category != 'info_query':
                                        needs_correction = True
                                        logger.info(f"⚠️ Follow-up to info query used non-info function - correcting")
                                
                                # RULE 3: If categories completely mismatch, likely wrong
                                # (e.g., "list games" (gaming) → AI picks "list_wifi_networks" (network))
                                elif detected_category != last_action_category and detected_category != 'other':
                                    # Check if it's a reasonable category switch
                                    reasonable_switches = {
                                        ('gaming', 'app_control'),  # list games → open game
                                        ('app_control', 'window_mgmt'),  # open app → maximize
                                        ('app_control', 'info_query'),  # close app → what apps running
                                        ('window_mgmt', 'info_query'),  # minimize → what's active
                                        ('network', 'info_query'),  # network op → check status
                                        ('screen', 'file'),  # screenshot → save location
                                        ('info_query', 'app_control'),  # check running → close app
                                        ('info_query', 'window_mgmt'),  # check active → minimize
                                    }
                                    
                                    category_pair = (last_action_category, detected_category)
                                    if category_pair not in reasonable_switches:
                                        needs_correction = True
                                        logger.warning(f"⚠️ Category mismatch: {last_action_category} → {detected_category}")
                                
                                # RULE 4: Specific known problematic cases (DISABLED - RULE 0 handles these better)
                                # The explicit new command detection (RULE 0) correctly identifies when user
                                # is asking for a different domain (e.g., "what apps" after "list wifi")
                                # This rule was causing false corrections, so it's been disabled.
                                
                                # RULE 5: User query contains explicit category keywords - DON'T correct
                                # If user says "games", don't correct to music function, etc.
                                category_keywords = {
                                    'games': ['game', 'games', 'gaming', 'tekken', 'play game'],
                                    'music': ['music', 'song', 'songs', 'spotify', 'playlist', 'track'],
                                    'network': ['wifi', 'network', 'internet', 'connection'],
                                    'app_control': ['app', 'apps', 'application', 'open', 'close', 'launch'],
                                    'memory': ['memory', 'memories', 'remember', 'forgot', 'know about'],
                                }
                                
                                # Check if user's query clearly mentions a different category
                                user_mentioned_category = None
                                for cat, keywords in category_keywords.items():
                                    if any(kw in user_text_lower for kw in keywords):
                                        user_mentioned_category = cat
                                        break
                                
                                # If user explicitly mentions a category and last_action is different, DON'T correct
                                if user_mentioned_category:
                                    last_action_matches = False
                                    if user_mentioned_category == 'games' and 'game' in last_action.lower():
                                        last_action_matches = True
                                    elif user_mentioned_category == 'music' and 'music' in last_action.lower():
                                        last_action_matches = True
                                    elif user_mentioned_category == 'network' and ('wifi' in last_action.lower() or 'network' in last_action.lower()):
                                        last_action_matches = True
                                    elif user_mentioned_category == 'app_control' and 'app' in last_action.lower():
                                        last_action_matches = True
                                    elif user_mentioned_category == 'memory' and 'memory' in last_action.lower():
                                        last_action_matches = True
                                    
                                    if not last_action_matches:
                                        needs_correction = False
                                        logger.info(f"✓ User explicitly asked about '{user_mentioned_category}' - keeping {func_name}, not correcting to {last_action}")
                                
                                # Apply correction if needed, BUT only if target function exists
                                if needs_correction:
                                    # SAFETY CHECK: Verify last_action function exists before correcting
                                    if last_action in self.executor.function_registry.functions:
                                        original_func = func_name
                                        func_name = last_action
                                        logger.info(f"✅ CORRECTED: {original_func} → {func_name} (follow-up to {last_action})")
                                    else:
                                        logger.warning(f"⚠️ Cannot correct to '{last_action}' - function doesn't exist! Keeping {func_name}")
                                        needs_correction = False
                                else:
                                    logger.debug(f"✓ Follow-up function validated: {func_name}")
                        
                        # Add is_follow_up to parameters if function supports it
                        if is_follow_up and func_name in ['list_games', 'get_running_applications', 
                                                            'list_wifi_networks', 'find_folder']:
                            func_params['is_follow_up'] = True
                            logger.info(f"✅ Added is_follow_up=True to {func_name} parameters")
                        
                        # OPTIMIZATION: Try to answer from cache if it's a follow-up question
                        if is_follow_up and last_action:
                            # Get last result from action stack
                            last_action_data = self.context_manager.get_last_action()
                            if isinstance(last_action_data, dict):
                                last_result = last_action_data.get('result', '')
                            else:
                                _, last_data = last_action_data
                                last_result = last_data.get('result', '')
                            
                            # Try to answer from cached data
                            cached_answer = self._answer_from_cache(user_text, last_action, last_result)
                            if cached_answer:
                                logger.info(f"⚡ CACHE HIT: Answered follow-up from cached data (no re-execution)")
                                return cached_answer
                            else:
                                logger.debug(f"💾 Cache miss - will execute function normally")
                        
                        # CLARIFICATION CHECK: Does this command need clarification?
                        clarification_question = self._requires_clarification(user_text, func_name, func_params)
                        if clarification_question:
                            # Ask user for clarification instead of executing
                            return self._ask_clarification(clarification_question)
                        
                        # EDGE CASE VALIDATION: Semantic type validation
                        if self.input_validator and self.enable_input_validation:
                            # Validate semantic correctness (e.g., can't "open volume")
                            action_verb = self._extract_action_verb(user_text)
                            target = func_params.get('app_name') or func_params.get('folder_name') or func_params.get('parameter', '')
                            
                            if action_verb and target:
                                is_valid, error_msg = self.input_validator.validate_semantic_type(action_verb, target)
                                if not is_valid:
                                    logger.warning(f"⚠️ Semantic validation failed: {error_msg}")
                                    return error_msg
                            
                            # Validate numeric ranges (volume, brightness 0-100)
                            if func_name in ['set_volume', 'set_brightness'] and 'level' in func_params:
                                level = func_params['level']
                                param_name = 'volume' if 'volume' in func_name else 'brightness'
                                is_valid, error_msg = self.input_validator.validate_numeric_range(param_name, level)
                                if not is_valid:
                                    logger.warning(f"⚠️ Range validation failed: {error_msg}")
                                    return error_msg
                            
                            # Validate existence for window operations
                            if func_name in ['close_window', 'minimize_window', 'maximize_window', 'restore_window']:
                                app_name = func_params.get('app_name', '') or func_params.get('identifier', '')
                                if app_name:
                                    # For window operations, check if WINDOW exists (not just process)
                                    window_exists = self.executor.window_exists(app_name)
                                    
                                    is_valid, error_msg = self.input_validator.validate_existence('window', app_name, window_exists)
                                    if not is_valid:
                                        logger.warning(f"⚠️ Existence validation failed: {error_msg}")
                                        return error_msg
                            
                            # Validate existence for close_application (process-based)
                            if func_name == 'close_application':
                                app_name = func_params.get('app_name', '')
                                if app_name:
                                    # For close app, check if process is running
                                    # is_application_running returns a boolean (True/False)
                                    is_running = self.executor.is_application_running(app_name)
                                    
                                    is_valid, error_msg = self.input_validator.validate_existence('app', app_name, is_running)
                                    if not is_valid:
                                        logger.warning(f"⚠️ Existence validation failed: {error_msg}")
                                        return error_msg
                        
                        # PHASE B: Pre-execution validation (faster failure detection)
                        # Check if command will fail BEFORE executing
                        if func_name == 'open_application':
                            app_name = func_params.get('app_name', '')
                            if app_name:
                                # Check if app exists via discovery
                                app_info = self.executor.app_discovery.find_app(app_name)
                                
                                if not app_info:
                                    # App not found - suggest alternatives
                                    error_msg = f"I couldn't find '{app_name}' on your computer. "
                                    
                                    # Try fuzzy matching for suggestions
                                    similar_apps = self._find_similar_apps(app_name)
                                    if similar_apps:
                                        error_msg += f"Did you mean: {', '.join(similar_apps[:3])}?"
                                    else:
                                        error_msg += "Try saying 'list applications' to see what's installed."
                                    
                                    logger.warning(f"⚠️ Pre-execution check: App '{app_name}' not found")
                                    return error_msg  # Return error immediately without execution
                        
                        # Execute function dynamically via registry
                        try:
                            result = self.executor.function_registry.call(func_name, func_params)
                            
                            # PHASE 29: Record activity for pattern learning
                            self._record_activity_pattern(func_name, "command")
                            
                            # Store this action in action stack for multi-step context
                            self.context_manager.push_action(
                                action=func_name,
                                data=func_params,
                                result=result
                            )
                            
                            # NEW: Learn user preferences from actions
                            self._learn_from_action(func_name, func_params)
                            
                            # ⏱️ TIMING: Function execution complete
                            time_exec = time.time() - start_exec
                            logger.info(f"✅ Function '{func_name}' executed successfully ({time_exec:.3f}s)")
                            logger.info(f"   Result: {result[:100] if isinstance(result, str) else result}")
                            
                            # CRITICAL FIX V2: Prevent hallucinations by validating results
                            # Information queries always return actual result
                            # Actions check for errors before returning AI's optimistic response
                            
                            # DYNAMIC: Detect information vs action functions by pattern
                            is_info_function = self._is_information_function(func_name)
                            
                            if is_info_function and isinstance(result, str):
                                # Information query - always return actual result
                                logger.debug(f"ℹ️ Returning actual result for information query: {func_name}")
                                return result
                            else:
                                # Action command - VALIDATE result before returning AI message
                                # This prevents hallucinations like "Opening XYZ" when app doesn't exist
                                if self._is_error_result(result):
                                    # Function failed - return actual error message
                                    logger.warning(f"⚠️ Function {func_name} failed, returning error: {result[:100]}")
                                    return result
                                else:
                                    # Function succeeded - return result OR user-friendly AI message
                                    # CRITICAL FIX: If user_response is "Processing...", return actual result
                                    if user_response == "Processing...":
                                        logger.debug(f"💬 Returning actual result (no AI message): {result[:100] if isinstance(result, str) else str(result)[:100]}")
                                        return result
                                    # CRITICAL FIX: For content functions (refine, summarize), return the actual content, not AI message
                                    elif func_name in ['refine_text', 'create_pdf'] and isinstance(result, str) and len(result) > 100:
                                        # Long text result (refined/generated content) - return it directly
                                        logger.debug(f"💬 Returning content result for {func_name}: {result[:100]}...")
                                        return result
                                    else:
                                        logger.debug(f"💬 Function succeeded, returning AI message: {user_response[:100]}")
                                        return user_response
                        except Exception as e:
                            logger.error(f"❌ Function execution failed: {e}")
                            return f"I tried to {user_response.lower()}, but encountered an error: {str(e)}"
                    
                    # NEW: Just conversation (Gemma3 - no function call)
                    elif "response" in response_data and "action" not in response_data:
                        # Pure conversation response
                        conversation_response = response_data.get("response", "")
                        
                        # ⏱️ TIMING: Total processing time
                        time_total = time.time() - start_llm
                        logger.info(f"💬 Conversation response: {conversation_response[:50]}")
                        logger.info(f"⏱️ Total processing time: {time_total:.3f}s")
                        return conversation_response
                    
                    # OLD: Hardcoded keyword system - Keep for backwards compatibility
                    elif response_data.get('action') in ['system_command', 'music_command']:
                        intent = response_data.get('intent', 'unknown')
                        # Handle both 'windows_command' and 'music_command' fields
                        windows_command = response_data.get('windows_command', '') or response_data.get('music_command', '')
                        user_response = response_data.get('response', 'Done!')
                        
                        logger.info(f"⚙️ Legacy system command detected")
                        logger.info(f"   Intent: {intent}")
                        logger.info(f"   Command: {windows_command}")
                        
                        # Execute based on command type
                        if windows_command == 'ASK_TIME':
                            # Get real system time
                            result = self.executor.get_current_time()
                            logger.info(f"✅ Time result: {result}")
                            return result
                        
                        elif windows_command == 'CHECK_MODE':
                            # PHASE 24: Check mode - same model (Llama 3.1 8B), different feature availability
                            mode = self.llm_manager.current_mode
                            if mode == LLMMode.ONLINE:
                                result = "I'm currently online. Internet-dependent features (vision, web search, weather) are available. Using Llama 3.1 8B."
                            else:
                                result = "I'm currently offline. All core features work perfectly, but internet-dependent features (vision, web search, weather) are disabled. Using Llama 3.1 8B."
                            logger.info(f"✅ Mode check (Phase 24): {result}")
                            return result
                        
                        elif windows_command.startswith('OPEN_APP:'):
                            # Open application
                            app_name = windows_command.replace('OPEN_APP:', '').strip()
                            result = self.executor.open_application(app_name)
                            logger.info(f"✅ App launch: {result}")
                            
                            # Check if app was not found and provide helpful feedback
                            if "Could not find" in result or "not found" in result.lower():
                                return f"I couldn't find '{app_name}' on your computer. It may not be installed, or it might have a different name. Would you like me to list installed applications?"
                            
                            return result
                        
                        # ===== APP MANAGEMENT =====
                        elif windows_command == 'LIST_APPS':
                            # List running applications (background processes)
                            result = self.executor.get_running_applications()
                            logger.info(f"✅ Running apps: {result}")
                            return result
                        
                        elif windows_command == 'LIST_INSTALLED_APPS':
                            # List all installed applications on the system
                            result = self.executor.get_installed_applications()
                            logger.info(f"✅ Installed apps: {result[:100]}...")
                            return result
                        
                        elif windows_command.startswith('LIST_INSTALLED_APPS:'):
                            # Search installed apps by keyword
                            search_query = windows_command.split(':', 1)[1].strip()
                            result = self.executor.get_installed_applications(search_query=search_query)
                            logger.info(f"✅ Installed apps search '{search_query}': {result[:100]}...")
                            return result
                        
                        elif windows_command == 'REFRESH_APPS':
                            # Force re-scan of installed applications
                            result = self.executor.refresh_installed_apps()
                            logger.info(f"✅ Apps refreshed: {result}")
                            return result
                        
                        elif windows_command.startswith('APP_RUNNING:'):
                            # Check if specific app is running
                            app_name = windows_command.split(':', 1)[1].strip()
                            is_running = self.executor.is_application_running(app_name)
                            result = f"{app_name} is {'running' if is_running else 'not running'}"
                            logger.info(f"✅ App check: {result}")
                            return result
                        
                        elif windows_command.startswith('CLOSE_APP:'):
                            # Close application
                            app_name = windows_command.split(':', 1)[1].strip()
                            result = self.executor.close_application(app_name)
                            logger.info(f"✅ App closed: {result}")
                            return result
                        
                        elif windows_command.startswith('SEARCH_WEB:'):
                            # PHASE 24: Web search requires internet (online mode)
                            if self.llm_manager.current_mode != LLMMode.ONLINE:
                                result = "Web search requires internet connection. I'm currently offline. Please connect to WiFi to search the web."
                                logger.warning("⚠️ Web search blocked - offline mode (Phase 24)")
                                return result
                            
                            # Search web using default browser
                            query = windows_command.split(':', 1)[1].strip()
                            result = self.executor.search_web(query)
                            logger.info(f"✅ Web search: {result}")
                            return result
                        
                        # ===== VOLUME CONTROLS =====
                        elif windows_command.startswith('VOLUME_UP:'):
                            amount = int(windows_command.split(':')[1]) if ':' in windows_command else 10
                            result = self.executor.increase_volume(amount)
                            logger.info(f"✅ Volume increased: {result}")
                            return result
                        
                        elif windows_command.startswith('VOLUME_DOWN:'):
                            amount = int(windows_command.split(':')[1]) if ':' in windows_command else 10
                            result = self.executor.decrease_volume(amount)
                            logger.info(f"✅ Volume decreased: {result}")
                            return result
                        
                        elif windows_command.startswith('VOLUME_SET:'):
                            level = int(windows_command.split(':')[1])
                            result = self.executor.set_volume(level)
                            logger.info(f"✅ Volume set: {result}")
                            return result
                        
                        elif windows_command == 'VOLUME_MUTE':
                            result = self.executor.mute_volume()
                            logger.info(f"✅ Volume muted: {result}")
                            return result
                        
                        elif windows_command == 'VOLUME_UNMUTE':
                            result = self.executor.unmute_volume()
                            logger.info(f"✅ Volume unmuted: {result}")
                            return result
                        
                        # ===== BRIGHTNESS CONTROLS =====
                        elif windows_command.startswith('BRIGHTNESS_UP:'):
                            amount = int(windows_command.split(':')[1]) if ':' in windows_command else 10
                            result = self.executor.increase_brightness(amount)
                            logger.info(f"✅ Brightness increased: {result}")
                            return result
                        
                        elif windows_command.startswith('BRIGHTNESS_DOWN:'):
                            amount = int(windows_command.split(':')[1]) if ':' in windows_command else 10
                            result = self.executor.decrease_brightness(amount)
                            logger.info(f"✅ Brightness decreased: {result}")
                            return result
                        
                        elif windows_command.startswith('BRIGHTNESS_SET:'):
                            level = int(windows_command.split(':')[1])
                            result = self.executor.set_brightness(level)
                            logger.info(f"✅ Brightness set: {result}")
                            return result
                        
                        # ===== WIFI CONTROLS =====
                        elif windows_command == 'WIFI_STATUS':
                            result = self.executor.get_wifi_status()
                            logger.info(f"✅ WiFi status: {result}")
                            return result
                        
                        elif windows_command == 'WIFI_DISCONNECT':
                            result = self.executor.disconnect_wifi()
                            logger.info(f"✅ WiFi disconnected: {result}")
                            
                            # IMPROVEMENT: Automatically switch to OFFLINE mode when WiFi disconnects
                            self.llm_manager.set_mode(LLMMode.OFFLINE, clear_cache=True)
                            logger.info("🔒 Switched to OFFLINE mode (WiFi disconnected)")
                            
                            # Notify UI of mode change
                            self._emit_mode_change(LLMMode.OFFLINE)
                            
                            return result + " - Switched to offline mode."
                        
                        elif windows_command.startswith('WIFI_CONNECT:'):
                            network_name = windows_command.split(':', 1)[1].strip()
                            result = self.executor.connect_wifi(network_name)
                            logger.info(f"✅ WiFi connect: {result}")
                            
                            # Wait for internet to be fully available
                            # WiFi connects instantly but full internet/API access takes 4-10 seconds
                            import time
                            logger.debug("⏳ Waiting for internet and API access to become available...")
                            
                            # Try up to 5 times with 2-second intervals (10 seconds total)
                            max_attempts = 5
                            for attempt in range(1, max_attempts + 1):
                                time.sleep(2)  # Wait 2 seconds between attempts
                                
                                # Clear cache and check connectivity
                                self.llm_manager._connectivity_cache = False
                                self.llm_manager._last_connectivity_check = 0
                                
                                is_online = self.llm_manager.check_internet_connectivity()
                                if is_online:
                                    logger.info(f"✅ Internet connectivity confirmed after {attempt} attempt(s) ({attempt * 2}s)")
                                    
                                    # Give extra time for API endpoints to be reachable
                                    if attempt < 3:
                                        logger.debug("⏳ Internet confirmed but giving APIs more time to be reachable...")
                                        continue
                                    else:
                                        logger.info("✅ APIs should be ready now - online mode ready")
                                        # IMPROVEMENT: Switch to ONLINE mode when WiFi connects successfully
                                        self.llm_manager.set_mode(LLMMode.ONLINE, clear_cache=True)
                                        logger.info("🌐 Switched to ONLINE mode (internet available)")
                                        
                                        # Notify UI of mode change
                                        self._emit_mode_change(LLMMode.ONLINE)
                                        
                                        result += " - Now online!"
                                        break
                                else:
                                    logger.debug(f"⏳ Attempt {attempt}/{max_attempts}: No internet yet, retrying...")
                            
                            if not is_online:
                                logger.warning("⚠️ WiFi connected but no internet detected after 5 attempts (10s) - staying in offline mode")
                                result += " - WiFi connected but no internet access detected."
                            
                            return result
                        
                        elif windows_command == 'WIFI_LIST':
                            result = self.executor.list_wifi_networks()
                            logger.info(f"✅ WiFi networks: {result}")
                            return result
                        
                        elif windows_command == 'WIFI_PROFILES':
                            result = self.executor.get_saved_wifi_profiles()
                            logger.info(f"✅ WiFi profiles: {result}")
                            return result
                        
                        # ===== SMART TEXT SELECTION (Phase 3.5) =====
                        elif windows_command.startswith('SMART_SELECT:'):
                            query = windows_command.split(':', 1)[1].strip()
                            result = self.executor.find_and_select_text(query)
                            logger.info(f"✅ Smart select: {result}")
                            return result
                        
                        elif windows_command.startswith('SMART_COPY:'):
                            query = windows_command.split(':', 1)[1].strip()
                            result = self.executor.find_and_copy_text(query)
                            logger.info(f"✅ Smart copy: {result}")
                            return result
                        
                        elif windows_command.startswith('SMART_DELETE:'):
                            query = windows_command.split(':', 1)[1].strip()
                            result = self.executor.find_and_delete_text(query)
                            logger.info(f"✅ Smart delete: {result}")
                            return result
                        
                        elif windows_command == 'READ_SCREEN':
                            # Check privacy consent for screen analysis
                            if not self._check_screen_privacy_consent():
                                # Set pending action for user confirmation
                                self.context_manager.set_pending_action(
                                    'screen_analysis',
                                    {'command': 'READ_SCREEN', 'type': 'ocr'}
                                )
                                return "I can read the text on your screen using OCR. This will capture the active window only. Do you want me to proceed?"
                            
                            result = self.executor.read_screen_content()
                            # Store result for follow-up questions
                            self.context_manager.store_screen_analysis('ocr', result)
                            logger.info(f"✅ Read screen: {result[:100]}")
                            return result
                        
                        elif windows_command == 'DESCRIBE_SCREEN':
                            # Check privacy consent for screen analysis
                            if not self._check_screen_privacy_consent():
                                # Set pending action for user confirmation
                                self.context_manager.set_pending_action(
                                    'screen_analysis',
                                    {'command': 'DESCRIBE_SCREEN', 'type': 'vision'}
                                )
                                return "I can describe what's on your screen using AI vision. This will capture the active window only. Do you want me to proceed?"
                            
                            result = self.executor.describe_screen()
                            # Store result for follow-up questions
                            self.context_manager.store_screen_analysis('vision', result)
                            logger.info(f"✅ Describe screen: {result}")
                            return result
                        
                        # Phase 8: Combined Screen Analysis (OCR + Vision)
                        elif windows_command == 'SCREEN_ANALYZE':
                            # Check privacy consent for screen analysis
                            if not self._check_screen_privacy_consent():
                                # Set pending action for user confirmation
                                self.context_manager.set_pending_action(
                                    'screen_analysis',
                                    {'command': 'SCREEN_ANALYZE', 'type': 'combined'}
                                )
                                return "I can analyze your screen using both OCR and AI vision for comprehensive understanding. This will capture the active window only. Do you want me to proceed?"
                            
                            # Get both OCR text and AI vision description
                            logger.info("🔍 Performing comprehensive screen analysis (OCR + Vision)")
                            
                            ocr_text = self.executor.read_screen_content()
                            ai_description = self.executor.describe_screen()
                            
                            # Combine results
                            result = f"Visual Analysis: {ai_description}\n\nText Content: {ocr_text}"
                            
                            # Store result for follow-up questions
                            self.context_manager.store_screen_analysis('combined', result)
                            logger.info(f"✅ Screen analysis complete")
                            return result
                        
                        elif windows_command == 'SELECT_ALL':
                            result = self.executor.select_all_text()
                            logger.info(f"✅ Select all: {result}")
                            return result
                        
                        elif windows_command == 'COPY_SELECTED':
                            result = self.executor.copy_selected()
                            logger.info(f"✅ Copy selected: {result}")
                            return result
                        
                        elif windows_command == 'PASTE':
                            result = self.executor.paste_clipboard()
                            logger.info(f"✅ Paste: {result}")
                            return result
                        
                        elif windows_command == 'CUT_SELECTED':
                            result = self.executor.cut_selected()
                            logger.info(f"✅ Cut selected: {result}")
                            return result
                        
                        elif windows_command == 'DELETE_SELECTED':
                            result = self.executor.delete_selected()
                            logger.info(f"✅ Delete selected: {result}")
                            return result
                        
                        # Phase 4: Window Management
                        elif windows_command.startswith('WINDOW_MINIMIZE:'):
                            identifier = windows_command.replace('WINDOW_MINIMIZE:', '').strip()
                            result = self.executor.minimize_window(identifier)
                            logger.info(f"✅ Minimize window: {result}")
                            return result
                        
                        elif windows_command.startswith('WINDOW_MAXIMIZE:'):
                            identifier = windows_command.replace('WINDOW_MAXIMIZE:', '').strip()
                            result = self.executor.maximize_window(identifier)
                            logger.info(f"✅ Maximize window: {result}")
                            return result
                        
                        elif windows_command.startswith('WINDOW_RESTORE:'):
                            identifier = windows_command.replace('WINDOW_RESTORE:', '').strip()
                            result = self.executor.restore_window(identifier)
                            logger.info(f"✅ Restore window: {result}")
                            return result
                        
                        elif windows_command.startswith('WINDOW_HIDE:'):
                            identifier = windows_command.replace('WINDOW_HIDE:', '').strip()
                            result = self.executor.hide_window(identifier)
                            logger.info(f"✅ Hide window: {result}")
                            return result
                        
                        elif windows_command.startswith('WINDOW_SHOW:'):
                            identifier = windows_command.replace('WINDOW_SHOW:', '').strip()
                            result = self.executor.show_window(identifier)
                            logger.info(f"✅ Show window: {result}")
                            return result
                        
                        elif windows_command == 'WINDOW_ACTIVE':
                            result = self.executor.get_active_window()
                            logger.info(f"✅ Active window: {result}")
                            return f"The active window is: {result}"
                        
                        elif windows_command.startswith('WINDOW_STATE:'):
                            identifier = windows_command.replace('WINDOW_STATE:', '').strip()
                            result = self.executor.get_window_state(identifier)
                            logger.info(f"✅ Window state: {result}")
                            return result
                        
                        # Battery Status
                        elif windows_command == 'BATTERY_STATUS':
                            result = self.executor.get_battery_status()
                            logger.info(f"✅ Battery status: {result}")
                            return result
                        
                        elif windows_command == 'BATTERY_PERCENT':
                            result = self.executor.get_battery_percentage()
                            logger.info(f"✅ Battery percentage: {result}")
                            return result
                        
                        elif windows_command == 'BATTERY_CHARGING':
                            result = self.executor.is_battery_charging()
                            logger.info(f"✅ Battery charging: {result}")
                            return result
                        
                        elif windows_command == 'BATTERY_TIME':
                            result = self.executor.get_battery_time_remaining()
                            logger.info(f"✅ Battery time: {result}")
                            return result
                        
                        elif windows_command == 'NOTIFICATIONS_READ':
                            result = self.executor.read_notifications()
                            logger.info(f"✅ Notifications: {result}")
                            return result
                        
                        elif windows_command == 'NOTIFICATIONS_CHECK':
                            result = self.executor.check_notifications()
                            logger.info(f"✅ Notification check: {result}")
                            return result
                        
                        elif windows_command == 'SCREENSHOT':
                            result = self.executor.take_screenshot()
                            logger.info(f"✅ Screenshot: {result}")
                            return result
                        
                        elif windows_command == 'SCREENSHOT_CLIPBOARD':
                            result = self.executor.take_screenshot(copy_to_clipboard=True)
                            logger.info(f"✅ Screenshot to clipboard: {result}")
                            return result
                        
                        elif windows_command == 'SCREENSHOTS_FOLDER':
                            result = self.executor.open_screenshots_folder()
                            logger.info(f"✅ Screenshots folder: {result}")
                            return result
                        
                        elif windows_command == 'SCREENSHOTS_COUNT':
                            result = self.executor.get_screenshot_count()
                            logger.info(f"✅ Screenshot count: {result}")
                            return result
                        
                        # ===== GAME MANAGEMENT (Phase 12) =====
                        elif windows_command.startswith('LAUNCH_GAME:'):
                            game_name = windows_command.replace('LAUNCH_GAME:', '').strip()
                            result = self.executor.launch_game(game_name)
                            logger.info(f"✅ Game launch: {result}")
                            return result
                        
                        elif windows_command == 'LIST_GAMES':
                            # Check if this is a follow-up request for game names
                            last_action_result = self.context_manager.get_last_action()
                            
                            # Handle both tuple (legacy) and dict (new action stack) formats
                            if isinstance(last_action_result, dict):
                                last_action = last_action_result.get('action', '')
                                last_data = last_action_result.get('data', {})
                            else:
                                last_action, last_data = last_action_result
                            
                            is_follow_up = False
                            
                            # Detect follow-up patterns
                            if last_action == "list_games":
                                follow_up_patterns = [
                                    "what are those", "what are they", "which ones",
                                    "tell me their names", "list them", "what games",
                                    "tell me the names", "which games", "name them",
                                    "what are the games", "which are they"
                                ]
                                user_text_lower = user_text.lower()
                                if any(pattern in user_text_lower for pattern in follow_up_patterns):
                                    is_follow_up = True
                            
                            result = self.executor.list_games(is_follow_up=is_follow_up)
                            logger.info(f"✅ Games list (follow_up={is_follow_up}): {result}")
                            return result
                        
                        elif windows_command.startswith('LIST_GAMES:'):
                            platform = windows_command.replace('LIST_GAMES:', '').strip()
                            
                            # Check if this is a follow-up request for game names
                            last_action_result = self.context_manager.get_last_action()
                            
                            # Handle both tuple (legacy) and dict (new action stack) formats
                            if isinstance(last_action_result, dict):
                                last_action = last_action_result.get('action', '')
                                last_data = last_action_result.get('data', {})
                            else:
                                last_action, last_data = last_action_result
                            
                            is_follow_up = False
                            
                            # Detect follow-up patterns
                            if last_action == "list_games" and last_data.get('platform') == platform:
                                follow_up_patterns = [
                                    "what are those", "what are they", "which ones",
                                    "tell me their names", "list them", "what games",
                                    "tell me the names", "which games", "name them",
                                    "what are the games", "which are they"
                                ]
                                user_text_lower = user_text.lower()
                                if any(pattern in user_text_lower for pattern in follow_up_patterns):
                                    is_follow_up = True
                            
                            result = self.executor.list_games(platform, is_follow_up=is_follow_up)
                            logger.info(f"✅ {platform} games list (follow_up={is_follow_up}): {result}")
                            return result
                        
                        # ===== FOLDER MANAGEMENT (Phase 12) =====
                        elif windows_command.startswith('OPEN_FOLDER:'):
                            folder_name = windows_command.replace('OPEN_FOLDER:', '').strip()
                            result = self.executor.open_folder(folder_name)
                            logger.info(f"✅ Folder opened: {result}")
                            return result
                        
                        elif windows_command.startswith('FIND_FOLDER:'):
                            folder_name = windows_command.replace('FIND_FOLDER:', '').strip()
                            result = self.executor.find_folder(folder_name)
                            logger.info(f"✅ Folder found: {result}")
                            return result
                        
                        # ===== MUSIC CONTROL =====
                        elif windows_command == 'PLAY_MUSIC':
                            result = self.executor.music_manager.play_random()
                            logger.info(f"🎵 Play random music: {result}")
                            return result
                        
                        elif windows_command.startswith('PLAY_MUSIC:'):
                            song_name = windows_command.replace('PLAY_MUSIC:', '').strip()
                            result = self.executor.music_manager.play_song(song_name=song_name)
                            logger.info(f"🎵 Play song '{song_name}': {result}")
                            return result
                        
                        elif windows_command == 'PAUSE_MUSIC':
                            result = self.executor.music_manager.pause()
                            logger.info(f"⏸️ Pause music: {result}")
                            return result
                        
                        elif windows_command == 'RESUME_MUSIC':
                            result = self.executor.music_manager.resume()
                            logger.info(f"▶️ Resume music: {result}")
                            return result
                        
                        elif windows_command == 'STOP_MUSIC':
                            result = self.executor.music_manager.stop()
                            logger.info(f"⏹️ Stop music: {result}")
                            return result
                        
                        elif windows_command == 'NEXT_SONG':
                            result = self.executor.music_manager.next_song()
                            logger.info(f"⏭️ Next song: {result}")
                            return result
                        
                        elif windows_command == 'PREVIOUS_SONG':
                            result = self.executor.music_manager.previous_song()
                            logger.info(f"⏮️ Previous song: {result}")
                            return result
                        
                        elif windows_command == 'WHATS_PLAYING':
                            result = self.executor.music_manager.get_current_track()
                            logger.info(f"🎵 Current track: {result}")
                            return result
                        
                        elif windows_command == 'LIST_MUSIC':
                            songs = self.executor.music_manager.list_songs()
                            result = "\n".join(songs) if songs else "No music files found in your Music folder."
                            logger.info(f"🎵 Music list: {len(songs)} songs")
                            return result
                        
                        elif windows_command == 'MUSIC_STATS':
                            result = self.executor.music_manager.get_library_stats()
                            logger.info(f"📊 Music stats: {result}")
                            return result
                        
                        elif windows_command == 'SUGGEST_MUSIC' or windows_command.startswith('SUGGEST_MUSIC:'):
                            # Extract parameters
                            based_on_current = ':similar' in windows_command.lower()
                            result = self.executor.music_manager.suggest_music(count=5, based_on_current=based_on_current)
                            logger.info(f"💡 Music suggestions: {result[:100]}")
                            return result
                        
                        elif windows_command:
                            # Execute any Windows command dynamically (fallback)
                            result = self.executor.execute_command(windows_command)
                            logger.info(f"✅ Command executed: {result[:100] if result else 'Success'}")
                            
                            # Return user-friendly response if command succeeded
                            if result and 'error' not in result.lower() and 'failed' not in result.lower():
                                return user_response
                            elif not result or len(result.strip()) == 0:
                                # Empty result usually means success for system commands
                                return user_response
                            else:
                                return f"{user_response}, but there was an issue: {result[:200]}"
                        
                        return user_response
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ Failed to parse JSON command: {e}")
                    logger.warning(f"   Raw response: {response_text[:200]}")
                    # Don't speak raw JSON/markdown - give user-friendly error
                    if '```' in response_text or '{' in response_text[:50]:
                        logger.error(f"🔴 AI returned malformed JSON - not speaking raw output")
                        return "I tried to process that command, but got an unexpected response format. Please try again."
                    logger.debug("Treating as normal conversation")
            
            # SAFETY CHECK: Don't speak raw JSON or markdown blocks
            if response_text.strip().startswith('```') or (response_text.strip().startswith('{') and '"function_call"' in response_text):
                logger.error(f"🔴 Response contains unprocessed JSON/markdown - blocking TTS")
                logger.error(f"   This indicates JSON extraction failed")
                logger.error(f"   Raw response: {response_text[:200]}")
                return "I had trouble processing that command. Please try again."
            
            # Regular conversation response
            return response_text
            
        except Exception as e:
            logger.error(f"❌ AI processing error: {e}", exc_info=True)
            return "I'm having trouble processing that request right now."
    
    def _speak_response(self, text: str):
        """
        Convert response to speech and play it.
        Pauses listening during TTS to avoid feedback loop.
        BLOCKS until speech completes to prevent queue processing issues.
        
        Args:
            text: Text to speak
        """
        # Clean markdown formatting before speaking
        text = self._clean_markdown(text)
        
        logger.debug(f"🗣️ Speaking: {text[:100]}")
        # State will be set to SPEAKING by TTS callback (_on_tts_start)
        
        # Issue 4 Fix: Use slightly slower speed for clearer, calmer responses
        # Short responses (< 50 chars) get normal speed, longer ones get slower
        speech_speed = 0.95 if len(text) > 50 else 1.0
        
        try:
            # Pause listening to avoid picking up TTS output
            # Keep music at listening volume (15%) - TTS ducking will lower it to 3%
            logger.debug("Pausing listener for TTS...")
            self.listener.pause_listening(for_tts=False)
            
            # Speak the response (BLOCKING - waits for TTS to finish)
            # Ducking will lower music from 15% → 3% during speech for clarity
            logger.debug("Starting TTS (blocking mode with ducking)...")
            self.tts.speak(text, blocking=True, ducking=True, speed=speech_speed)
            logger.debug("TTS completed")
            
            # Resume listening after TTS completes
            logger.debug("Resuming listener...")
            self.listener.resume_listening()
        except Exception as e:
            logger.error(f"TTS error: {e}", exc_info=True)
            self.listener.resume_listening()  # Always resume even on error
        
        # State will be set back to IDLE by TTS callback (_on_tts_end)
        # No need to manually change state here
    
    def start_listening(self):
        """Begin listening for user input."""
        if self.state == NexaState.IDLE:
            self._change_state(NexaState.LISTENING)
            self.listener.set_passive_mode(False)  # Active mode - process all commands
            self.listener.start_listening()
    
    def stop_listening(self):
        """Stop listening for user input."""
        self.listener.stop_listening()
        self._change_state(NexaState.IDLE)
    
    def _change_state(self, new_state: NexaState):
        """
        Change Nexa's operational state and notify listeners.
        
        Args:
            new_state: New state to transition to
        """
        import time
        
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            
            # Enhanced state transition logging with context
            state_icons = {
                NexaState.IDLE: "💤",
                NexaState.LISTENING: "👂",
                NexaState.THINKING: "🤔",
                NexaState.SPEAKING: "💬"
            }
            old_icon = state_icons.get(old_state, "❓")
            new_icon = state_icons.get(new_state, "❓")
            
            # Track listening start time
            if new_state == NexaState.LISTENING:
                self._listening_start_time = time.time()
                logger.info(f"🔄 STATE: {old_icon} {old_state.value} → {new_icon} {new_state.value} (listening timer: {self._listening_timeout_duration:.0f}s)")
            elif new_state == NexaState.IDLE:
                # Show how long we were in previous state
                if old_state == NexaState.LISTENING and self._listening_start_time > 0:
                    duration = time.time() - self._listening_start_time
                    logger.info(f"🔄 STATE: {old_icon} {old_state.value} → {new_icon} {new_state.value} (was listening for {duration:.1f}s)")
                else:
                    logger.info(f"🔄 STATE: {old_icon} {old_state.value} → {new_icon} {new_state.value}")
            else:
                logger.info(f"🔄 STATE: {old_icon} {old_state.value} → {new_icon} {new_state.value}")
            
            # Notify callbacks
            for callback in self.state_callbacks:
                try:
                    callback(new_state)
                except Exception as e:
                    logger.error(f"Error in state callback: {e}")
    
    def _emit_message(self, sender: str, text: str):
        """
        Emit a message to UI callbacks.
        
        Args:
            sender: Message sender ('user' or 'nexa')
            text: Message text
        """
        message = {
            'sender': sender,
            'text': text,
            'timestamp': self.context_manager._get_timestamp()
        }
        
        for callback in self.message_callbacks:
            try:
                callback(message)
            except Exception as e:
                logger.error(f"Error in message callback: {e}")
    
    def register_state_callback(self, callback):
        """Register a callback for state changes."""
        self.state_callbacks.append(callback)
    
    def register_message_callback(self, callback):
        """Register a callback for new messages."""
        self.message_callbacks.append(callback)
    
    def register_audio_level_callback(self, callback):
        """Register a callback for audio level updates."""
        self.audio_level_callbacks.append(callback)
    
    def register_mode_callback(self, callback):
        """Register a callback for mode changes (online/offline)."""
        self.mode_callbacks.append(callback)
    
    def set_window(self, window):
        """
        Set window reference for UI control (e.g., theme switching).
        Also connects executor's signals to window slots for thread-safe GUI operations.
        
        Args:
            window: NexaModernWindow instance
        """
        self.window = window
        self.executor.window = window  # Pass to executor for function registry
        
        # Connect executor's close_content_window signal to window's slot
        self.executor.close_content_window_requested.connect(window._close_content_window)
        logger.info("✅ Executor signals connected to window slots")
        
        logger.info("✅ Window reference set for UI control")
    
    def set_gpu_monitor(self, gpu_monitor):
        """
        Set GPU monitor reference for GPU usage queries.
        
        Args:
            gpu_monitor: GPUMonitor instance
        """
        self.gpu_monitor = gpu_monitor
        self.executor.gpu_monitor = gpu_monitor  # Pass to executor for usage queries
        logger.info("✅ GPU monitor reference set")
    
    def _on_llm_mode_changed(self, new_mode):
        """
        Handle LLM mode changes from llm_manager.
        Announces verbally and forwards to UI callbacks.
        """
        from core.llm_manager import LLMMode
        
        mode_display = "online" if new_mode == LLMMode.ONLINE else "offline"
        logger.info(f"🔄 LLM mode changed to: {mode_display.upper()}")
        
        # Announce verbally
        if new_mode == LLMMode.ONLINE:
            message = "I'm now online. Full features are available."
        else:
            message = "I'm now offline. Basic features only."
        
        # Speak announcement with BLOCKING to prevent listener from picking it up
        # This prevents the echo issue where listener processes the announcement as a command
        try:
            self.tts.speak(message, blocking=True, ducking=True)
            logger.debug("🔇 Mode announcement completed (blocking TTS used to prevent echo)")
        except Exception as e:
            logger.error(f"Failed to announce mode change: {e}")
        
        # Forward to UI callbacks
        self._emit_mode_change(new_mode)
    
    def _on_tts_start(self):
        """Callback when TTS starts speaking - update state to RESPONDING."""
        logger.debug("🗣️ TTS started - setting state to SPEAKING")
        self._change_state(NexaState.SPEAKING)
    
    def _on_tts_end(self):
        """Callback when TTS finishes speaking - return to LISTENING for follow-ups."""
        logger.debug("✅ TTS finished - returning to LISTENING for follow-up commands")
        
        # Check if we were in proactive mode (set before TTS started)
        is_proactive = self.listener.proactive_listening if self.listener else False
        
        # Reset listener timeout and ensure active mode (no wake word needed)
        if self.listener:
            self.listener.record_valid_command()
            self.listener.set_passive_mode(False)  # Active mode - process all commands
        
        # Stay in LISTENING state for follow-up commands
        self._change_state(NexaState.LISTENING)
        
        # Resume/start listening - preserve proactive mode by passing None
        # The proactive flag was already set by _on_proactive_opportunity()
        if self.listener and not self.listener.is_listening:
            # Don't pass proactive arg - let it preserve existing flag
            self.listener.start_listening()
            if is_proactive:
                logger.info("💜 Proactive mode active - user can respond without wake word")
        elif self.listener:
            self.listener.resume_listening()
    
    def _emit_mode_change(self, new_mode):
        """Notify all registered callbacks of mode change."""
        for callback in self.mode_callbacks:
            try:
                callback(new_mode)
            except Exception as e:
                logger.error(f"Error in mode callback: {e}")
    
    def get_conversation_history(self) -> list:
        """Get recent conversation history."""
        return self.context_manager.get_recent_context(max_interactions=20)
    
    def _clean_markdown(self, text: str) -> str:
        """
        Remove markdown formatting from text before TTS.
        Removes: **, *, bullets, headers, etc.
        
        Delegates to TextProcessor for the actual logic.
        
        Args:
            text: Original text with markdown
            
        Returns:
            Clean text for TTS
        """
        return self.text_processor.clean_markdown(text)
    
    def _learn_from_action(self, func_name: str, params: Dict[str, Any]):
        """
        Learn user preferences from executed actions.
        Tracks patterns like preferred volume levels, apps, etc.
        
        Args:
            func_name: Function that was executed
            params: Parameters passed to the function
        """
        try:
            # Learn volume preferences
            if func_name == 'set_volume' and 'level' in params:
                level = params['level']
                self.context_manager.learn_preference('volume_levels', 'level', level)
            
            # Learn brightness preferences
            elif func_name == 'set_brightness' and 'level' in params:
                level = params['level']
                self.context_manager.learn_preference('brightness_levels', 'level', level)
            
            # Learn frequently opened apps
            elif func_name == 'open_application' and 'app_name' in params:
                app = params['app_name']
                self.context_manager.learn_preference('frequently_opened_apps', 'app_name', app)
            
            # Learn preferred game platform
            elif func_name == 'list_games' and 'platform' in params:
                platform = params.get('platform')
                if platform:  # Only if specific platform requested
                    self.context_manager.learn_preference('game_platforms', 'platform', platform)
            
            # Track common commands
            self.context_manager.learn_preference('common_commands', 'function', func_name)
            
        except Exception as e:
            logger.debug(f"⚠️ Learning error (non-critical): {e}")
    
    def _is_error_result(self, result: Any) -> bool:
        """
        Check if function execution result indicates an error/failure.
        
        Critical for preventing hallucinations where LLM claims success
        when the function actually failed.
        
        Delegates to FunctionValidator for the actual logic.
        
        Args:
            result: Function execution result (usually string)
            
        Returns:
            bool: True if result indicates error, False if success
        """
        return self.function_validator.is_error_result(result)
    
    def _find_similar_apps(self, query: str, max_results: int = 3) -> List[str]:
        """
        Find similar app names using fuzzy matching.
        
        Args:
            query: App name query to match
            max_results: Maximum number of suggestions
            
        Returns:
            List[str]: List of similar app names
        """
        try:
            from difflib import get_close_matches
            
            # Get list of installed apps from discovery
            all_apps = self.executor.app_discovery.get_all_apps()
            app_names = [app['name'] for app in all_apps if 'name' in app]
            
            # Fuzzy match with 60% similarity threshold
            matches = get_close_matches(query, app_names, n=max_results, cutoff=0.6)
            return matches
        except Exception as e:
            logger.debug(f"⚠️ Error finding similar apps: {e}")
            return []
    
    def _is_information_function(self, func_name: str) -> bool:
        """
        Dynamically determine if a function is an information query vs action.
        
        Information functions return data without changing system state.
        Actions modify system state (open, close, set, etc.).
        
        ALSO includes functions that return their own descriptive messages
        (like music functions) to avoid double TTS from LLM response + function result.
        
        Delegates to FunctionValidator for the actual logic.
        
        Args:
            func_name: Function name to check
            
        Returns:
            bool: True if information function, False if action
        """
        return self.function_validator.is_information_function(func_name)
    
    def validate_function_call(self, func_name: str, func_params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate a function call before execution (CR-12, CR-13, CR-14).
        Prevents hallucinated functions, invalid parameters, and unsafe operations.
        
        Delegates to FunctionValidator for the actual logic.
        
        Args:
            func_name: Function name to validate
            func_params: Parameters dict to validate
            
        Returns:
            tuple: (is_valid: bool, error_message: Optional[str])
                   If valid: (True, None)
                   If invalid: (False, "error description")
        """
        return self.function_validator.validate_function_call(
            func_name, 
            func_params, 
            is_content_mode=self._is_content_mode_active()
        )
    
    def _get_error_indicators(self) -> List[str]:
        """
        Get list of error indicator phrases dynamically.
        Can be extended to load from config file in the future.
        
        Delegates to FunctionValidator for the actual logic.
        
        Returns:
            List[str]: Error indicator phrases
        """
        return self.function_validator.get_error_indicators()
    
    def _build_llama_history(self, recent_history: List[Dict[str, Any]]) -> str:
        """
        Build a Llama-optimized conversation history.
        
        Delegates to ConversationHistoryBuilder.
        
        Args:
            recent_history: Recent conversation interactions
            
        Returns:
            str: Formatted history for Llama
        """
        return self.history_builder.build_llama_history(recent_history)
    
    def _prefetch_memory_context(self, user_text: str) -> str:
        """
        Pre-fetch relevant memory context for personal/relationship questions.
        
        This ensures the LLM has the information BEFORE it needs to decide
        whether to call what_do_you_know. Makes memory queries much more reliable.
        
        Args:
            user_text: User's input text
            
        Returns:
            str: Memory context to inject into prompt, or empty string
        """
        try:
            user_lower = user_text.lower()
            
            # Keywords that trigger memory pre-fetch
            memory_triggers = [
                # Relationship words
                'friend', 'best friend', 'bestfriend', 'brother', 'sister', 
                'mother', 'father', 'mom', 'dad', 'girlfriend', 'boyfriend',
                'wife', 'husband', 'cousin', 'uncle', 'aunt', 'boss', 'family',
                # Personal info
                'birthday', 'favorite', 'favourite', 'hobby', 'hobbies',
                'like', 'love', 'prefer', 'enjoy',
                # Questions about people/self
                'who is', 'who\'s', 'do you know', 'tell me about', 'what about',
                'remember', 'what do you know', 'know about',
                # Creator
                'created', 'creator', 'made you', 'who made',
            ]
            
            # DYNAMIC: Load personal names, locations, and education from user_prefs
            dynamic_triggers = self._get_dynamic_memory_triggers()
            memory_triggers.extend(dynamic_triggers)
            
            # Build exclusion list dynamically (user's own name should not trigger name detection)
            user_name_lower = self.config.user_name.lower() if hasattr(self, 'config') and self.config else 'ali'
            name_exclusions = {'the', 'what', 'who', 'how', 'why', 'when', 'where', 
                             'can', 'could', 'would', 'should', 'did', 'does', 
                             'have', 'has', 'are', 'is', 'am', 'was', 'were', 
                             'will', 'nexa', user_name_lower,
                             # Common command/action words (not person names)
                             'get', 'set', 'open', 'close', 'start', 'stop', 'run',
                             'show', 'tell', 'take', 'play', 'pause', 'find', 'check',
                             'make', 'turn', 'switch', 'change', 'move', 'lock', 'unlock',
                             'search', 'list', 'help', 'give', 'let', 'put', 'send',
                             'read', 'write', 'save', 'delete', 'create', 'add', 'remove',
                             'try', 'use', 'see', 'look', 'go', 'come', 'keep', 'say',
                             'my', 'your', 'his', 'her', 'our', 'its', 'their',
                             'this', 'that', 'these', 'those', 'it', 'all', 'just',
                             'also', 'too', 'not', 'don', 'but', 'and', 'for',
                             'with', 'from', 'about', 'some', 'any', 'new', 'old',
                             'now', 'here', 'there', 'please', 'thanks', 'yes', 'no',
                             'hey', 'hi', 'hello', 'okay', 'sure', 'well', 'much',
                             'very', 'really', 'more', 'most', 'only', 'other',
                             'right', 'want', 'need', 'know', 'think', 'like',
                             'full', 'info', 'system', 'profile', 'screen', 'volume',
                             'brightness', 'battery', 'time', 'date', 'app', 'window',
                             'file', 'folder', 'name', 'size', 'type', 'mode',
                             'what\'s', 'it\'s', 'don\'t', 'i\'m', 'you\'re', 'can\'t',
                             'won\'t', 'didn\'t', 'doesn\'t', 'isn\'t', 'aren\'t'}
            
            # Check if any trigger is present
            triggered = False
            trigger_topics = []
            
            for trigger in memory_triggers:
                if trigger in user_lower:
                    triggered = True
                    trigger_topics.append(trigger)
            
            # Also check for capitalized names (potential person names)
            words = user_text.split()
            for word in words:
                if word and word[0].isupper() and len(word) > 2 and word.lower() not in name_exclusions:
                    triggered = True
                    trigger_topics.append(word)
            
            if not triggered:
                return ""
            
            # Query memory for relevant facts
            if not hasattr(self, 'context_manager') or not self.context_manager:
                return ""
            
            if not hasattr(self.context_manager, 'smart_memory') or not self.context_manager.smart_memory:
                return ""
            
            # Build search query from trigger topics
            search_query = user_text  # Use full text for semantic search
            
            # Get relevant facts from memory
            result = self.context_manager.recall_knowledge_answer(search_query, limit=5)
            
            if not result.get('found'):
                # Also try individual trigger topics (only meaningful ones)
                for topic in trigger_topics[:3]:  # Limit to 3 topics
                    # Skip short/generic topics that won't yield useful results
                    if len(topic) < 4:
                        continue
                    result = self.context_manager.recall_knowledge_answer(topic, limit=3)
                    if result.get('found'):
                        break
            
            if not result.get('found'):
                return ""
            
            # Build memory context text
            facts = result.get('facts', [])
            if not facts:
                return ""
            
            memory_text = "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            memory_text += "🧠 MEMORY CONTEXT (USE THIS INFO TO ANSWER!):\n"
            memory_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            memory_text += "I remember the following about the user:\n"
            for fact in facts[:5]:  # Limit to 5 facts
                memory_text += f"• {fact}\n"
            memory_text += "\n⚠️ USE THE ABOVE FACTS to answer the user's question naturally!\n"
            memory_text += "DO NOT say 'I don't know' - the information is RIGHT HERE!\n"
            memory_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            
            logger.info(f"🧠 Memory pre-fetch found {len(facts)} relevant facts for: '{user_text[:50]}...'")
            return memory_text
            
        except Exception as e:
            logger.warning(f"Memory pre-fetch failed (non-critical): {e}")
            return ""
    
    def _get_dynamic_memory_triggers(self) -> list:
        """
        Dynamically build memory trigger keywords from user_prefs.json.
        
        This replaces hardcoded names like 'saliha', 'waseem', 'nusrat' with
        whatever is in the user's preferences — works for ANY user, not just Ali.
        
        Returns:
            list: Dynamic trigger keywords from personal data
        """
        triggers = []
        try:
            if not hasattr(self, 'config') or not self.config:
                return triggers
            
            prefs_file = self.config.data_dir / 'user_prefs.json'
            if not prefs_file.exists():
                return triggers
            
            import json
            with open(prefs_file, 'r', encoding='utf-8-sig') as f:
                prefs = json.load(f)
            
            personal = prefs.get('personal', {})
            
            # Extract relationship names (first names, nicknames)
            relationships = personal.get('relationships', {})
            for key, info in relationships.items():
                # Add the key itself (e.g., 'saliha', 'father')
                triggers.append(key.lower())
                # Add the full name
                if 'name' in info:
                    triggers.append(info['name'].lower())
                    # Add first name only
                    first_name = info['name'].split()[0].lower()
                    if first_name != key.lower():
                        triggers.append(first_name)
                # Add nickname if different
                if 'nickname' in info:
                    triggers.append(info['nickname'].lower())
                # Add relationship type 
                if 'relationship' in info:
                    triggers.append(info['relationship'].lower())
            
            # Extract user_info keywords (location, university, etc.)
            user_info = personal.get('user_info', {})
            for field in ['university', 'location']:
                value = user_info.get(field, '')
                if value:
                    # Add full value and individual significant words
                    triggers.append(value.lower())
                    for word in value.split():
                        clean_word = word.strip('(),').lower()
                        if len(clean_word) > 2 and clean_word not in ('of', 'and', 'the', 'for'):
                            triggers.append(clean_word)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_triggers = []
            for t in triggers:
                if t not in seen:
                    seen.add(t)
                    unique_triggers.append(t)
            
            return unique_triggers
            
        except Exception as e:
            logger.debug(f"Could not load dynamic memory triggers: {e}")
            return triggers
    
    def _identify_command_type(self, user_msg: str) -> str:
        """
        Identify the type of command from user message.
        
        Delegates to ConversationHistoryBuilder.
        
        Args:
            user_msg: User's message
            
        Returns:
            str: Command type (query, action, conversation)
        """
        return self.history_builder.identify_command_type(user_msg)
    
    def _extract_entities_from_message(self, user_msg: str, nexa_msg: str) -> List[str]:
        """
        Extract key entities (app names, numbers, items) from messages.
        
        Delegates to ConversationHistoryBuilder.
        
        Args:
            user_msg: User's message
            nexa_msg: Nexa's response
            
        Returns:
            List[str]: Extracted entities
        """
        return self.history_builder.extract_entities_from_message(user_msg, nexa_msg)
    
    def _detect_mode_switch_command(self, user_input: str) -> str:
        """
        Detect explicit mode switching commands (go online/offline, switch mode).
        
        Delegates to CommandDetector.
        
        Args:
            user_input: User's message
            
        Returns:
            str: Response message if mode switched, None otherwise
        """
        return self.command_detector.detect_mode_switch_command(
            user_input, 
            self.llm_manager.current_mode, 
            self.llm_manager
        )
    
    def _detect_vision_request(self, user_input: str) -> bool:
        """
        Detect if user is requesting AI vision analysis.
        
        Delegates to CommandDetector.
        
        Args:
            user_input: User's message
            
        Returns:
            bool: True ONLY for actual AI vision requests, not simple screenshot commands
        """
        return self.command_detector.detect_vision_request(
            user_input, 
            self.llm_manager.current_mode
        )
    
    def _extract_action_verb(self, user_text: str) -> str:
        """
        Extract the action verb from user input for semantic validation.
        
        Delegates to TextProcessor for the actual logic.
        
        Args:
            user_text: Original user input
            
        Returns:
            str: Action verb (open, close, set, etc.) or empty string
        """
        return self.text_processor.extract_action_verb(user_text)
    
    def _normalize_window_variations(self, user_text: str) -> str:
        """
        Normalize natural language variations for window management commands.
        Helps AI understand phrases like "make it bigger" = "maximize".
        
        Delegates to TextProcessor for the actual logic.
        
        Args:
            user_text: Original user input
            
        Returns:
            str: Normalized text with standardized window commands
        """
        return self.text_processor.normalize_window_variations(user_text)
    
    def _resolve_standalone_ordinal(self, user_text: str) -> str:
        """
        Resolve standalone ordinal commands by auto-executing implicit list commands.
        
        Delegates to ReferenceResolver.
        
        Args:
            user_text: Original user input with ordinal reference
            
        Returns:
            str: Text with ordinal resolved to actual item (after auto-listing)
        """
        return self.reference_resolver.resolve_standalone_ordinal(user_text)
    
    def _resolve_pronouns(self, user_text: str) -> str:
        """
        Resolve pronouns (it, that, this, them) to actual targets from context.
        This runs BEFORE AI processing to make commands explicit.
        
        Delegates to ReferenceResolver.
        
        Args:
            user_text: Original user input with pronouns
            
        Returns:
            str: Text with pronouns resolved to actual targets
        """
        return self.reference_resolver.resolve_pronouns(user_text)
    
    def _detect_implicit_references(self, user_text: str) -> Dict[str, str]:
        """
        Detect implicit references in user text (e.g., "the folder", "the network").
        
        Delegates to TextProcessor for the actual logic.
        
        Args:
            user_text: User input text
            
        Returns:
            Dict mapping reference type to phrase found
        """
        return self.text_processor.detect_implicit_references(user_text)
    
    def _resolve_implicit_references(self, user_text: str, references: Dict[str, str]) -> str:
        """
        Resolve implicit references to actual entities from context.
        
        Delegates to ReferenceResolver.
        
        Args:
            user_text: Original user input
            references: Dict of detected reference types
            
        Returns:
            str: Text with implicit references resolved
        """
        return self.reference_resolver._resolve_implicit_references(user_text, references)
    
    # ============================================================================
    # NEW: Clarification Question System
    # ============================================================================
    
    def _requires_clarification(self, user_text: str, func_name: str, func_params: Dict[str, Any]) -> Optional[str]:
        """
        Detect if command needs clarification due to missing parameters or ambiguity.
        
        Delegates to ClarificationHandler.
        
        Args:
            user_text: Original user input
            func_name: Detected function name
            func_params: Function parameters extracted by AI
            
        Returns:
            Clarification question string or None if no clarification needed
        """
        # Store current command so clarification handler can save it with the question
        self.clarification_handler.set_current_command(user_text)
        return self.clarification_handler.requires_clarification(user_text, func_name, func_params)
    
    def _ask_clarification(self, question: str) -> str:
        """
        Store clarification question as pending and return it to user.
        This puts Nexa in a "waiting for answer" state.
        
        Delegates to ClarificationHandler.
        
        Args:
            question: Clarification question to ask user
            
        Returns:
            The question string
        """
        return self.clarification_handler.ask_clarification(question)
    
    def _handle_pending_intent(self, user_text: str) -> Optional[str]:
        """
        Handle user response to a pending intent (e.g., song name after "play a song").
        
        Checks if there's a pending intent and processes the user's response.
        For play_music: executes play_music with the provided song name.
        
        Args:
            user_text: User's response
            
        Returns:
            Result string if handled, None if not a pending intent response
        """
        try:
            # Get pending intent from IntentState (preferred) or legacy pending_action
            intent_type = None
            
            # Check IntentState first
            if hasattr(self.context_manager, 'intent_state') and self.context_manager.intent_state:
                pending_intent = self.context_manager.intent_state.get_pending_intent()
                if pending_intent:
                    intent_type = pending_intent.intent
                    logger.info(f"🎯 Found IntentState pending: {intent_type}")
            
            # Fallback to legacy pending_action (without clearing it yet)
            if not intent_type and self.context_manager.has_pending_action():
                pending = self.context_manager.pending_action  # Access directly, don't clear yet
                intent_type = pending.get('type', '')
                logger.info(f"🎯 Found legacy pending action: {intent_type}")
            
            if not intent_type:
                return None
            
            user_lower = user_text.lower().strip()
            
            logger.info(f"🎯 Processing pending intent: {intent_type}, user said: '{user_text}'")
            
            # Helper to clear pending state
            def clear_pending():
                self.context_manager.clear_follow_up()  # Clears IntentState + legacy
            
            # Check for cancellation
            cancel_words = ['cancel', 'nevermind', 'never mind', 'forget it', 'stop', 'no']
            if any(word in user_lower for word in cancel_words):
                clear_pending()
                logger.info("❌ User cancelled pending intent")
                return "Okay, cancelled."
            
            # Handle play_music pending intent
            if intent_type == 'play_music':
                # Check for random/shuffle keywords
                if user_lower in ['random', 'shuffle', 'anything', 'surprise me', 'whatever']:
                    clear_pending()
                    result = self.executor.music_manager.play_random()
                    logger.info(f"🎵 Playing random song: {result}")
                    return result
                
                # Check for "list songs" request
                if 'list' in user_lower and ('song' in user_lower or 'music' in user_lower):
                    clear_pending()
                    result = self.executor.list_music(limit=10)
                    logger.info(f"🎵 Listing songs: {result}")
                    return result
                
                # Treat the input as a song name
                clear_pending()
                result = self.executor.music_manager.play_song(song_name=user_text)
                logger.info(f"🎵 Playing song '{user_text}': {result}")
                return result
            
            # Handle proactive_suggestion - user is responding to a proactive offer
            # Pass the CONTEXT to LLM so it understands what "do it" / "yes" means
            if intent_type == 'proactive_suggestion':
                # Reset proactive listening flag since user responded
                if self.listener:
                    self.listener.proactive_listening = False
                
                # Get the pending suggestion from proactive engine
                pending_suggestion = None
                if self.proactive_engine:
                    pending_suggestion = self.proactive_engine.get_pending_suggestion()
                
                # Get the original suggestion message from IntentState
                original_suggestion = ""
                if pending_intent:
                    original_suggestion = pending_intent.original_command or pending_intent.clarification_question
                
                if not original_suggestion and pending_suggestion:
                    original_suggestion = pending_suggestion.message
                
                clear_pending()
                if pending_suggestion:
                    self.proactive_engine.clear_pending()
                
                if not original_suggestion:
                    logger.warning("💜 Proactive response but no context found - passing to LLM")
                    return None
                
                # Build a contextualized prompt for LLM
                # The LLM will understand "please do it" in context of what was suggested
                contextualized_input = f'[NEXA just said: "{original_suggestion}"] User replied: "{user_text}"'
                
                logger.info(f"💜 Proactive follow-up: {contextualized_input}")
                
                # Return None but inject the context into the user text
                # This will be processed by normal LLM flow with full context
                return ("__PROACTIVE_CONTEXT__", contextualized_input)
            
            # Unknown intent type - clear and let normal processing handle it
            logger.warning(f"⚠️ Unknown pending intent type: {intent_type}")
            return None
            
        except Exception as e:
            logger.error(f"Error handling pending intent: {e}")
            self.context_manager.clear_follow_up()
            return None
    
    def _check_clarification_response(self, user_text: str) -> Optional[str]:
        """
        Check if user is responding to a clarification question.
        If yes, reformulate the command with the provided information.
        
        Delegates to ClarificationHandler.
        
        Args:
            user_text: User's response
            
        Returns:
            Reformulated command or None if not a clarification response
        """
        return self.clarification_handler.check_clarification_response(user_text)
    
    # ============================================================================
    # NEW: Optimized Follow-up Question System (Use Cached Data)
    # ============================================================================
    
    def _is_counting_question(self, user_text: str) -> bool:
        """
        Detect if user is asking for a count ("how many?", "what's the count?").
        
        Delegates to TextProcessor for the actual logic.
        
        Args:
            user_text: User input
            
        Returns:
            True if counting question detected
        """
        return self.text_processor.is_counting_question(user_text)
    
    def _is_listing_question(self, user_text: str) -> bool:
        """
        Detect if user wants details/names ("what are they?", "list them").
        
        Delegates to TextProcessor for the actual logic.
        
        Args:
            user_text: User input
            
        Returns:
            True if listing question detected
        """
        return self.text_processor.is_listing_question(user_text)
    
    def _answer_from_cache(self, user_text: str, last_action: str, last_result: Any) -> Optional[str]:
        """
        Answer follow-up questions using cached data instead of re-executing.
        Significantly faster and reduces redundant operations.
        
        Delegates to ResponseCache for the actual logic.
        
        Args:
            user_text: User's follow-up question
            last_action: Last executed action
            last_result: Result from last action (string or data)
            
        Returns:
            Answer from cache or None if can't answer from cache
        """
        return self.response_cache.answer_from_cache(
            user_text, last_action, last_result, self.context_manager
        )
    
    # ============================================================================
    
    def _get_function_category(self, func_name: str) -> str:
        """
        Categorize function by type for follow-up correction.
        
        Delegates to FunctionValidator for the actual logic.
        
        Args:
            func_name: Name of the function
            
        Returns:
            Category string (info_query, app_control, system_setting, etc.)
        """
        return self.function_validator.get_function_category(func_name)
    
    # ============================================================================
    # PHASE 29: PROACTIVE ENGAGEMENT METHODS
    # ============================================================================
    
    def _on_proactive_opportunity(self, idle_duration: float, idle_state) -> bool:
        """
        Callback when a proactive engagement opportunity is detected.
        
        Args:
            idle_duration: How long user has been idle (seconds)
            idle_state: Current IdleState enum
            
        Returns:
            True if suggestion was made, False otherwise
        """
        logger.info(f"💜 Proactive opportunity callback: idle={idle_duration:.1f}s, state={idle_state}")
        
        if not self.proactive_engine or not self.enable_proactive:
            logger.warning("❌ Proactive engine or flag disabled")
            return False
        
        try:
            # Don't interrupt if we're not in IDLE state
            if self.state != NexaState.IDLE:
                logger.debug("Not in IDLE state, skipping proactive")
                return False
            
            # Build context
            session_duration = self.idle_monitor.get_session_duration() if self.idle_monitor else 0
            interaction_count = self.idle_monitor.stats.total_interactions if self.idle_monitor else 0
            
            logger.info(f"💜 Building proactive context: session={session_duration:.0f}s, interactions={interaction_count}")
            
            context = self.proactive_engine.build_context(
                idle_duration=idle_duration,
                session_duration=session_duration,
                interaction_count=interaction_count
            )
            
            logger.info(f"💜 Context built: time_of_day={context.time_of_day}, hour={context.current_hour}")
            
            # Decide what to suggest
            suggestion = self.proactive_engine.decide_suggestion(context)
            
            if suggestion:
                # Speak the proactive suggestion
                logger.info("🎯 Making proactive suggestion: %s", suggestion.message)
                
                # Enable proactive listening mode - bypass wake word for user's response
                if self.listener:
                    self.listener.set_proactive_listening(True)
                
                # Speak the suggestion (this will transition to SPEAKING, then LISTENING)
                self._speak_response(suggestion.message)
                
                # Mark that this came from proactive (for function calls)
                if hasattr(self.context_manager, 'intent_state') and self.context_manager.intent_state:
                    # Set a pending intent for the proactive suggestion
                    self.context_manager.intent_state.set_pending_intent(
                        intent="proactive_suggestion",
                        data_needed="user_response",
                        original_command=suggestion.message,
                        clarification_question=suggestion.message
                    )
                
                return True
            
            logger.info("💜 No proactive suggestion generated (no matching criteria)")
            return False
            
        except Exception as e:
            logger.error(f"Error in proactive opportunity: {e}")
            return False
    
    def _record_user_interaction(self):
        """Record that a user interaction occurred (for idle tracking)."""
        if self.idle_monitor and self.enable_proactive:
            self.idle_monitor.record_interaction()
    
    def _record_activity_pattern(self, activity: str, category: str = "command"):
        """
        Record an activity for pattern learning.
        
        Args:
            activity: The activity performed (e.g., "open_application")
            category: Category of activity
        """
        if self.pattern_learner and self.enable_proactive:
            try:
                self.pattern_learner.record_activity(activity, category)
            except Exception as e:
                logger.debug(f"Pattern recording failed: {e}")
    
    def _check_listening_timeout(self):
        """
        Check if listening should timeout and return to IDLE.
        Called by QTimer every 5 seconds.
        """
        import time
        
        # Only check when in LISTENING state
        if self.state != NexaState.LISTENING:
            return
        
        # Calculate time remaining
        if self.listener and self.listener.last_valid_command_time:
            elapsed = time.time() - self.listener.last_valid_command_time
            
            # Different timeout for proactive mode
            if self.listener.proactive_listening:
                proactive_timeout = 30.0
                remaining = proactive_timeout - elapsed
                if remaining > 0:
                    logger.info(f"💜 PROACTIVE LISTENING: {remaining:.0f}s remaining for response")
            else:
                remaining = self._listening_timeout_duration - elapsed
                if remaining > 0:
                    logger.info(f"⏱️ LISTENING: {remaining:.0f}s remaining until IDLE")
            
        # Check if listener has timed out
        if self.listener and self.listener.check_listening_timeout():
            logger.info("⏰ Listening timed out - transitioning to IDLE state")
            
            # In wake word mode, keep listener running in passive mode
            # so it can still detect the wake word while IDLE
            if self.listener.wake_word_enabled:
                logger.info("🎤 Wake word mode: Listener stays active for wake word detection")
                # Set passive mode - only wake word will activate
                self.listener.set_passive_mode(True)
                self.listener.wake_word_active = False
            else:
                # Without wake word, fully stop listening
                self.listener.stop_listening()
            
            self._change_state(NexaState.IDLE)
            
            # NOTE: Do NOT call record_interaction() here!
            # Timeout means the user STOPPED interacting — recording an interaction
            # would reset idle time to zero, defeating the proactive engine.
            # The idle_monitor already tracks from the last real interaction.
    
    def _check_proactive_opportunity(self):
        """
        Periodically check if we should make a proactive suggestion.
        Called by QTimer every 60 seconds.
        """
        import time
        
        # Reset proactive timer tracking
        self._proactive_timer_start = time.time()
        
        # Only check when in IDLE state
        if self.state != NexaState.IDLE:
            logger.info(f"💜 Proactive check: SKIPPED (state={self.state.value}, need IDLE)")
            return
        
        if not self.enable_proactive or not self.idle_monitor:
            logger.debug("⏸️ Proactive skipped: disabled or no idle_monitor")
            return
        
        # Update idle state and get timing info
        self.idle_monitor.update_state()
        idle_duration = self.idle_monitor.get_idle_duration()
        idle_state = self.idle_monitor.get_idle_state()
        
        logger.info(f"💜 Proactive check: IDLE for {idle_duration:.0f}s ({idle_state.value}), next check in {self._proactive_interval:.0f}s")
        
        # Check if we can trigger proactive
        if self.idle_monitor.can_trigger_proactive():
            logger.info("💜 ✨ Triggering proactive suggestion!")
            self.idle_monitor.trigger_proactive_opportunity()
        else:
            logger.debug("⏸️ Proactive not triggered (conditions not met)")

