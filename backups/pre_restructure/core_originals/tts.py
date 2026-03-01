"""
TTS Engine using Kokoro TTS (Local, 82M parameters, Apache-2.0 license)
Voice: af_heart (American Female, warm and natural)
Uses subprocess isolation to avoid DLL conflicts with PyTorch CUDA

OPTIMIZED: Sentence-level streaming for reduced latency on long text.
- First sentence plays in ~0.5s regardless of total text length
- Background thread generates remaining sentences while playing
- Pre-buffering minimizes gaps between sentences
"""

import os
import sys
import time
import logging
import tempfile
import threading
import queue
import re
from pathlib import Path
import pygame
import urllib.request
import soundfile as sf
import subprocess
import numpy as np

logger = logging.getLogger(__name__)

# Lazy imports to avoid DLL loading issues at startup
Kokoro = None
SAMPLE_RATE = 24000  # Default, will be updated when Kokoro loads

# Sentence splitting pattern - split on . ! ? followed by space or end
# Keeps the punctuation with the sentence
SENTENCE_PATTERN = re.compile(r'(?<=[.!?])\s+')


def _get_espeak_data_path():
    """
    Get the espeak-ng data path, handling both frozen and normal Python environments.
    
    Returns:
        Path to espeak-ng-data directory
    """
    if getattr(sys, 'frozen', False):
        # Running as frozen exe - look in _internal folder
        base_path = Path(sys._MEIPASS)
        espeak_path = base_path / 'espeakng_loader' / 'espeak-ng-data'
        if espeak_path.exists():
            return str(espeak_path)
        # Fallback to alternative locations
        alt_paths = [
            base_path / 'espeak-ng-data',
            base_path / '_internal' / 'espeakng_loader' / 'espeak-ng-data',
        ]
        for alt in alt_paths:
            if alt.exists():
                return str(alt)
        logger.warning(f"espeak-ng-data not found in frozen app at expected locations")
        return None
    else:
        # Running normally - use espeakng_loader's path
        try:
            import espeakng_loader
            return espeakng_loader.get_data_path()
        except ImportError:
            logger.warning("espeakng_loader not installed")
            return None


def _lazy_import_kokoro():
    """Lazy import of Kokoro to avoid DLL conflicts at startup."""
    global Kokoro, SAMPLE_RATE
    if Kokoro is None:
        # Set espeak data path before importing kokoro
        espeak_path = _get_espeak_data_path()
        if espeak_path:
            os.environ['ESPEAK_DATA_PATH'] = espeak_path
            logger.debug(f"Set ESPEAK_DATA_PATH={espeak_path}")
        
        from kokoro_onnx import Kokoro as KokoroClass
        from kokoro_onnx.config import SAMPLE_RATE as KokoroSampleRate
        Kokoro = KokoroClass
        SAMPLE_RATE = KokoroSampleRate
    return Kokoro, SAMPLE_RATE


def _split_sentences(text: str) -> list:
    """
    Split text into sentences for streaming TTS.
    
    Args:
        text: Text to split
        
    Returns:
        List of sentences (non-empty, stripped)
    """
    # Clean text first
    clean_text = text.replace('\n', ' ').replace('\r', ' ').strip()
    clean_text = ' '.join(clean_text.split())
    
    if not clean_text:
        return []
    
    # Split on sentence boundaries
    sentences = SENTENCE_PATTERN.split(clean_text)
    
    # Filter empty and strip
    sentences = [s.strip() for s in sentences if s.strip()]
    
    # If no splits happened (single sentence), return as-is
    if not sentences:
        sentences = [clean_text]
    
    return sentences


class TTSEngine:
    """Kokoro TTS Engine with af_heart voice."""
    
    def __init__(self, config):
        """Initialize Kokoro TTS engine with streaming support."""
        self.config = config
        self.kokoro = None
        self.voice_name = "af_heart"  # American Female, warm heart
        self.sample_rate = SAMPLE_RATE  # 24000 Hz
        self.current_channel = None  # Track active sound channel
        
        # State callbacks (for notifying brain when speaking starts/stops)
        self.speaking_start_callback = None
        self.speaking_end_callback = None
        
        # Response text callback (for companion speech bubble)
        # This callback receives the text being spoken so companion can display it
        self.response_text_callback = None
        
        # === STREAMING TTS INFRASTRUCTURE ===
        # Audio queue for streaming playback
        self._audio_queue = queue.Queue()
        # Stop flag for interrupting streaming playback
        self._stop_event = threading.Event()
        # Lock for thread-safe access to playback state
        self._playback_lock = threading.Lock()
        # Track if streaming is active
        self._is_streaming = False
        # Current playback sounds (for cleanup)
        self._current_sounds = []
        
        # Setup pygame for audio playback
        pygame.mixer.init(channels=8)  # Allow multiple channels
        logger.info("🔊 Pygame mixer initialized for audio playback")
        
        # Model paths
        self.model_dir = self.config.voice_dir / "kokoro_models"
        self.model_path = self.model_dir / "kokoro-v1.0.onnx"
        self.voices_path = self.model_dir / "voices-v1.0.bin"
        
        # Initialize Kokoro
        self._init_kokoro()
    
    def _download_models(self):
        """Download Kokoro models if not present."""
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.model_path.exists():
            logger.info("📥 Downloading Kokoro model (v1.0, 310MB)...")
            url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
            try:
                urllib.request.urlretrieve(url, str(self.model_path))
                size_mb = self.model_path.stat().st_size / 1024 / 1024
                logger.info(f"✅ Model downloaded ({size_mb:.1f} MB)")
            except Exception as e:
                logger.error(f"❌ Failed to download model: {e}")
                raise
        
        if not self.voices_path.exists():
            logger.info("📥 Downloading voices file (v1.0, 27MB)...")
            url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
            try:
                urllib.request.urlretrieve(url, str(self.voices_path))
                size_mb = self.voices_path.stat().st_size / 1024 / 1024
                logger.info(f"✅ Voices downloaded ({size_mb:.1f} MB)")
            except Exception as e:
                logger.error(f"❌ Failed to download voices: {e}")
                raise
    
    def _init_kokoro(self):
        """Initialize Kokoro TTS model (keep loaded in memory for fast generation)."""
        try:
            # Download models if needed
            self._download_models()
            
            # Verify models exist
            if not (self.model_path.exists() and self.voices_path.exists()):
                raise FileNotFoundError("Kokoro models not found after download")
            
            # Load model into memory for fast generation
            logger.info("� Loading Kokoro model into memory...")
            start_time = time.time()
            
            KokoroClass, sample_rate = _lazy_import_kokoro()
            self.kokoro = KokoroClass(str(self.model_path), str(self.voices_path))
            self.sample_rate = sample_rate
            
            load_time = time.time() - start_time
            logger.info(f"✅ Kokoro model loaded in {load_time:.2f}s - {self.voice_name} voice ready")
            logger.info("⚡ Using in-memory model for fast generation")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Kokoro TTS: {e}")
            raise
    
    def speak(self, text, wait=True, ducking=False, blocking=True, silent=False, speed=1.0):
        """
        Generate and play speech using Kokoro TTS.
        
        Args:
            text: Text to speak
            wait: Whether to wait for playback to finish (deprecated, use blocking)
            ducking: Whether to duck background music during speech
            blocking: Whether to block until speech completes.
                      If False, runs TTS in a background thread so the caller (e.g. UI) is not frozen.
            silent: If True, skip state callbacks (for thinking feedback - stay in THINKING state)
            speed: Speech speed multiplier (0.5 = half speed, 1.0 = normal, 2.0 = double)
        """
        if not text or not text.strip():
            logger.warning("⚠️ Empty text provided to TTS")
            return
        
        if blocking:
            # Synchronous path - blocks caller until speech finishes
            self._speak_core(text, ducking=ducking, silent=silent, speed=speed)
        else:
            # Non-blocking path - run TTS in a background thread so UI stays responsive
            tts_thread = threading.Thread(
                target=self._speak_core,
                args=(text,),
                kwargs={"ducking": ducking, "silent": silent, "speed": speed},
                daemon=True,
                name="TTS-NonBlocking"
            )
            tts_thread.start()
            logger.debug("🔊 TTS started in non-blocking mode (background thread)")
    
    def _speak_core(self, text, ducking=False, silent=False, speed=1.0):
        """
        Core speak implementation. Always runs synchronously.
        Called directly for blocking mode, or in a background thread for non-blocking.
        
        Args:
            text: Text to speak
            ducking: Whether to duck background music during speech
            silent: If True, skip state callbacks
            speed: Speech speed multiplier
        """
        try:
            # CRITICAL: Stop any currently playing speech to prevent echo/overlap
            if self.is_speaking():
                logger.info("🔊 Stopping previous speech before starting new")
                self.stop()
            
            # Notify that speaking is starting (skip if silent mode for thinking feedback)
            if not silent and self.speaking_start_callback:
                try:
                    self.speaking_start_callback()
                except Exception as e:
                    logger.error(f"Error in speaking_start_callback: {e}")
            
            # P4: Send response text to companion speech bubble (skip if silent - thinking phrases don't show)
            if not silent and self.response_text_callback:
                try:
                    self.response_text_callback(text)
                except Exception as e:
                    logger.error(f"Error in response_text_callback: {e}")
            
            # Enable ducking if requested and music manager is available
            if ducking and hasattr(self, 'music_manager') and self.music_manager:
                self.music_manager.enable_ducking()
                logger.debug("🔉 Music ducking enabled for TTS")
            
            self._speak_with_kokoro(text, speed=speed)
            
            # Disable ducking after speech completes
            if ducking and hasattr(self, 'music_manager') and self.music_manager:
                self.music_manager.disable_ducking()
                logger.debug("🔊 Music ducking disabled after TTS")
            
            # Notify that speaking has ended (skip if silent mode)
            if not silent and self.speaking_end_callback:
                try:
                    self.speaking_end_callback()
                except Exception as e:
                    logger.error(f"Error in speaking_end_callback: {e}")
                
        except Exception as e:
            logger.error(f"❌ TTS error: {e}")
            # Restore music volume even on error
            if ducking and hasattr(self, 'music_manager') and self.music_manager:
                try:
                    self.music_manager.disable_ducking()
                except:
                    pass
            # Notify end even on error (skip if silent mode)
            if not silent and self.speaking_end_callback:
                try:
                    self.speaking_end_callback()
                except:
                    pass
            # Don't raise - just log the error to avoid breaking the app
    
    def _speak_with_kokoro(self, text, speed=1.0):
        """Generate and play speech with Kokoro TTS using streaming.
        
        For long text (multiple sentences), this uses streaming playback:
        - Generate first sentence and play immediately (~0.5s latency)
        - Generate remaining sentences in background while playing
        - Pre-buffer next sentence for minimal gaps (~50-100ms)
        
        For short text (single sentence), behaves like before.
        
        Args:
            text: Text to speak
            speed: Speech speed multiplier (0.5 = slower, 1.0 = normal, 1.5 = faster)
        """
        # Reset stop flag
        self._stop_event.clear()
        self._is_streaming = True
        self._current_sounds = []
        
        try:
            # Split text into sentences
            sentences = _split_sentences(text)
            
            if not sentences:
                logger.warning("⚠️ No sentences to speak")
                return
            
            total_sentences = len(sentences)
            logger.info(f"🎤 Streaming TTS: {total_sentences} sentence(s) with {self.voice_name} voice")
            overall_start = time.time()
            
            # For single sentence, use simple path (no threading overhead)
            if total_sentences == 1:
                self._generate_and_play_single(sentences[0], speed)
                return
            
            # === STREAMING MODE FOR MULTIPLE SENTENCES ===
            # Strategy: Generate S1 -> Play S1 while generating S2 -> Play S2 while generating S3...
            
            # Generate and play first sentence immediately
            first_audio = self._generate_audio(sentences[0], speed)
            if first_audio is None or self._stop_event.is_set():
                return
            
            first_gen_time = time.time() - overall_start
            logger.info(f"⚡ First sentence ready in {first_gen_time:.2f}s - starting playback")
            
            # Start playback thread for first sentence
            playback_queue = queue.Queue()
            playback_queue.put(first_audio)
            
            # Background thread to generate remaining sentences
            def generate_remaining():
                for i, sentence in enumerate(sentences[1:], start=2):
                    if self._stop_event.is_set():
                        break
                    audio = self._generate_audio(sentence, speed)
                    if audio is not None and not self._stop_event.is_set():
                        playback_queue.put(audio)
                        logger.debug(f"📦 Sentence {i}/{total_sentences} queued")
                # Signal end of generation
                playback_queue.put(None)
            
            gen_thread = threading.Thread(target=generate_remaining, daemon=True)
            gen_thread.start()
            
            # Play audio chunks sequentially
            sentence_num = 1
            while not self._stop_event.is_set():
                try:
                    audio_data = playback_queue.get(timeout=10.0)
                    if audio_data is None:  # End signal
                        break
                    
                    self._play_audio_chunk(audio_data, sentence_num, total_sentences)
                    sentence_num += 1
                    
                except queue.Empty:
                    logger.warning("⚠️ Audio queue timeout - generation may have stalled")
                    break
            
            # Wait for generator thread to finish
            gen_thread.join(timeout=2.0)
            
            total_time = time.time() - overall_start
            logger.info(f"✅ Streaming playback complete ({total_time:.2f}s total)")
            
        except Exception as e:
            logger.error(f"❌ Kokoro TTS error: {e}")
            raise
        finally:
            self._is_streaming = False
    
    def _generate_audio(self, sentence: str, speed: float):
        """Generate audio for a single sentence.
        
        Returns:
            numpy array of audio data, or None on error
        """
        try:
            audio_data, _ = self.kokoro.create(sentence, voice=self.voice_name, speed=speed)
            return audio_data
        except Exception as e:
            logger.error(f"❌ Failed to generate audio: {e}")
            return None
    
    def _generate_and_play_single(self, sentence: str, speed: float):
        """Generate and play a single sentence (simple path, no streaming)."""
        try:
            start_time = time.time()
            audio_data = self._generate_audio(sentence, speed)
            
            if audio_data is None:
                return
            
            gen_time = time.time() - start_time
            audio_duration = len(audio_data) / self.sample_rate
            logger.info(f"✅ Speech generated in {gen_time:.2f}s ({audio_duration:.2f}s audio)")
            
            self._play_audio_chunk(audio_data, 1, 1)
            
        except Exception as e:
            logger.error(f"❌ Single sentence TTS error: {e}")
    
    def _play_audio_chunk(self, audio_data, chunk_num: int, total_chunks: int):
        """Play an audio chunk and wait for completion."""
        if self._stop_event.is_set():
            return
        
        try:
            # Create temp file for this chunk
            temp_path = Path(tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name)
            sf.write(str(temp_path), audio_data, self.sample_rate)
            
            if not temp_path.exists():
                logger.error("❌ Temp audio file not found!")
                return
            
            # Load and play at full volume
            sound = pygame.mixer.Sound(str(temp_path))
            sound.set_volume(1.0)  # Ensure TTS is at maximum volume
            self._current_sounds.append(sound)
            
            with self._playback_lock:
                self.current_channel = sound.play()
                if self.current_channel:
                    self.current_channel.set_volume(1.0)  # Max channel volume for clarity over music
            
            logger.debug(f"▶️ Playing chunk {chunk_num}/{total_chunks}")
            
            # Wait for playback to complete (check stop flag frequently)
            while self.current_channel and self.current_channel.get_busy():
                if self._stop_event.is_set():
                    self.current_channel.stop()
                    break
                time.sleep(0.05)  # 50ms polling for responsive stop
            
            # Cleanup temp file
            try:
                temp_path.unlink()
            except:
                pass
                
        except Exception as e:
            logger.error(f"❌ Playback error: {e}")
    
    def is_speaking(self):
        """Check if TTS is currently speaking (including streaming playback)."""
        try:
            # Check both streaming state and channel state
            if self._is_streaming:
                return True
            return pygame.mixer.get_init() and self.current_channel and self.current_channel.get_busy()
        except Exception:
            return False
    
    def stop(self):
        """Stop current speech playback (including streaming)."""
        try:
            # Signal streaming thread to stop
            self._stop_event.set()
            
            # Stop current channel
            with self._playback_lock:
                if pygame.mixer.get_init() and self.current_channel and self.current_channel.get_busy():
                    self.current_channel.stop()
            
            # Stop all queued sounds
            for sound in self._current_sounds:
                try:
                    sound.stop()
                except:
                    pass
            self._current_sounds = []
            
            # Clear streaming state
            self._is_streaming = False
            
            logger.info("🛑 Speech playback stopped")
        except Exception as e:
            logger.debug(f"Stop playback: {e}")
    
    def cleanup(self):
        """Unload Kokoro model and free memory."""
        import gc
        
        # Stop any ongoing playback
        self.stop()
        
        # Unload Kokoro model
        if self.kokoro is not None:
            try:
                logger.info("🧹 Unloading Kokoro TTS model...")
                del self.kokoro
                self.kokoro = None
            except Exception as e:
                logger.debug(f"Error unloading Kokoro: {e}")
        
        # Quit pygame mixer (only if initialized)
        try:
            if pygame.mixer.get_init():
                pygame.mixer.quit()
                logger.info("✅ Pygame mixer closed")
        except Exception as e:
            logger.debug(f"Error closing pygame mixer: {e}")
        
        # Force garbage collection
        gc.collect()
        logger.info("✅ TTS resources freed")
