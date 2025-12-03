"""
Audio Listener - Speech Input Capture and Transcription
Handles microphone input and faster-whisper integration for GPU-accelerated STT.
"""

import logging
import threading
import wave
import tempfile
import os
import sys
from pathlib import Path
from typing import Optional, Callable

# Add cuDNN to PATH for ctranslate2 (before importing faster_whisper)
def _add_cudnn_to_path():
    """Add NVIDIA cuDNN and cuBLAS DLL directories to system PATH."""
    try:
        # Get the site-packages directory
        site_packages = Path(__file__).parent.parent / '.venv' / 'Lib' / 'site-packages'
        
        # Add cuDNN bin directory
        cudnn_bin = site_packages / 'nvidia' / 'cudnn' / 'bin'
        if cudnn_bin.exists():
            cudnn_path = str(cudnn_bin.absolute())
            if cudnn_path not in os.environ.get('PATH', ''):
                os.environ['PATH'] = cudnn_path + os.pathsep + os.environ.get('PATH', '')
                print(f"[OK] Added cuDNN to PATH: {cudnn_path}")
        else:
            print(f"[WARN] cuDNN bin directory not found: {cudnn_bin}")
        
        # Add cuBLAS bin directory
        cublas_bin = site_packages / 'nvidia' / 'cublas' / 'bin'
        if cublas_bin.exists():
            cublas_path = str(cublas_bin.absolute())
            if cublas_path not in os.environ.get('PATH', ''):
                os.environ['PATH'] = cublas_path + os.pathsep + os.environ.get('PATH', '')
                print(f"[OK] Added cuBLAS to PATH: {cublas_path}")
        else:
            print(f"[WARN] cuBLAS bin directory not found: {cublas_bin}")
            
    except Exception as e:
        print(f"[WARN] Failed to add CUDA libraries to PATH: {e}")

_add_cudnn_to_path()

try:
    import pyaudio
except ImportError:
    pyaudio = None

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

# Import DeepFilterNet2 for noise cancellation
try:
    from df.enhance import enhance, init_df
    from df.io import resample
    import torch
    DEEPFILTERNET_AVAILABLE = True
except ImportError:
    DEEPFILTERNET_AVAILABLE = False

# Import Silero VAD for voice activity detection
try:
    import torch
    import torchaudio
    SILERO_VAD_AVAILABLE = True
except ImportError:
    SILERO_VAD_AVAILABLE = False

# Import noisereduce for lightweight noise cancellation
try:
    import noisereduce as nr
    NOISEREDUCE_AVAILABLE = True
except ImportError:
    NOISEREDUCE_AVAILABLE = False

# Import SpeakerVerification for voice authentication (optional)
try:
    from .speaker_verification import SpeakerVerification
    SPEAKER_VERIFICATION_AVAILABLE = True
except ImportError:
    SPEAKER_VERIFICATION_AVAILABLE = False
    SpeakerVerification = None
    
logger = logging.getLogger(__name__)


class AudioListener:
    """
    Manages audio capture from microphone and transcription via faster-whisper.
    Runs in a separate thread to avoid blocking the main application.
    Uses GPU acceleration for fast transcription.
    Supports wake word detection ("Nexa") to activate listening.
    """
    
    def __init__(self, config):
        """
        Initialize audio listener with configuration.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.is_listening = False
        self.is_speaking = False  # Flag to pause recording during TTS
        self.is_paused = False  # Flag for user-requested pause (stop listening command)
        self.transcription_callback: Optional[Callable] = None
        self.audio_level_callback: Optional[Callable] = None  # NEW: Callback for audio levels
        self.state_callback: Optional[Callable] = None  # NEW: Callback for state changes (e.g., RECOGNIZING)
        self.speaker_rejection_callback: Optional[Callable] = None  # NEW: Callback for speaker rejection
        
        # Wake word detection
        self.wake_word_enabled = True  # Enable wake word by default
        self.wake_word = "nexa"  # Primary wake word
        self.wake_word_active = False  # True when wake word detected, waiting for command
        self.wake_word_timeout = 5.0  # Seconds to wait for command after wake word
        self.wake_word_detected_time = 0  # Time when wake word was last detected
        
        # Music manager reference (for ducking during speech)
        self.music_manager = None  # Will be set by brain.py after initialization
        
        # Audio settings
        self.sample_rate = config.sample_rate
        self.chunk_size = config.chunk_size
        self.channels = config.channels
        self.format = pyaudio.paInt16 if pyaudio else None
        
        # PyAudio instance
        self.audio: Optional[pyaudio.PyAudio] = None
        self.stream: Optional[pyaudio.Stream] = None
        
        # Recording thread
        self.recording_thread: Optional[threading.Thread] = None
        
        # Faster-Whisper model (loaded once, kept in memory)
        self.whisper_model: Optional[WhisperModel] = None
        self._load_whisper_model()
        
        # DeepFilterNet2 for noise cancellation
        self.df_model = None
        self.df_state = None
        self._load_deepfilternet()
        
        # Silero VAD for voice activity detection
        self.vad_model = None
        self.vad_utils = None
        self._load_silero_vad()
        
        # Speaker Verification (optional, for voice authentication)
        self.speaker_verifier: Optional[SpeakerVerification] = None
        self._load_speaker_verification()
        
        # Speaker Enrollment (will be set by brain.py after initialization)
        self.speaker_enrollment = None
        
        # Initialize PyAudio
        if pyaudio:
            try:
                self.audio = pyaudio.PyAudio()
                logger.info("PyAudio initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize PyAudio: {e}")
                self.audio = None
        else:
            logger.warning("PyAudio not available - audio capture disabled")
    
    def _reinitialize_pyaudio(self):
        """Reinitialize PyAudio (useful if audio subsystem gets corrupted)."""
        if not pyaudio:
            logger.warning("PyAudio not available")
            return False
        
        try:
            # Terminate existing instance
            if self.audio:
                try:
                    self.audio.terminate()
                except:
                    pass
            
            # Create new instance
            self.audio = pyaudio.PyAudio()
            logger.info("✅ PyAudio reinitialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to reinitialize PyAudio: {e}")
            self.audio = None
            return False
    
    def _load_whisper_model(self):
        """Load faster-whisper model (GPU-accelerated)."""
        if not WhisperModel:
            logger.error("faster-whisper not installed!")
            return
        
        try:
            logger.info(f"🔄 Loading Whisper model: {self.config.whisper_model_name}")
            logger.info(f"   Device: {self.config.whisper_device}")
            logger.info(f"   Compute type: {self.config.whisper_compute_type}")
            logger.info(f"   Cache dir: {self.config.whisper_model_cache_dir}")
            
            self.whisper_model = WhisperModel(
                self.config.whisper_model_name,
                device=self.config.whisper_device,
                compute_type=self.config.whisper_compute_type,
                download_root=str(self.config.whisper_model_cache_dir)
            )
            logger.info("✅ Whisper model loaded successfully (GPU-accelerated)!")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            logger.info("Falling back to CPU...")
            try:
                self.whisper_model = WhisperModel(
                    self.config.whisper_model_name,
                    device="cpu",
                    compute_type="int8",
                    download_root=str(self.config.whisper_model_cache_dir)
                )
                logger.info("✅ Whisper model loaded on CPU")
            except Exception as e2:
                logger.error(f"Failed to load Whisper model on CPU: {e2}")
                self.whisper_model = None
    
    def _load_deepfilternet(self):
        """Load DeepFilterNet2 model for noise cancellation."""
        if not DEEPFILTERNET_AVAILABLE:
            logger.warning("⚠️ DeepFilterNet2 not available - noise cancellation disabled")
            logger.warning("   Install with: pip install deepfilternet torch")
            return
        
        try:
            logger.info("🔄 Loading DeepFilterNet2 (noise cancellation)...")
            
            # If frozen (bundled), set DF_MODELS environment variable to bundled models
            if getattr(sys, 'frozen', False):
                bundled_models_dir = Path(sys._MEIPASS) / 'df_models'
                if bundled_models_dir.exists():
                    os.environ['DF_MODELS'] = str(bundled_models_dir)
                    logger.info(f"   Using bundled DeepFilterNet models: {bundled_models_dir}")
            
            # Initialize DeepFilterNet2 model
            self.df_model, self.df_state, _ = init_df()
            logger.info("✅ DeepFilterNet2 loaded successfully!")
        except Exception as e:
            logger.error(f"Failed to load DeepFilterNet2: {e}")
            logger.warning("   Continuing without noise cancellation")
            self.df_model = None
            self.df_state = None
    
    def _load_silero_vad(self):
        """Load Silero VAD model for voice activity detection."""
        if not SILERO_VAD_AVAILABLE:
            logger.warning("⚠️ Silero VAD not available - using simple amplitude-based VAD")
            logger.warning("   Install with: pip install torch torchaudio")
            return
        
        try:
            logger.info("🔄 Loading Silero VAD (voice activity detection)...")
            # Load Silero VAD model
            self.vad_model, self.vad_utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                trust_repo=True
            )
            
            # Extract utility functions
            (self.get_speech_timestamps,
             self.save_audio,
             self.read_audio,
             self.VADIterator,
             self.collect_chunks) = self.vad_utils
            
            logger.info("✅ Silero VAD loaded successfully!")
        except Exception as e:
            logger.error(f"Failed to load Silero VAD: {e}")
            logger.warning("   Falling back to simple amplitude-based VAD")
            self.vad_model = None
            self.vad_utils = None
    
    def _load_speaker_verification(self):
        """Load speaker verification system (optional, for voice authentication)."""
        if not SPEAKER_VERIFICATION_AVAILABLE:
            logger.debug("Speaker verification module not available (optional feature)")
            return
        
        try:
            # Only initialize if explicitly enabled in config
            if not getattr(self.config, 'speaker_verification_enabled', False):
                logger.debug("Speaker verification disabled in config (set SPEAKER_VERIFICATION_ENABLED=true to enable)")
                return
            
            logger.info("🔄 Loading speaker verification system...")
            self.speaker_verifier = SpeakerVerification(self.config)
            
            if self.speaker_verifier.enabled:
                logger.info("✅ Speaker verification loaded successfully!")
            else:
                logger.warning("⚠️ Speaker verification initialization failed")
                self.speaker_verifier = None
        except Exception as e:
            logger.error(f"Failed to load speaker verification: {e}")
            logger.warning("   Continuing without speaker verification")
            self.speaker_verifier = None
    
    def set_transcription_callback(self, callback: Callable[[str], None]):
        """
        Set callback function for transcription results.
        
        Args:
            callback: Function to call with transcribed text
        """
        self.transcription_callback = callback
    
    def set_audio_level_callback(self, callback: Callable[[float, float, bool], None]):
        """
        Set callback function for audio level updates.
        
        Args:
            callback: Function to call with (audio_level, confidence, is_listening)
        """
        self.audio_level_callback = callback
    
    def start_listening(self):
        """Start listening for audio input."""
        if not self.audio:
            logger.error("Cannot start listening - PyAudio not initialized")
            logger.info("🔄 Attempting to reinitialize PyAudio...")
            if not self._reinitialize_pyaudio():
                logger.error("❌ Failed to reinitialize PyAudio - audio capture unavailable")
                return
        
        if self.is_listening:
            logger.warning("Already listening")
            return
        
        logger.info("🎤 STARTING AUDIO LISTENER...")
        if self.wake_word_enabled:
            logger.info("🔔 Wake word mode: Say 'Nexa' to activate, then give your command")
        else:
            logger.info("🔊 Direct mode: Just speak your command (wake word disabled)")
        self.is_listening = True
        
        # Music ducking strategy:
        # - Wake word mode: Keep music at NORMAL volume during passive listening
        #   Ducking only happens when speech is detected by VAD
        #   Returns to normal volume (85%) after each command
        # - Direct mode: Set listening mode immediately (lower volume for VAD)
        #   Returns to listening volume (70%) after ducking
        if self.music_manager:
            try:
                # Tell music manager about wake word mode for proper volume restoration
                self.music_manager.set_wake_word_mode(self.wake_word_enabled)
                
                if self.wake_word_enabled:
                    # Wake word mode: Keep music at normal volume during passive listening
                    self.music_manager.set_normal_mode()
                    logger.debug("🎵 Wake word mode: Music at normal volume until speech detected")
                else:
                    # Direct mode: Lower volume immediately for speech detection
                    self.music_manager.set_listening_mode()
            except Exception as e:
                logger.debug(f"Failed to set music mode: {e}")
        
        # Start recording thread
        self.recording_thread = threading.Thread(
            target=self._recording_loop,
            name="AudioListenerThread",
            daemon=True
        )
        self.recording_thread.start()
        logger.info("✅ Audio listener thread started - just speak your command!")
    
    def pause_listening(self, for_tts: bool = False):
        """Temporarily pause listening (e.g., during TTS playback or brain processing).
        
        Args:
            for_tts: If True, this pause is for TTS (ducking handled by TTS itself).
                    If False, this is for brain processing (restore music to normal).
        """
        self.is_speaking = True
        
        # During brain processing (thinking), restore music to normal volume
        # User has finished speaking, so they can enjoy full music while waiting
        # TTS will handle its own ducking when it speaks
        if self.music_manager and not for_tts:
            try:
                self.music_manager.set_normal_mode()
                logger.debug("🔊 Music → Normal mode (85%) during thinking")
            except Exception as e:
                logger.debug(f"Failed to set normal mode: {e}")
        
        logger.info(f"🔇 Paused listening {'for TTS' if for_tts else 'for brain processing'}")
    
    def resume_listening(self):
        """Resume listening after pause."""
        self.is_speaking = False
        
        # Set music back to appropriate mode based on wake word setting
        if self.music_manager:
            try:
                if self.wake_word_enabled:
                    # Wake word mode: Return to normal volume
                    self.music_manager.set_normal_mode()
                    logger.debug("🎧 Music → Normal mode (85%) - wake word mode")
                else:
                    # Direct mode: Return to listening volume
                    self.music_manager.set_listening_mode()
                    logger.debug("🎧 Music → Listening mode (70%) - direct mode")
            except Exception as e:
                logger.debug(f"Failed to set music mode: {e}")
        
        logger.info("🔊 Listening resumed")
    
    def pause_for_user(self):
        """Pause listening when user says 'stop listening' - keeps mic active."""
        self.is_paused = True
        logger.info("⏸️ Listening paused by user (mic still active, only listening for 'start listening')")
    
    def resume_for_user(self):
        """Resume listening when user says 'start listening'."""
        self.is_paused = False
        logger.info("▶️ Listening resumed by user")
    
    def stop_listening(self):
        """Stop listening for audio input completely."""
        if not self.is_listening:
            return
        
        self.is_listening = False
        
        # Set music to normal mode when listener stops
        if self.music_manager:
            try:
                self.music_manager.set_normal_mode()
            except Exception as e:
                logger.debug(f"Failed to set normal mode: {e}")
        
        # Don't join if called from the recording thread itself (would cause deadlock)
        current_thread = threading.current_thread()
        if self.recording_thread and self.recording_thread.is_alive():
            if current_thread != self.recording_thread:
                # Only join from a different thread
                self.recording_thread.join(timeout=2.0)
            # If called from recording thread, just set flag and return
        
        logger.info("Stopped listening")
    
    def stop(self):
        """Cleanup audio resources."""
        self.stop_listening()
        
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            except Exception as e:
                logger.debug(f"Error closing stream: {e}")
        
        if self.audio:
            try:
                self.audio.terminate()
                self.audio = None
            except Exception as e:
                logger.debug(f"Error terminating PyAudio: {e}")
        
        logger.info("Audio listener stopped")
    
    def _recording_loop(self):
        """Main recording loop with DeepFilterNet2 noise cancellation and Silero VAD."""
        try:
            # Get default input device
            try:
                default_input = self.audio.get_default_input_device_info()
                input_device_index = default_input['index']
                logger.info(f"🎤 Using input device: {default_input['name']} (index {input_device_index})")
            except Exception as e:
                logger.warning(f"⚠️ Could not get default input device: {e}")
                logger.info("🔍 Searching for available input devices...")
                input_device_index = None
                
            # Open audio stream with explicit device index
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=input_device_index,
                frames_per_buffer=self.chunk_size
            )
            
            logger.info("🎙️ Audio stream opened successfully - listening for speech...")
            if self.df_model:
                logger.info("✨ Noise cancellation: ENABLED (DeepFilterNet2)")
            elif NOISEREDUCE_AVAILABLE:
                logger.info("✨ Noise cancellation: ENABLED (noisereduce - lightweight)")
            else:
                logger.info("⚠️ Noise cancellation: DISABLED")
            
            if self.vad_model:
                logger.info("✨ Voice activity detection: ENABLED (Silero VAD)")
            else:
                logger.info("⚠️ Voice activity detection: FALLBACK (amplitude-based)")
            
            frames = []
            raw_frames = []  # Store original frames before noise cancellation
            pre_speech_buffer = []  # FIX: Buffer to capture audio BEFORE speech detection (catches first word!)
            pre_speech_buffer_size = 5  # Keep last 5 chunks (~0.3s) before speech starts
            silence_duration = 0
            max_silence = 0.8  # PHASE 3 OPTIMIZATION: Reduced from 1.2s to 0.8s for faster cutoff (saves ~0.4s)
            min_speech_duration = 0.6  # FIX: Reduced from 1.0s to 0.6s to catch short commands like "my games"
            
            # BUGFIX (Oct 22): Check if enrollment is active - needs longer duration for long sentences
            # Enrollment prompts can be up to 46 words (~6-8 seconds to speak naturally)
            # Normal commands stay at 4.0s for faster responses
            if hasattr(self, 'speaker_enrollment') and self.speaker_enrollment and self.speaker_enrollment.is_enrolling:
                max_recording_duration = 10.0  # Allow longer sentences during enrollment
            else:
                max_recording_duration = 4.0  # OPTIMIZED: Reduced from 8.0s to 4.0s - stops mic earlier for faster responses
            
            is_speaking = False
            speech_confidence_threshold = 0.45  # Silero VAD confidence threshold (45% for convenient listening range)
            min_start_confidence = 0.45  # Lowered to 45% for easier voice detection
            consecutive_speech_chunks = 0
            consecutive_silence_chunks = 0
            min_consecutive_speech = 2  # FIX: Reduced from 3 to 2 chunks to start recording faster
            min_consecutive_silence = 2  # Need 2 consecutive silence chunks to end
            
            while self.is_listening:
                try:
                    # Skip recording if TTS is speaking (avoid feedback loop)
                    if self.is_speaking:
                        # Discard any accumulated frames during TTS
                        if frames:
                            frames = []
                            raw_frames = []
                            is_speaking = False
                            silence_duration = 0
                            consecutive_speech_chunks = 0
                            consecutive_silence_chunks = 0
                        continue
                    
                    # Check if we were just paused (for debugging timing issues)
                    if not hasattr(self, '_was_speaking'):
                        self._was_speaking = False
                    if self._was_speaking and not self.is_speaking:
                        logger.info("✅ TTS finished, now actively listening for next command")
                        self._was_speaking = False
                    elif self.is_speaking:
                        self._was_speaking = True
                    
                    # Read audio chunk
                    data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                    
                    # Check for speech using Silero VAD on ORIGINAL audio (before noise reduction)
                    # This gives more accurate confidence scores since noise reduction dampens the signal
                    try:
                        is_speech_detected, speech_confidence = self._check_speech_vad(data)
                    except Exception as vad_error:
                        logger.error(f"❌ VAD check failed: {vad_error}", exc_info=True)
                        # Fallback to amplitude-based
                        audio_level = self._get_audio_level(data)
                        is_speech_detected = audio_level > 1500
                        speech_confidence = audio_level / 10000.0
                    
                    # Send audio level update to UI (if callback registered)
                    if self.audio_level_callback and not self.is_paused:
                        try:
                            # Normalize audio level for visualization (0.0 to 1.0)
                            audio_amplitude = min(1.0, speech_confidence * 2.0)  # Scale up for better visualization
                            self.audio_level_callback(audio_amplitude, speech_confidence, is_listening=True)
                        except Exception as callback_error:
                            logger.debug(f"Audio level callback error: {callback_error}")
                    
                    # Apply noise cancellation for recording (but NOT for VAD)
                    try:
                        if self.df_model:
                            clean_data = self._apply_noise_cancellation(data)
                        elif NOISEREDUCE_AVAILABLE:
                            clean_data = self._apply_noisereduce(data)
                        else:
                            clean_data = data
                    except Exception as nc_error:
                        logger.error(f"❌ Noise cancellation failed: {nc_error}")
                        clean_data = data  # Use original if noise cancellation fails
                    
                    # DEBUG: Log VAD results every 2 seconds (DISABLED to reduce log spam)
                    # Uncomment below to debug VAD issues
                    # import time
                    # current_time = time.time()
                    # if not hasattr(self, '_last_debug_log_time'):
                    #     self._last_debug_log_time = current_time
                    #     logger.debug("🔍 VAD monitoring started")
                    # if current_time - self._last_debug_log_time >= 5.0:  # Log every 5 seconds
                    #     logger.debug(f"🔍 VAD: speech={is_speech_detected}, conf={speech_confidence:.2f}, speaking={is_speaking}, frames={len(frames)}")
                    #     self._last_debug_log_time = current_time
                    
                    # Update consecutive counters FIRST (before storing frames)
                    if is_speech_detected:
                        consecutive_speech_chunks += 1
                        consecutive_silence_chunks = 0
                    else:
                        consecutive_silence_chunks += 1
                        consecutive_speech_chunks = 0
                    
                    # DUCKING STRATEGY for Wake Word Mode:
                    # In wake word mode, we DON'T want any ducking during passive listening.
                    # Music should play at full volume until:
                    # 1. Wake word is detected (then duck while user gives command)
                    # 2. Nexa speaks (TTS handles its own ducking)
                    # 
                    # The problem: Music vocals trigger VAD at 15-50% confidence,
                    # causing constant pre-ducking. Solution: Disable pre-ducking entirely
                    # in wake word mode during passive listening.
                    
                    if self.wake_word_enabled:
                        # Wake word mode: Only duck when wake word is active (user giving command)
                        duck_threshold = 0.60  # 60% - real speech is usually above this
                        pre_duck_threshold = 0.90  # Effectively disabled - almost nothing triggers this
                        enable_pre_ducking = self.wake_word_active  # Only pre-duck after wake word detected
                    else:
                        # Direct mode: Normal thresholds
                        duck_threshold = 0.45
                        pre_duck_threshold = 0.15
                        enable_pre_ducking = True
                    
                    # PRE-DUCKING: Lower music volume when speech probability detected
                    # In wake word mode, this only activates AFTER wake word is detected
                    if not is_speaking and self.music_manager and enable_pre_ducking:
                        try:
                            if speech_confidence >= pre_duck_threshold:
                                self.music_manager.enable_pre_ducking()
                            elif speech_confidence < 0.10 and consecutive_silence_chunks >= 3:
                                # Low probability and sustained silence = disable pre-ducking
                                self.music_manager.disable_pre_ducking()
                        except Exception as pre_duck_error:
                            logger.warning(f"Pre-ducking error: {pre_duck_error}")
                    
                    # Check if we should start recording (with confidence gating)
                    if not is_speaking and consecutive_speech_chunks >= min_consecutive_speech:
                        # Only start recording if confidence is high enough (reduces false triggers)
                        # Use the wake-word-mode-aware threshold
                        if speech_confidence >= duck_threshold:
                            logger.info(f"🎤 Listening... (confidence: {speech_confidence:.0%})")
                            is_speaking = True
                            silence_duration = 0
                            
                            # FULL DUCKING: Only duck if wake word is active (user giving command)
                            # In passive wake word mode, we don't duck - music plays at full volume
                            # until user says "Nexa" and gives a command
                            if self.music_manager and (not self.wake_word_enabled or self.wake_word_active):
                                try:
                                    self.music_manager.enable_ducking()
                                except Exception as duck_error:
                                    logger.debug(f"Ducking enable error: {duck_error}")
                            elif self.wake_word_enabled and not self.wake_word_active:
                                # In passive wake word mode - don't duck, just log that we heard audio
                                logger.debug(f"🎵 Wake word mode: Ignoring VAD trigger (music), waiting for 'Nexa'...")
                            
                            # FIX: Include pre-speech buffer to capture the first word!
                            # This catches audio that was spoken BEFORE VAD triggered
                            frames = list(pre_speech_buffer)  # Copy buffer to frames
                            raw_frames = list(pre_speech_buffer)  # Copy to raw frames too
                            logger.debug(f"   ├─ Included {len(pre_speech_buffer)} pre-speech chunks ({len(pre_speech_buffer) * self.chunk_size / self.sample_rate:.2f}s)")
                        else:
                            logger.debug(f"⏩ Skipped low-confidence speech ({speech_confidence:.0%}, need ≥{int(duck_threshold*100)}%)")
                            consecutive_speech_chunks = 0  # Reset to avoid accumulating low-confidence chunks
                    
                    # Maintain pre-speech buffer (rolling window of last N chunks)
                    # This allows us to capture audio BEFORE speech detection triggers
                    if not is_speaking:
                        pre_speech_buffer.append(clean_data)
                        if len(pre_speech_buffer) > pre_speech_buffer_size:
                            pre_speech_buffer.pop(0)  # Remove oldest chunk
                    
                    # Only store frames if we're actively recording speech
                    if is_speaking:
                        frames.append(clean_data)
                        raw_frames.append(data)
                    
                    # Check if recording is too long (prevent endless captures)
                    current_recording_duration = len(frames) * self.chunk_size / self.sample_rate if is_speaking else 0
                    if current_recording_duration >= max_recording_duration and is_speaking:
                        logger.warning(f"⏱️ Max recording duration reached ({max_recording_duration}s) - forcing transcription")
                        speech_duration = len(frames) * self.chunk_size / self.sample_rate
                        logger.info(f"🗣️ Speech ended - transcribing {len(frames)} frames ({speech_duration:.2f}s)...")
                        self._transcribe_audio(frames)
                        is_speaking = False
                        frames = []
                        raw_frames = []
                        silence_duration = 0
                        consecutive_speech_chunks = 0
                        consecutive_silence_chunks = 0
                        pre_speech_buffer = []  # Clear buffer
                        
                        # DUCKING: Restore normal volume after recording
                        if self.music_manager:
                            try:
                                self.music_manager.disable_ducking()
                            except Exception as duck_error:
                                logger.debug(f"Ducking disable error: {duck_error}")
                        
                        continue
                    
                    # If we're speaking, check for speech end
                    if is_speaking:
                        if is_speech_detected:
                            # Still speaking - reset silence
                            silence_duration = 0
                        else:
                            # Silence detected - calculate duration
                            silence_duration = (consecutive_silence_chunks * self.chunk_size) / self.sample_rate
                            
                            # Check if we should end recording
                            if consecutive_silence_chunks >= min_consecutive_silence and silence_duration >= max_silence:
                                speech_duration = len(frames) * self.chunk_size / self.sample_rate
                                if speech_duration >= min_speech_duration:
                                    logger.info(f"📝 Transcribing {speech_duration:.1f}s of audio...")
                                    self._transcribe_audio(frames)
                                else:
                                    logger.info(f"⏩ Ignored {speech_duration:.1f}s clip (too short, need ≥1.0s)")
                                
                                is_speaking = False
                                frames = []
                                raw_frames = []
                                silence_duration = 0
                                consecutive_speech_chunks = 0
                                consecutive_silence_chunks = 0
                                
                                # DUCKING: Restore normal volume after recording
                                if self.music_manager:
                                    try:
                                        self.music_manager.disable_ducking()
                                    except Exception as duck_error:
                                        logger.debug(f"Ducking disable error: {duck_error}")
                
                except Exception as e:
                    logger.error(f"❌ Error in recording loop iteration: {e}", exc_info=True)
                    # Don't break - try to continue
            
            logger.info("🛑 Recording loop ended (is_listening=False)")
        
        except OSError as e:
            # Audio device error - attempt recovery
            if "Invalid input device" in str(e) or "-9996" in str(e):
                logger.error(f"❌ Audio device error: {e}")
                logger.info("🔄 Attempting to recover audio device...")
                
                # Try to reinitialize PyAudio
                if self._reinitialize_pyaudio():
                    logger.info("✅ PyAudio reinitialized - please restart Nexa")
                else:
                    logger.error("❌ Failed to recover audio device")
            else:
                logger.error(f"❌ CRITICAL OSError in recording loop: {e}", exc_info=True)
        
        except Exception as e:
            logger.error(f"❌ CRITICAL Error in recording loop: {e}", exc_info=True)
        finally:
            if self.stream:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except:
                    pass  # Ignore errors during cleanup
    
    def _apply_noise_cancellation(self, audio_data: bytes) -> bytes:
        """
        Apply DeepFilterNet2 noise cancellation to audio chunk.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            Noise-cancelled audio bytes
        """
        if not self.df_model or not self.df_state:
            # No noise cancellation available, return original
            return audio_data
        
        try:
            import numpy as np
            
            # Convert bytes to numpy array
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Reshape for DeepFilterNet2 (expects shape: [channels, samples])
            audio_tensor = torch.from_numpy(audio_np).unsqueeze(0)
            
            # Apply noise cancellation
            with torch.no_grad():
                enhanced_audio = enhance(self.df_model, self.df_state, audio_tensor)
            
            # Mix enhanced audio with original (reduce aggressiveness)
            # This preserves more of the original voice while still reducing noise
            enhanced_np = enhanced_audio.squeeze().numpy()
            mix_ratio = 0.6  # 60% enhanced, 40% original (was 100% enhanced)
            mixed_audio = (enhanced_np * mix_ratio) + (audio_np * (1 - mix_ratio))
            
            # Convert back to bytes
            mixed_audio = np.clip(mixed_audio * 32768.0, -32768, 32767).astype(np.int16)
            
            return mixed_audio.tobytes()
            
        except Exception as e:
            logger.debug(f"Noise cancellation failed, using original audio: {e}")
            return audio_data
    
    def _apply_noisereduce(self, audio_data: bytes) -> bytes:
        """
        Apply lightweight noisereduce noise cancellation to audio chunk.
        Fast, no GPU required, minimal overhead.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            Noise-reduced audio bytes
        """
        if not NOISEREDUCE_AVAILABLE:
            return audio_data
        
        try:
            import numpy as np
            
            # Convert bytes to numpy array
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Apply lightweight noise reduction (stationary noise only)
            # Uses spectral gating - very fast, no ML model needed
            reduced = nr.reduce_noise(
                y=audio_np,
                sr=self.sample_rate,
                stationary=True,  # Assume stationary noise (fan, AC, etc.)
                prop_decrease=0.5  # Reduce noise by 50% (was 0.8 - too aggressive)
            )
            
            # Convert back to bytes
            reduced_np = np.clip(reduced * 32768.0, -32768, 32767).astype(np.int16)
            return reduced_np.tobytes()
            
        except Exception as e:
            logger.debug(f"Noisereduce failed, using original audio: {e}")
            return audio_data
    
    def _check_speech_vad(self, audio_data: bytes) -> tuple[bool, float]:
        """
        Check if audio contains speech using Silero VAD.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            Tuple of (is_speech, confidence)
        """
        if not self.vad_model:
            # Fallback to amplitude-based detection
            audio_level = self._get_audio_level(audio_data)
            # Simple threshold: above 1500 = might be speech
            is_speech = audio_level > 1500
            confidence = audio_level / 10000.0
            
            # Log first time fallback is used
            if not hasattr(self, '_fallback_logged'):
                self._fallback_logged = True
                logger.warning("⚠️ Using amplitude-based VAD fallback (Silero VAD not available)")
            
            return (is_speech, confidence)
        
        try:
            import numpy as np
            
            # Convert bytes to numpy array
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Convert to tensor (Silero VAD expects 16kHz, resample if needed)
            audio_tensor = torch.from_numpy(audio_np)
            
            # Resample to 16kHz if our sample rate is different
            if self.sample_rate != 16000:
                resampler = torchaudio.transforms.Resample(
                    orig_freq=self.sample_rate,
                    new_freq=16000
                )
                audio_tensor = resampler(audio_tensor)
            
            # Get speech probability from Silero VAD
            with torch.no_grad():
                speech_prob = self.vad_model(audio_tensor, 16000).item()
            
            # Threshold: 0.5 means 50% confidence that it's speech
            is_speech = speech_prob > 0.5
            
            return (is_speech, speech_prob)
            
        except Exception as e:
            logger.debug(f"VAD check failed, falling back to amplitude: {e}")
            # Fallback
            audio_level = self._get_audio_level(audio_data)
            return (audio_level > 1500, audio_level / 10000.0)
    
    def _get_audio_level(self, data: bytes) -> float:
        """
        Calculate audio level from raw audio data.
        Simple RMS calculation.
        
        Args:
            data: Raw audio bytes
            
        Returns:
            Audio level
        """
        import array
        samples = array.array('h', data)
        return sum(abs(s) for s in samples) / len(samples)
    
    def _transcribe_audio(self, frames: list):
        """
        Transcribe recorded audio using faster-whisper (GPU-accelerated).
        
        Args:
            frames: List of audio frames
        """
        if not frames:
            return
        
        if not self.whisper_model:
            logger.error("Whisper model not loaded - cannot transcribe")
            return
        
        try:
            # Create temporary WAV file
            temp_fd, temp_path_str = tempfile.mkstemp(suffix='.wav')
            temp_path = Path(temp_path_str)
            
            try:
                # Close the file descriptor immediately
                import os
                os.close(temp_fd)
                
                # Write WAV file
                with wave.open(str(temp_path), 'wb') as wf:
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(self.audio.get_sample_size(self.format))
                    wf.setframerate(self.sample_rate)
                    wf.writeframes(b''.join(frames))
                
                logger.debug(f"💾 Saved audio: {temp_path.stat().st_size / 1024:.1f}KB")
                
                # ===== SPEAKER ENROLLMENT (if active) =====
                # Check if enrollment is in progress - if yes, process audio for enrollment
                if self.speaker_enrollment and self.speaker_enrollment.is_enrolling:
                    try:
                        # Notify UI of RECOGNIZING state
                        if self.state_callback:
                            sample_num = self.speaker_enrollment.current_prompt_index + 1
                            total_samples = self.speaker_enrollment.num_samples
                            self.state_callback("recognizing", f"Processing voice sample {sample_num}/{total_samples}")
                        
                        # Extract raw audio data from frames
                        audio_bytes = b''.join(frames)
                        import numpy as np
                        audio_data = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                        
                        # Process enrollment audio
                        logger.info(f"🔍 Processing enrollment sample {self.speaker_enrollment.current_prompt_index + 1}/{self.speaker_enrollment.num_samples}")
                        self.speaker_enrollment.process_enrollment_audio(audio_data, self.sample_rate)
                        
                        # Return to LISTENING state after processing
                        if self.state_callback:
                            self.state_callback("listening", "Waiting for next sample")
                        
                        # Cleanup temp file and return (don't transcribe during enrollment)
                        try:
                            temp_path.unlink()
                        except:
                            pass
                        return  # Skip normal transcription during enrollment
                    except Exception as e:
                        logger.error(f"Error processing enrollment audio: {e}")
                        # Continue to normal transcription if enrollment fails
                # ===== END SPEAKER ENROLLMENT =====
                
                # ===== SPEAKER VERIFICATION (if enabled) =====
                # Check speaker identity BEFORE transcription to save resources
                if self.speaker_verifier and self.speaker_verifier.is_enabled():
                    try:
                        # Extract audio data for verification
                        audio_bytes = b''.join(frames)
                        
                        # Verify speaker identity
                        is_verified, similarity = self.speaker_verifier.verify_speaker_from_audio_bytes(
                            audio_bytes, 
                            self.sample_rate
                        )
                        
                        if not is_verified:
                            reject_unknown = getattr(self.config, 'speaker_reject_unknown', True)
                            if reject_unknown:
                                logger.warning(f"❌ Unknown speaker rejected (similarity: {similarity*100:.1f}%)")
                                
                                # Notify brain about rejection (will trigger TTS response)
                                if self.speaker_rejection_callback:
                                    self.speaker_rejection_callback(similarity)
                                
                                # Cleanup temp file before returning
                                try:
                                    temp_path.unlink()
                                except:
                                    pass
                                return  # Ignore this audio completely
                            else:
                                logger.warning(f"⚠️ Unknown speaker detected but not rejected (similarity: {similarity*100:.1f}%)")
                        else:
                            logger.debug(f"✅ Speaker VERIFIED ({similarity*100:.1f}% match)")
                    except Exception as e:
                        logger.error(f"Speaker verification error (continuing anyway): {e}")
                # ===== END SPEAKER VERIFICATION =====
                
                # Run faster-whisper transcription (GPU-accelerated!)
                transcription = self._run_whisper(temp_path)
                
                # Send to callback (unless paused)
                if transcription and self.transcription_callback:
                    # If paused, only listen for "start listening" command
                    if self.is_paused:
                        transcription_lower = transcription.lower()
                        if "start listening" in transcription_lower or "resume listening" in transcription_lower:
                            logger.info("▶️ Detected 'start listening' while paused")
                            self.transcription_callback(transcription)
                        else:
                            logger.debug(f"⏸️ Ignoring transcription while paused: '{transcription}'")
                    else:
                        # ===== WAKE WORD DETECTION =====
                        # Check for wake word before sending to brain
                        wake_word_found, command = self._check_wake_word(transcription)
                        
                        if wake_word_found:
                            if command:
                                # Wake word + command found, send command to brain
                                self.transcription_callback(command)
                            else:
                                # Wake word detected alone, play acknowledgment sound
                                # The callback will be called when the actual command comes
                                logger.info("🔔 Waiting for command after wake word...")
                        else:
                            # No wake word - ignore (unless wake word is disabled)
                            if not self.wake_word_enabled:
                                self.transcription_callback(transcription)
                            else:
                                logger.debug(f"⏭️ Ignored (no wake word): '{transcription}'")
                        # ===== END WAKE WORD DETECTION =====
                else:
                    logger.debug("No transcription to send to callback")
                
                # Cleanup temp file
                try:
                    temp_path.unlink()
                except:
                    pass
                    
            except Exception as e:
                logger.error(f"Error in WAV processing: {e}", exc_info=True)
        
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}", exc_info=True)
    
    def _run_whisper(self, audio_file: Path) -> Optional[str]:
        """
        Run faster-whisper to transcribe audio file (GPU-accelerated).
        
        Args:
            audio_file: Path to audio file
            
        Returns:
            Transcribed text or None
        """
        if not self.whisper_model:
            logger.error("Whisper model not loaded")
            return None
        
        try:
            # Apply lightweight noise reduction if available
            if NOISEREDUCE_AVAILABLE:
                try:
                    import soundfile as sf
                    
                    # Load audio
                    audio_data, sample_rate = sf.read(str(audio_file))
                    
                    # Apply noise reduction (stationary noise reduction - fast!)
                    logger.debug("🔇 Applying noise reduction...")
                    reduced_audio = nr.reduce_noise(
                        y=audio_data,
                        sr=sample_rate,
                        stationary=True,  # Assume stationary background noise (fan, AC)
                        prop_decrease=0.5  # Reduce noise by 50% (balanced - was 0.8/80% which was too aggressive)
                    )
                    
                    # Save cleaned audio back to file
                    sf.write(str(audio_file), reduced_audio, sample_rate)
                    logger.debug("✅ Noise reduced")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Noise reduction failed: {e}")
            
            # Transcribe with faster-whisper (uses GPU!)
            segments, info = self.whisper_model.transcribe(
                str(audio_file),
                language="en",
                beam_size=5,
                vad_filter=False  # Disabled VAD due to onnxruntime DLL issues on Windows
            )
            
            # 🔥 MEMORY MANAGEMENT: Clear CUDA cache immediately after transcription
            # Prevents GPU memory fragmentation that causes crashes
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    logger.debug("🧹 CUDA cache cleared after transcription")
            except Exception as e:
                logger.debug(f"Could not clear CUDA cache: {e}")
            
            # Extract transcription text
            transcription = " ".join([segment.text for segment in segments]).strip()
            
            # Correct common mishearings (like "next sir" → "Nexa")
            transcription = self._correct_common_mishearings(transcription)
            
            # Remove duplicate phrases (happens when user holds mic too long)
            transcription = self._remove_duplicate_phrases(transcription)
            
            if transcription:
                logger.info(f"✅ You said: \"{transcription}\"")
                logger.debug(f"   Language: {info.language} ({info.language_probability:.0%})")
                return transcription
            else:
                logger.debug("No speech detected in audio")
                return None
        
        except Exception as e:
            logger.error(f"Error running Whisper: {e}", exc_info=True)
            return None
    
    def _correct_common_mishearings(self, text: str) -> str:
        """
        Correct common transcription errors for custom vocabulary.
        Post-processes Whisper output to fix known mishearings.
        
        Args:
            text: Original transcription from Whisper
            
        Returns:
            Corrected transcription
        """
        if not text:
            return text
        
        import re
        
        # Define corrections: {wrong: correct}
        # Case-insensitive replacement for phonetically similar words
        # CRITICAL: Only correct CLEAR mishearings, not legitimate phrases!
        corrections = {
            # "Nexa" variations (most common mishearings)
            r'\bnext sir\b': 'Nexa',
            r'\bnecsa\b': 'Nexa',
            r'\bnex sir\b': 'Nexa',
            r'\bnexus\b': 'Nexa',  # Context-aware: only if not talking about Google Nexus
            r'\bnexar\b': 'Nexa',
            r'\bnexa sir\b': 'Nexa',
            r'\bnext sa\b': 'Nexa',
            r'\bnext to\b': 'Nexa',  # "how are you next to?" → "how are you Nexa?"
            
            # Other common mishearings (phonetically similar words only)
            r'\bold life\b': 'online',  # "are you old life?" → "are you online?"
            r'\bof line\b': 'offline',
            r'\bon life\b': 'online',
            r'\ball right\b': 'alright',  # Normalize
        }
        
        original_text = text
        corrected_text = text
        
        # Apply corrections (case-insensitive)
        for pattern, replacement in corrections.items():
            new_text = re.sub(pattern, replacement, corrected_text, flags=re.IGNORECASE)
            if new_text != corrected_text:
                # Log what was corrected
                matches = re.findall(pattern, corrected_text, flags=re.IGNORECASE)
                if matches:
                    logger.info(f"📝 Corrected: '{matches[0]}' → '{replacement}'")
                corrected_text = new_text
        
        # If nothing changed, no need to log
        if corrected_text == original_text:
            return corrected_text
        
        # Log final result if changed
        if corrected_text != original_text:
            logger.info(f"✏️ Transcription corrected: '{original_text}' → '{corrected_text}'")
        
        return corrected_text
    
    def _remove_duplicate_phrases(self, text: str) -> str:
        """
        Remove duplicate phrases from transcription.
        Example: "What's my battery? What's my battery?" → "What's my battery?"
        
        Args:
            text: Original transcription
            
        Returns:
            Cleaned transcription without duplicates
        """
        if not text:
            return text
        
        # Split by common sentence delimiters
        import re
        sentences = re.split(r'[.!?]\s*', text)
        
        # Remove empty strings
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= 1:
            return text
        
        # Check if all sentences are identical or very similar
        first_sentence = sentences[0].lower()
        all_same = all(s.lower() == first_sentence for s in sentences)
        
        if all_same:
            logger.info(f"🧹 Removed {len(sentences) - 1} duplicate phrases")
            return sentences[0]  # Return just the first occurrence
        
        # Check for repetitive patterns (2-3 word phrases repeated)
        words = text.split()
        if len(words) > 6:
            # Check if first half equals second half
            midpoint = len(words) // 2
            first_half = ' '.join(words[:midpoint]).lower()
            second_half = ' '.join(words[midpoint:midpoint*2]).lower()
            
            if first_half == second_half:
                logger.info(f"🧹 Removed duplicate half: '{second_half}'")
                return ' '.join(words[:midpoint])
        
        return text
    
    def _check_wake_word(self, text: str) -> tuple[bool, str]:
        """
        Check if text contains wake word using fuzzy phonetic matching.
        This handles Whisper misrecognitions like "next", "next up", "necks", etc.
        
        Args:
            text: Transcribed text
            
        Returns:
            Tuple of (wake_word_found, remaining_command)
            - If wake word found with command: (True, "the command")
            - If wake word found alone: (True, "")
            - If no wake word: (False, original_text)
        """
        import time
        import re
        
        if not self.wake_word_enabled:
            # Wake word disabled - return text as-is
            return (True, text)
        
        text_lower = text.lower().strip()
        
        # Check if we're in "wake word active" state (already detected, waiting for command)
        current_time = time.time()
        if self.wake_word_active:
            # Check if timeout expired
            if current_time - self.wake_word_detected_time > self.wake_word_timeout:
                logger.info("⏰ Wake word timeout - returning to passive listening")
                self.wake_word_active = False
                # Restore music to normal volume
                if self.music_manager:
                    self.music_manager.disable_ducking()
            else:
                # Still within timeout - this is the command
                logger.info(f"🎯 Command received: \"{text}\"")
                self.wake_word_active = False  # Reset for next command
                return (True, text)
        
        def sounds_like_nexa(word: str) -> bool:
            """
            Check if a word sounds like 'Nexa' using phonetic patterns.
            This catches Whisper misrecognitions dynamically.
            """
            word = word.lower().strip('.,!?"\' ')
            
            # Exact matches
            if word in ['nexa', 'nexus', 'nex']:
                return True
            
            # Starts with 'nex' - very likely meant Nexa
            if word.startswith('nex'):
                return True
            
            # Common Whisper misrecognitions that sound like "Nexa"
            # "next" is the most common - N-EX-T sounds like N-EX-A
            # "exha", "exa" - Whisper sometimes drops the 'n' or adds 'h'
            if word in ['next', 'necks', 'neck', 'nets', 'lex', 'lexa', 'alexa',
                        'exha', 'exa', 'neha', 'mecha', 'nexia', 'nixie', 'nessa',
                        'alexa', 'extra', 'texha', 'texa', 'hexa', 'vexha']:
                return True
            
            # Words ending in 'xa' or 'xha' that sound like Nexa
            if word.endswith('xa') or word.endswith('xha') or word.endswith('xah'):
                return True
            
            # Phonetic similarity: starts with 'n' and contains 'x' or 'ks' sound
            if word.startswith('n') and ('x' in word or 'ks' in word or 'cks' in word):
                return True
            
            # Contains 'ex' and is short (likely meant Nexa)
            if 'ex' in word and len(word) <= 5:
                return True
            
            # Check Levenshtein-like similarity (simple version)
            # If word is close to "nexa" (1-2 character difference)
            if len(word) >= 3 and len(word) <= 6:
                # Count matching characters in sequence
                nexa = "nexa"
                matches = sum(1 for i, c in enumerate(word[:4]) if i < len(nexa) and c == nexa[i])
                if matches >= 2:  # At least 2 of first 4 chars match "nexa"
                    return True
            
            return False
        
        def find_wake_word_position(text: str) -> tuple[int, int]:
            """
            Find wake word in text, return (start_pos, end_pos) or (-1, -1) if not found.
            Handles multi-word phrases like "next up", "hey next", etc.
            """
            words = text.split()
            
            # Check first 1-3 words for wake word patterns
            for i in range(min(3, len(words))):
                word = words[i].lower().strip('.,!?"\' ')
                
                # Skip common prefixes
                if word in ['hey', 'ok', 'okay', 'hi', 'hello', 'yo', 'bye']:
                    continue
                
                if sounds_like_nexa(word):
                    # Found it! Calculate position
                    start_pos = text.lower().find(words[i].lower())
                    end_pos = start_pos + len(words[i])
                    
                    # Check if next word is a "filler" like "up", "sir", "her", "to", "a"
                    # These are often part of misrecognized "Nexa"
                    if i + 1 < len(words):
                        next_word = words[i + 1].lower().strip('.,!?"\' ')
                        if next_word in ['up', 'sir', 'her', 'to', 'a', 'the', 'ah', 'uh', 'um']:
                            # Include this filler word as part of wake word
                            end_pos = text.lower().find(words[i + 1].lower()) + len(words[i + 1])
                    
                    return (start_pos, end_pos)
            
            return (-1, -1)
        
        # Find wake word in text
        start_pos, end_pos = find_wake_word_position(text)
        
        if start_pos >= 0:
            # Extract command after wake word
            remaining = text[end_pos:].strip()
            remaining = remaining.lstrip('.,!? ')
            
            detected_wake = text[start_pos:end_pos]
            
            if remaining:
                # Wake word + command in same utterance
                logger.info(f"🎙️ Wake word detected ('{detected_wake}' → 'Nexa'), command: \"{remaining}\"")
                self.wake_word_active = False
                # Duck music while processing command
                if self.music_manager:
                    self.music_manager.enable_ducking()
                return (True, remaining)
            else:
                # Just the wake word - wait for command
                logger.info(f"🎙️ Wake word detected ('{detected_wake}' → 'Nexa') - listening for command...")
                self.wake_word_active = True
                self.wake_word_detected_time = current_time
                
                # Duck music while waiting for command
                if self.music_manager:
                    self.music_manager.enable_ducking()
                
                # Provide audio feedback
                if self.state_callback:
                    self.state_callback("wake_word", "I'm listening...")
                
                return (True, "")
        
        # No wake word found
        if self.wake_word_active:
            # We were waiting for command
            logger.info(f"🎯 Follow-up command: \"{text}\"")
            self.wake_word_active = False
            return (True, text)
        
        # Not in active state, no wake word - ignore
        logger.debug(f"⏸️ No wake word detected - ignoring: \"{text}\"")
        return (False, text)
    
    def enable_wake_word(self, enabled: bool = True):
        """Enable or disable wake word detection."""
        self.wake_word_enabled = enabled
        if enabled:
            logger.info("🎙️ Wake word detection ENABLED - say 'Nexa' to activate")
        else:
            logger.info("🔊 Wake word detection DISABLED - always listening")
    
    def is_wake_word_mode(self) -> bool:
        """Check if wake word mode is enabled."""
        return self.wake_word_enabled

