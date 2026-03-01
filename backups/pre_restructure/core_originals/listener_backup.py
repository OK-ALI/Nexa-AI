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
                print(f"✓ Added cuDNN to PATH: {cudnn_path}")
        else:
            print(f"⚠ cuDNN bin directory not found: {cudnn_bin}")
        
        # Add cuBLAS bin directory
        cublas_bin = site_packages / 'nvidia' / 'cublas' / 'bin'
        if cublas_bin.exists():
            cublas_path = str(cublas_bin.absolute())
            if cublas_path not in os.environ.get('PATH', ''):
                os.environ['PATH'] = cublas_path + os.pathsep + os.environ.get('PATH', '')
                print(f"✓ Added cuBLAS to PATH: {cublas_path}")
        else:
            print(f"⚠ cuBLAS bin directory not found: {cublas_bin}")
            
    except Exception as e:
        print(f"⚠ Failed to add CUDA libraries to PATH: {e}")

_add_cudnn_to_path()

try:
    import pyaudio
except ImportError:
    pyaudio = None

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None
    
logger = logging.getLogger(__name__)


class AudioListener:
    """
    Manages audio capture from microphone and transcription via faster-whisper.
    Runs in a separate thread to avoid blocking the main application.
    Uses GPU acceleration for fast transcription.
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
    
    def set_transcription_callback(self, callback: Callable[[str], None]):
        """
        Set callback function for transcription results.
        
        Args:
            callback: Function to call with transcribed text
        """
        self.transcription_callback = callback
    
    def start_listening(self):
        """Start listening for audio input."""
        if not self.audio:
            logger.error("Cannot start listening - PyAudio not initialized")
            return
        
        if self.is_listening:
            logger.warning("Already listening")
            return
        
        logger.info("🎤 STARTING AUDIO LISTENER...")
        self.is_listening = True
        
        # Start recording thread
        self.recording_thread = threading.Thread(
            target=self._recording_loop,
            name="AudioListenerThread",
            daemon=True
        )
        self.recording_thread.start()
        logger.info("✅ Audio listener thread started - just speak your command!")
    
    def pause_listening(self):
        """Temporarily pause listening (e.g., during TTS playback)."""
        self.is_speaking = True
        logger.debug("🔇 Listening paused (TTS speaking)")
    
    def resume_listening(self):
        """Resume listening after pause."""
        self.is_speaking = False
        logger.debug("🔊 Listening resumed")
    
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
            self.stream.stop_stream()
            self.stream.close()
        
        if self.audio:
            self.audio.terminate()
        
        logger.info("Audio listener stopped")
    
    def _recording_loop(self):
        """Main recording loop - captures audio and transcribes it."""
        try:
            # Open audio stream
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            logger.info("🎙️ Audio stream opened successfully - listening for speech...")
            
            frames = []
            silence_threshold = 1500  # Higher = less sensitive (ignores distant/quiet sounds) - INCREASED from 1200
            speech_threshold = 2000   # Minimum level to start detecting speech - INCREASED from 1500
            silence_duration = 0
            max_silence = 1.5  # seconds of silence to trigger transcription
            min_speech_duration = 1.0  # minimum speech duration (seconds) to process - INCREASED from 0.5
            max_recording_duration = 15.0  # Maximum recording time in seconds (prevent endless captures) - INCREASED from 10.0
            is_speaking = False
            speech_start_time = 0
            
            while self.is_listening:
                try:
                    # Skip recording if TTS is speaking (avoid feedback loop)
                    if self.is_speaking:
                        # Discard any accumulated frames during TTS
                        if frames:
                            frames = []
                            is_speaking = False
                            silence_duration = 0
                        continue
                    
                    # Read audio chunk
                    data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                    frames.append(data)
                    
                    # Simple voice activity detection
                    audio_level = self._get_audio_level(data)
                    
                    # Check if recording is too long (prevent endless captures)
                    current_recording_duration = len(frames) * self.chunk_size / self.sample_rate
                    if current_recording_duration >= max_recording_duration and is_speaking:
                        logger.warning(f"⏱️ Max recording duration reached ({max_recording_duration}s) - forcing transcription")
                        speech_duration = len(frames) * self.chunk_size / self.sample_rate
                        logger.info(f"🗣️ Speech ended - transcribing {len(frames)} frames ({speech_duration:.2f}s)...")
                        self._transcribe_audio(frames)
                        is_speaking = False
                        frames = []
                        silence_duration = 0
                        continue
                    
                    if audio_level < silence_threshold:
                        silence_duration += self.chunk_size / self.sample_rate
                        
                        # If enough silence and we have meaningful speech, transcribe
                        if silence_duration >= max_silence and is_speaking:
                            speech_duration = len(frames) * self.chunk_size / self.sample_rate
                            if speech_duration >= min_speech_duration:
                                logger.info(f"🗣️ Speech ended - transcribing {len(frames)} frames ({speech_duration:.2f}s)...")
                                self._transcribe_audio(frames)
                            is_speaking = False
                            frames = []
                            silence_duration = 0
                    elif audio_level >= speech_threshold:
                        # High enough audio level to be considered speech
                        silence_duration = 0
                        if not is_speaking:
                            logger.info(f"🎤 Speech detected! Audio level: {audio_level}")
                            is_speaking = True
                            speech_start_time = len(frames) * self.chunk_size / self.sample_rate
                    elif is_speaking:
                        # Continue recording if already speaking (medium audio level)
                        silence_duration = 0
                
                except Exception as e:
                    logger.error(f"Error reading audio: {e}")
                    break
            
        except Exception as e:
            logger.error(f"Error in recording loop: {e}", exc_info=True)
        finally:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
    
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
                
                logger.info(f"💾 Saved audio to: {temp_path} ({temp_path.stat().st_size} bytes)")
                
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
                        # Not paused, send normally
                        self.transcription_callback(transcription)
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
            logger.info(f"🎯 Starting GPU-accelerated Whisper transcription...")
            
            # Transcribe with faster-whisper (uses GPU!)
            segments, info = self.whisper_model.transcribe(
                str(audio_file),
                language="en",
                beam_size=5,
                vad_filter=False  # Disabled VAD due to onnxruntime DLL issues on Windows
            )
            
            # Extract transcription text
            transcription = " ".join([segment.text for segment in segments]).strip()
            
            # Remove duplicate phrases (happens when user holds mic too long)
            transcription = self._remove_duplicate_phrases(transcription)
            
            if transcription:
                logger.info(f"✅ Whisper transcription: '{transcription}'")
                logger.info(f"   Detected language: {info.language} (probability: {info.language_probability:.2f})")
                return transcription
            else:
                logger.debug("No speech detected in audio")
                return None
        
        except Exception as e:
            logger.error(f"Error running Whisper: {e}", exc_info=True)
            return None
    
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

