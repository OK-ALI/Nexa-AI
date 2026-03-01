"""
Coqui XTTS Engine for Nexa - Uses cloned af_heart voice

This engine uses Coqui XTTS v2 with a reference audio sample to clone
the af_heart voice from Kokoro, providing an alternative TTS option with
potentially better emotional range.

Requirements:
- coqui-tts package (install with: uv pip install coqui-tts)
- Reference audio file: voice/af_heart_reference.wav
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
import soundfile as sf
import numpy as np

logger = logging.getLogger(__name__)

# Lazy imports
_tts_model = None
_device = None

# Sentence splitting pattern
SENTENCE_PATTERN = re.compile(r'(?<=[.!?])\s+')


def _lazy_import_tts():
    """Lazy import of Coqui TTS to avoid loading at startup."""
    global _tts_model, _device
    
    if _tts_model is None:
        import torch
        from TTS.api import TTS
        
        _device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"🎤 Loading Coqui XTTS model on {_device}...")
        
        start = time.time()
        _tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(_device)
        logger.info(f"✅ Coqui XTTS loaded in {time.time() - start:.1f}s")
    
    return _tts_model, _device


def _split_sentences(text: str) -> list:
    """Split text into sentences for streaming TTS."""
    clean_text = text.replace('\n', ' ').replace('\r', ' ').strip()
    clean_text = ' '.join(clean_text.split())
    
    if not clean_text:
        return []
    
    sentences = SENTENCE_PATTERN.split(clean_text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        sentences = [clean_text]
    
    return sentences


class CoquiTTSEngine:
    """
    Coqui XTTS Engine with cloned af_heart voice.
    
    Uses voice cloning to replicate the af_heart voice from Kokoro,
    providing an alternative TTS with potentially better prosody control.
    """
    
    def __init__(self, config):
        """Initialize Coqui TTS engine."""
        self.config = config
        self.tts = None
        self.device = None
        self.sample_rate = 24000  # XTTS output rate
        self.current_channel = None
        
        # Reference audio for voice cloning
        self.reference_audio = config.voice_dir / "af_heart_reference.wav"
        
        # State callbacks (same interface as KokoroTTS)
        self.speaking_start_callback = None
        self.speaking_end_callback = None
        self.response_text_callback = None
        
        # Streaming infrastructure
        self._audio_queue = queue.Queue()
        self._stop_event = threading.Event()
        self._playback_lock = threading.Lock()
        self._is_streaming = False
        self._current_sounds = []
        
        # Setup pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init(channels=8)
            logger.info("🔊 Pygame mixer initialized")
        
        # Lazy load - don't load XTTS at init (it's heavy ~1.8GB)
        # Will load on first speak() call
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy initialization of XTTS model."""
        if self._initialized:
            return True
        
        try:
            # Check reference audio exists
            if not self.reference_audio.exists():
                logger.error(f"❌ Reference audio not found: {self.reference_audio}")
                logger.info("💡 Run test_coqui_clone.py to generate reference audio")
                return False
            
            # Load model
            self.tts, self.device = _lazy_import_tts()
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Coqui TTS: {e}")
            return False
    
    def speak(self, text, wait=True, ducking=False, blocking=True, silent=False, speed=1.0):
        """
        Generate and play speech using Coqui XTTS with cloned voice.
        
        Args:
            text: Text to speak
            wait: Whether to wait for playback (deprecated)
            ducking: Whether to duck background music
            blocking: Whether to block until speech completes
            silent: If True, skip state callbacks
            speed: Speech speed (note: XTTS has limited speed control)
        """
        if not text or not text.strip():
            logger.warning("⚠️ Empty text provided to TTS")
            return
        
        # Lazy init
        if not self._ensure_initialized():
            logger.error("❌ Coqui TTS not initialized, cannot speak")
            return
        
        try:
            # Stop any current speech
            if self.is_speaking():
                self.stop()
            
            # Notify speaking start
            if not silent and self.speaking_start_callback:
                try:
                    self.speaking_start_callback()
                except Exception as e:
                    logger.error(f"Error in speaking_start_callback: {e}")
            
            # Send text to pet speech bubble
            if not silent and self.response_text_callback:
                try:
                    self.response_text_callback(text)
                except Exception as e:
                    logger.error(f"Error in response_text_callback: {e}")
            
            # Enable ducking
            if ducking and hasattr(self, 'music_manager') and self.music_manager:
                self.music_manager.enable_ducking()
            
            # Generate and play
            self._speak_with_xtts(text)
            
            # Disable ducking
            if ducking and hasattr(self, 'music_manager') and self.music_manager:
                self.music_manager.disable_ducking()
            
            # Notify speaking end
            if not silent and self.speaking_end_callback:
                try:
                    self.speaking_end_callback()
                except Exception as e:
                    logger.error(f"Error in speaking_end_callback: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Coqui TTS error: {e}")
            if ducking and hasattr(self, 'music_manager') and self.music_manager:
                try:
                    self.music_manager.disable_ducking()
                except:
                    pass
            if not silent and self.speaking_end_callback:
                try:
                    self.speaking_end_callback()
                except:
                    pass
    
    def _speak_with_xtts(self, text):
        """Generate and play speech with XTTS using streaming."""
        self._stop_event.clear()
        self._is_streaming = True
        self._current_sounds = []
        
        try:
            sentences = _split_sentences(text)
            
            if not sentences:
                return
            
            total = len(sentences)
            logger.info(f"🎤 Coqui XTTS: {total} sentence(s) with cloned af_heart voice")
            start = time.time()
            
            # Simple mode for single sentence
            if total == 1:
                self._generate_and_play_single(sentences[0])
                return
            
            # Streaming mode
            first_audio = self._generate_audio(sentences[0])
            if first_audio is None or self._stop_event.is_set():
                return
            
            logger.info(f"⚡ First sentence ready in {time.time() - start:.2f}s")
            
            playback_queue = queue.Queue()
            playback_queue.put(first_audio)
            
            def generate_remaining():
                for i, sentence in enumerate(sentences[1:], start=2):
                    if self._stop_event.is_set():
                        break
                    audio = self._generate_audio(sentence)
                    if audio is not None and not self._stop_event.is_set():
                        playback_queue.put(audio)
                playback_queue.put(None)
            
            gen_thread = threading.Thread(target=generate_remaining, daemon=True)
            gen_thread.start()
            
            chunk_num = 1
            while not self._stop_event.is_set():
                try:
                    audio = playback_queue.get(timeout=30.0)
                    if audio is None:
                        break
                    self._play_audio_chunk(audio, chunk_num, total)
                    chunk_num += 1
                except queue.Empty:
                    break
            
            gen_thread.join(timeout=2.0)
            logger.info(f"✅ XTTS playback complete ({time.time() - start:.2f}s)")
            
        finally:
            self._is_streaming = False
    
    def _generate_audio(self, sentence: str) -> np.ndarray:
        """Generate audio for a single sentence using XTTS."""
        try:
            # XTTS generates directly to numpy array
            wav = self.tts.tts(
                text=sentence,
                speaker_wav=str(self.reference_audio),
                language="en"
            )
            return np.array(wav, dtype=np.float32)
        except Exception as e:
            logger.error(f"❌ XTTS generation failed: {e}")
            return None
    
    def _generate_and_play_single(self, sentence: str):
        """Generate and play single sentence."""
        try:
            start = time.time()
            audio = self._generate_audio(sentence)
            
            if audio is None:
                return
            
            gen_time = time.time() - start
            duration = len(audio) / self.sample_rate
            logger.info(f"✅ Generated in {gen_time:.2f}s ({duration:.2f}s audio)")
            
            self._play_audio_chunk(audio, 1, 1)
            
        except Exception as e:
            logger.error(f"❌ Single sentence error: {e}")
    
    def _play_audio_chunk(self, audio_data: np.ndarray, chunk_num: int, total: int):
        """Play audio chunk."""
        if self._stop_event.is_set():
            return
        
        try:
            # Save to temp file
            temp_path = Path(tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name)
            sf.write(str(temp_path), audio_data, self.sample_rate)
            
            # Load and play
            sound = pygame.mixer.Sound(str(temp_path))
            self._current_sounds.append(sound)
            
            with self._playback_lock:
                self.current_channel = sound.play()
            
            logger.debug(f"▶️ Playing chunk {chunk_num}/{total}")
            
            # Wait for completion
            while self.current_channel and self.current_channel.get_busy():
                if self._stop_event.is_set():
                    self.current_channel.stop()
                    break
                time.sleep(0.05)
            
            # Cleanup
            try:
                temp_path.unlink()
            except:
                pass
                
        except Exception as e:
            logger.error(f"❌ Playback error: {e}")
    
    def is_speaking(self) -> bool:
        """Check if TTS is currently speaking."""
        try:
            if self._is_streaming:
                return True
            return pygame.mixer.get_init() and self.current_channel and self.current_channel.get_busy()
        except:
            return False
    
    def stop(self):
        """Stop current playback."""
        try:
            self._stop_event.set()
            
            with self._playback_lock:
                if pygame.mixer.get_init() and self.current_channel and self.current_channel.get_busy():
                    self.current_channel.stop()
            
            for sound in self._current_sounds:
                try:
                    sound.stop()
                except:
                    pass
            self._current_sounds = []
            self._is_streaming = False
            
            logger.info("🛑 Coqui TTS stopped")
        except Exception as e:
            logger.debug(f"Stop error: {e}")
    
    def cleanup(self):
        """Free resources."""
        global _tts_model
        import gc
        
        self.stop()
        
        if _tts_model is not None:
            logger.info("🧹 Unloading Coqui XTTS model...")
            del _tts_model
            _tts_model = None
            self.tts = None
        
        try:
            if pygame.mixer.get_init():
                pygame.mixer.quit()
        except:
            pass
        
        gc.collect()
        logger.info("✅ Coqui TTS resources freed")
