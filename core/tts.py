"""
TTS Engine using Kokoro TTS (Local, 82M parameters, Apache-2.0 license)
Voice: af_heart (American Female, warm and natural)
Uses subprocess isolation to avoid DLL conflicts with PyTorch CUDA
"""

import os
import sys
import time
import logging
import tempfile
from pathlib import Path
import pygame
import urllib.request
import soundfile as sf
import subprocess

logger = logging.getLogger(__name__)

# Lazy imports to avoid DLL loading issues at startup
Kokoro = None
SAMPLE_RATE = 24000  # Default, will be updated when Kokoro loads


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


class TTSEngine:
    """Kokoro TTS Engine with af_heart voice."""
    
    def __init__(self, config):
        """Initialize Kokoro TTS engine."""
        self.config = config
        self.kokoro = None
        self.voice_name = "af_heart"  # American Female, warm heart
        self.sample_rate = SAMPLE_RATE  # 24000 Hz
        self.current_channel = None  # Track active sound channel
        
        # State callbacks (for notifying brain when speaking starts/stops)
        self.speaking_start_callback = None
        self.speaking_end_callback = None
        
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
    
    def speak(self, text, wait=True, ducking=False, blocking=True):
        """
        Generate and play speech using Kokoro TTS.
        
        Args:
            text: Text to speak
            wait: Whether to wait for playback to finish (deprecated, use blocking)
            ducking: Whether to duck background music during speech
            blocking: Whether to block until speech completes (same as wait)
        """
        if not text or not text.strip():
            logger.warning("⚠️ Empty text provided to TTS")
            return
        
        try:
            # Notify that speaking is starting
            if self.speaking_start_callback:
                try:
                    self.speaking_start_callback()
                except Exception as e:
                    logger.error(f"Error in speaking_start_callback: {e}")
            
            # Enable ducking if requested and music manager is available
            if ducking and hasattr(self, 'music_manager') and self.music_manager:
                self.music_manager.enable_ducking()
                logger.debug("🔉 Music ducking enabled for TTS")
            
            self._speak_with_kokoro(text)
            
            # Disable ducking after speech completes
            if ducking and hasattr(self, 'music_manager') and self.music_manager:
                self.music_manager.disable_ducking()
                logger.debug("🔊 Music ducking disabled after TTS")
            
            # Notify that speaking has ended
            if self.speaking_end_callback:
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
            # Notify end even on error
            if self.speaking_end_callback:
                try:
                    self.speaking_end_callback()
                except:
                    pass
            # Don't raise - just log the error to avoid breaking the app
    
    def _speak_with_kokoro(self, text):
        """Generate and play speech with Kokoro TTS (in-memory, fast)."""
        try:
            # Create temporary file for audio
            temp_path = Path(tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name)
            
            logger.info(f"🎤 Generating speech with {self.voice_name} voice...")
            start_time = time.time()
            
            # CRITICAL FIX: Clean text to avoid Kokoro line mismatch errors
            # Kokoro expects single-line input, but refined text may contain \n
            clean_text = text.replace('\n', ' ').replace('\r', ' ').strip()
            # Remove multiple spaces
            clean_text = ' '.join(clean_text.split())
            
            # Generate speech directly in memory (MUCH FASTER)
            audio_data, _ = self.kokoro.create(clean_text, voice=self.voice_name, speed=1.0)
            
            # Save to file
            sf.write(str(temp_path), audio_data, self.sample_rate)
            
            gen_time = time.time() - start_time
            audio_duration = len(audio_data) / self.sample_rate
            logger.info(f"✅ Speech generated in {gen_time:.2f}s ({audio_duration:.2f}s audio)")
            
            # Play audio with pygame using Sound (not music channel)
            # This allows music to continue playing on the music channel
            if temp_path.exists():
                file_size = temp_path.stat().st_size / 1024
                logger.info(f"▶️ Playing audio ({file_size:.1f} KB)...")
                
                # Load as Sound object (uses its own channel)
                sound = pygame.mixer.Sound(str(temp_path))
                self.current_channel = sound.play()
                
                # Wait for playback to complete
                while self.current_channel and self.current_channel.get_busy():
                    time.sleep(0.1)
                
                logger.info("✅ Playback complete")
                temp_path.unlink()
                
                logger.info("✅ Playback complete")
            else:
                logger.error("❌ Temp audio file not found!")
                
        except Exception as e:
            logger.error(f"❌ Kokoro TTS error: {e}")
            raise
    
    def is_speaking(self):
        """Check if TTS is currently speaking."""
        return self.current_channel and self.current_channel.get_busy()
    
    def stop(self):
        """Stop current speech playback."""
        if self.current_channel and self.current_channel.get_busy():
            self.current_channel.stop()
            logger.info("🛑 Speech playback stopped")
    
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
        
        # Quit pygame mixer
        try:
            pygame.mixer.quit()
            logger.info("✅ Pygame mixer closed")
        except Exception as e:
            logger.debug(f"Error closing pygame mixer: {e}")
        
        # Force garbage collection
        gc.collect()
        logger.info("✅ TTS resources freed")
