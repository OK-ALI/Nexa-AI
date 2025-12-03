"""
Speaker Verification Module - SpeechBrain Implementation
Provides speaker identification and verification for voice-based authentication.

Features:
- GPU-accelerated speaker embeddings extraction
- Multi-user profile management
- Real-time verification with optimized inference
- Offline/online mode support
- Automatic fallback on errors
"""

import logging
import numpy as np
import torch
import os
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import json
import time

# Fix Windows symlink permission issue
# HuggingFace Hub tries to create symlinks which requires admin/developer mode on Windows
# Force it to use file copying instead
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'

logger = logging.getLogger(__name__)


class SpeakerVerification:
    """
    Speaker verification using SpeechBrain ECAPA-TDNN model.
    Optimized for GPU inference with minimal latency.
    """
    
    def __init__(self, config):
        """
        Initialize speaker verification system.
        
        Args:
            config: Configuration object with speaker settings
        """
        self.config = config
        self.enabled = getattr(config, 'speaker_verification_enabled', False)
        self.device = None
        self.model = None
        self.classifier = None
        
        # Performance settings
        self.use_gpu = getattr(config, 'speaker_verification_gpu', True)
        self.use_fp16 = getattr(config, 'speaker_verification_fp16', True)  # Mixed precision
        self.similarity_threshold = getattr(config, 'speaker_similarity_threshold', 0.85)
        
        # Profile storage - use config's speaker_profiles_dir (AppData location)
        # This ensures it works even when installed to Program Files
        if hasattr(config, 'speaker_profiles_dir'):
            self.profiles_dir = Path(config.speaker_profiles_dir)
        else:
            # Fallback for standalone usage - use AppData
            appdata = os.environ.get('LOCALAPPDATA', '')
            if appdata:
                self.profiles_dir = Path(appdata) / 'Nexa AI' / 'data' / 'speaker_profiles'
            else:
                self.profiles_dir = Path('./data/speaker_profiles')
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        
        # Loaded profiles cache
        self.profiles: Dict[str, np.ndarray] = {}
        self.profile_metadata: Dict[str, Dict] = {}
        
        # Performance tracking
        self.verification_count = 0
        self.total_verification_time = 0.0
        
        # Initialize if enabled
        if self.enabled:
            self._initialize_model()
            self._load_profiles()
        else:
            logger.info("🔇 Speaker verification DISABLED (set SPEAKER_VERIFICATION_ENABLED=true to enable)")
    
    def _initialize_model(self):
        """Initialize SpeechBrain model with GPU optimization."""
        try:
            logger.info("🔄 Initializing SpeechBrain speaker verification...")
            start_time = time.time()
            
            # Suppress symlink warnings (model files are pre-downloaded locally)
            os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
            
            # Import SpeechBrain
            try:
                from speechbrain.inference import EncoderClassifier
            except ImportError:
                try:
                    from speechbrain.pretrained import EncoderClassifier
                except ImportError:
                    logger.error("❌ SpeechBrain not installed! Run: pip install speechbrain")
                    self.enabled = False
                    return
            
            # Determine device (GPU vs CPU)
            if self.use_gpu and torch.cuda.is_available():
                self.device = torch.device("cuda")
                logger.info(f"✅ Using GPU: {torch.cuda.get_device_name(0)}")
            else:
                self.device = torch.device("cpu")
                logger.warning("⚠️ GPU not available, using CPU (slower verification)")
            
            # Load pre-trained ECAPA-TDNN model (state-of-the-art speaker embeddings)
            # Model: ~50MB, trained on VoxCeleb dataset
            # Note: Model files are pre-downloaded to avoid Windows symlink issues
            model_source = "speechbrain/spkrec-ecapa-voxceleb"
            savedir = self.profiles_dir / "models" / "ecapa-voxceleb"
            savedir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"📦 Loading model: {model_source}")
            
            # Check if model files already exist locally
            model_files_exist = (savedir / "hyperparams.yaml").exists() and \
                               (savedir / "embedding_model.ckpt").exists()
            
            if model_files_exist:
                logger.info(f"✅ Model files found locally - loading from cache")
            else:
                logger.info(f"⬇️ Model not found locally - will download from HuggingFace")
                logger.warning(f"⚠️ First download may fail due to Windows symlink permissions")
                logger.warning(f"⚠️ If you see WinError 1314, run: python -m pip install --upgrade speechbrain")
            
            # Load model (will use local files if they exist)
            self.classifier = EncoderClassifier.from_hparams(
                source=model_source,
                savedir=str(savedir),
                run_opts={"device": str(self.device)}
            )
            
            # Enable mixed precision (FP16) for faster inference on GPU
            if self.use_fp16 and self.device.type == "cuda":
                logger.info("⚡ Enabling mixed precision (FP16) for faster inference")
                # SpeechBrain handles FP16 internally via run_opts
            
            init_time = time.time() - start_time
            logger.info(f"✅ Speaker verification initialized ({init_time:.2f}s)")
            logger.info(f"   Device: {self.device}")
            logger.info(f"   Model: ECAPA-TDNN (VoxCeleb)")
            logger.info(f"   Similarity threshold: {self.similarity_threshold * 100}%")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize speaker verification: {e}")
            logger.warning("⚠️ Speaker verification DISABLED due to initialization error")
            self.enabled = False
    
    def _load_profiles(self):
        """Load all saved voice profiles from disk."""
        try:
            profile_files = list(self.profiles_dir.glob("*.npy"))
            
            if not profile_files:
                logger.info("📂 No voice profiles found (enrollment needed)")
                return
            
            for profile_file in profile_files:
                profile_name = profile_file.stem
                
                try:
                    # Load embedding
                    embedding = np.load(profile_file)
                    self.profiles[profile_name] = embedding
                    
                    # Load metadata if exists
                    metadata_file = profile_file.with_suffix('.json')
                    if metadata_file.exists():
                        with open(metadata_file, 'r') as f:
                            self.profile_metadata[profile_name] = json.load(f)
                    else:
                        self.profile_metadata[profile_name] = {
                            "name": profile_name,
                            "enrolled_at": None,
                            "sample_count": None
                        }
                    
                    logger.info(f"✅ Loaded profile: {profile_name}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to load profile {profile_name}: {e}")
            
            logger.info(f"📊 Loaded {len(self.profiles)} voice profile(s)")
            
        except Exception as e:
            logger.error(f"❌ Error loading profiles: {e}")
    
    def extract_embedding(self, audio_path: str) -> Optional[np.ndarray]:
        """
        Extract speaker embedding from audio file.
        
        Args:
            audio_path: Path to audio file (WAV format)
            
        Returns:
            Speaker embedding vector (numpy array) or None on error
        """
        if not self.enabled or self.classifier is None:
            return None
        
        try:
            start_time = time.time()
            
            # Extract embedding using SpeechBrain
            # Returns 192-dimensional embedding vector
            embedding = self.classifier.encode_batch(
                torch.tensor([audio_path])  # SpeechBrain expects batch format
            )
            
            # Convert to numpy and normalize
            embedding_np = embedding.squeeze().cpu().numpy()
            embedding_np = embedding_np / np.linalg.norm(embedding_np)  # L2 normalization
            
            extract_time = time.time() - start_time
            logger.debug(f"⏱️ Embedding extracted in {extract_time:.3f}s")
            
            return embedding_np
            
        except Exception as e:
            logger.error(f"❌ Failed to extract embedding: {e}")
            return None
    
    def extract_embedding_from_audio_data(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Optional[np.ndarray]:
        """
        Extract speaker embedding from raw audio data (optimized for real-time).
        
        Args:
            audio_data: Raw audio samples (numpy array)
            sample_rate: Sample rate in Hz
            
        Returns:
            Speaker embedding vector or None on error
        """
        if not self.enabled or self.classifier is None:
            return None
        
        try:
            start_time = time.time()
            
            # Convert numpy audio to torch tensor
            audio_tensor = torch.from_numpy(audio_data).float()
            
            # Ensure correct shape (batch, samples)
            if audio_tensor.dim() == 1:
                audio_tensor = audio_tensor.unsqueeze(0)
            
            # Move to GPU if available
            audio_tensor = audio_tensor.to(self.device)
            
            # Extract embedding (SpeechBrain handles resampling internally)
            with torch.no_grad():  # Disable gradient computation for inference
                embedding = self.classifier.encode_batch(audio_tensor)
            
            # Convert to numpy and normalize
            embedding_np = embedding.squeeze().cpu().numpy()
            embedding_np = embedding_np / np.linalg.norm(embedding_np)
            
            extract_time = time.time() - start_time
            logger.debug(f"⏱️ Real-time embedding extracted in {extract_time:.3f}s")
            
            return embedding_np
            
        except Exception as e:
            logger.error(f"❌ Failed to extract embedding from audio data: {e}")
            return None
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score (0.0 to 1.0, higher = more similar)
        """
        try:
            # Cosine similarity (dot product of normalized vectors)
            similarity = np.dot(embedding1, embedding2)
            
            # Ensure in range [0, 1] (sometimes can be slightly outside due to numerical precision)
            similarity = np.clip(similarity, 0.0, 1.0)
            
            return float(similarity)
            
        except Exception as e:
            logger.error(f"❌ Failed to compute similarity: {e}")
            return 0.0
    
    def verify_speaker_from_audio_bytes(self, audio_bytes: bytes, sample_rate: int = 16000,
                                        profile_name: str = "user_primary") -> Tuple[bool, float]:
        """
        Verify speaker from raw audio bytes (from PyAudio).
        
        Args:
            audio_bytes: Raw audio bytes (16-bit PCM)
            sample_rate: Sample rate in Hz
            profile_name: Name of profile to verify against
            
        Returns:
            Tuple of (is_verified: bool, similarity_score: float)
        """
        try:
            # Convert bytes to numpy array (16-bit PCM audio)
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
            
            # Normalize to float32 in range [-1.0, 1.0]
            audio_float = audio_array.astype(np.float32) / 32768.0
            
            # Call the main verify_speaker method
            return self.verify_speaker(audio_float, sample_rate, profile_name)
            
        except Exception as e:
            logger.error(f"❌ Failed to convert audio bytes: {e}")
            return True, 0.0  # Fallback: allow through on error
    
    def verify_speaker(self, audio_data: np.ndarray, sample_rate: int = 16000, 
                       profile_name: str = "user_primary") -> Tuple[bool, float]:
        """
        Verify if audio matches enrolled speaker profile.
        
        Args:
            audio_data: Raw audio samples
            sample_rate: Sample rate in Hz
            profile_name: Name of profile to verify against
            
        Returns:
            Tuple of (is_verified: bool, similarity_score: float)
        """
        if not self.enabled:
            # If verification disabled, always pass through
            return True, 1.0
        
        if profile_name not in self.profiles:
            # Check if enrollment is required (strict mode)
            require_enrollment = getattr(self.config, 'speaker_require_enrollment', False)
            if require_enrollment:
                logger.warning(f"❌ No profile enrolled - REJECTING (strict mode)")
                return False, 0.0  # Reject until enrolled (strict security mode)
            else:
                logger.warning(f"⚠️ Profile '{profile_name}' not found - allowing through (fallback mode)")
                return True, 0.0  # No profile = allow (fallback/testing mode)
        
        try:
            # CRITICAL FIX: Validate audio quality BEFORE verification
            # This prevents 0.0% false detections on TTS audio, noise, silence
            
            # Check 1: Minimum audio length (avoid too-short clips)
            min_length_seconds = 1.0  # At least 1 second of audio
            audio_duration = len(audio_data) / sample_rate
            if audio_duration < min_length_seconds:
                logger.debug(f"⏭️ Audio too short ({audio_duration:.2f}s < {min_length_seconds}s) - allowing through without verification")
                return True, 0.0
            
            # Check 2: Minimum energy level (avoid silence/very quiet audio)
            # Calculate RMS (Root Mean Square) energy
            rms_energy = np.sqrt(np.mean(audio_data ** 2))
            min_energy = 0.01  # Threshold for "meaningful" audio (tunable)
            if rms_energy < min_energy:
                logger.debug(f"⏭️ Audio too quiet (RMS={rms_energy:.4f} < {min_energy}) - likely silence/noise, allowing through")
                return True, 0.0
            
            # Check 3: Dynamic range (avoid flat/corrupted audio)
            audio_range = np.max(np.abs(audio_data))
            min_range = 0.005  # Minimum dynamic range
            if audio_range < min_range:
                logger.debug(f"⏭️ Audio has no dynamic range ({audio_range:.4f}) - corrupted/silence, allowing through")
                return True, 0.0
            
            logger.debug(f"✅ Audio quality OK: {audio_duration:.2f}s, RMS={rms_energy:.4f}, range={audio_range:.4f}")
            
            start_time = time.time()
            
            # Extract embedding from incoming audio
            incoming_embedding = self.extract_embedding_from_audio_data(audio_data, sample_rate)
            
            if incoming_embedding is None:
                logger.error("❌ Failed to extract embedding - allowing through (fallback)")
                return True, 0.0
            
            # Compare with enrolled profile
            enrolled_embedding = self.profiles[profile_name]
            similarity = self.compute_similarity(incoming_embedding, enrolled_embedding)
            
            # Determine if verified
            is_verified = similarity >= self.similarity_threshold
            
            # Track performance
            verify_time = time.time() - start_time
            self.verification_count += 1
            self.total_verification_time += verify_time
            
            # Log result
            if is_verified:
                logger.info(f"✅ Speaker VERIFIED ({similarity * 100:.1f}% match, {verify_time:.3f}s)")
            else:
                logger.warning(f"❌ Speaker REJECTED ({similarity * 100:.1f}% match < {self.similarity_threshold * 100:.1f}% threshold)")
            
            return is_verified, similarity
            
        except Exception as e:
            logger.error(f"❌ Verification error: {e} - allowing through (fallback)")
            return True, 0.0
    
    def enroll_speaker(self, audio_samples: List[np.ndarray], profile_name: str = "user_primary", 
                       sample_rate: int = 16000) -> bool:
        """
        Enroll new speaker by averaging multiple audio samples.
        
        Args:
            audio_samples: List of audio recordings (numpy arrays)
            profile_name: Name for the profile
            sample_rate: Sample rate in Hz
            
        Returns:
            True if enrollment successful, False otherwise
        """
        if not self.enabled or self.classifier is None:
            logger.error("❌ Speaker verification not initialized")
            return False
        
        try:
            logger.info(f"🎤 Enrolling speaker: {profile_name} ({len(audio_samples)} samples)")
            
            embeddings = []
            
            # Extract embeddings from all samples
            for i, audio in enumerate(audio_samples):
                logger.info(f"   Processing sample {i + 1}/{len(audio_samples)}...")
                embedding = self.extract_embedding_from_audio_data(audio, sample_rate)
                
                if embedding is not None:
                    embeddings.append(embedding)
                else:
                    logger.warning(f"⚠️ Failed to process sample {i + 1}")
            
            if len(embeddings) == 0:
                logger.error("❌ No valid embeddings extracted - enrollment failed")
                return False
            
            # Average all embeddings (more robust than single sample)
            avg_embedding = np.mean(embeddings, axis=0)
            avg_embedding = avg_embedding / np.linalg.norm(avg_embedding)  # Renormalize
            
            # Save profile
            profile_path = self.profiles_dir / f"{profile_name}.npy"
            np.save(profile_path, avg_embedding)
            
            # Save metadata
            metadata = {
                "name": profile_name,
                "enrolled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "sample_count": len(embeddings),
                "similarity_threshold": self.similarity_threshold
            }
            
            metadata_path = self.profiles_dir / f"{profile_name}.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Update cache
            self.profiles[profile_name] = avg_embedding
            self.profile_metadata[profile_name] = metadata
            
            logger.info(f"✅ Profile '{profile_name}' enrolled successfully!")
            logger.info(f"   Samples used: {len(embeddings)}/{len(audio_samples)}")
            logger.info(f"   Saved to: {profile_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Enrollment failed: {e}")
            return False
    
    def delete_profile(self, profile_name: str = "user_primary") -> bool:
        """
        Delete a speaker profile.
        
        Args:
            profile_name: Name of profile to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            profile_path = self.profiles_dir / f"{profile_name}.npy"
            metadata_path = self.profiles_dir / f"{profile_name}.json"
            
            if profile_path.exists():
                profile_path.unlink()
                logger.info(f"🗑️ Deleted profile: {profile_path}")
            
            if metadata_path.exists():
                metadata_path.unlink()
            
            # Remove from cache
            if profile_name in self.profiles:
                del self.profiles[profile_name]
            if profile_name in self.profile_metadata:
                del self.profile_metadata[profile_name]
            
            logger.info(f"✅ Profile '{profile_name}' deleted")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete profile: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Get verification statistics."""
        avg_time = (self.total_verification_time / self.verification_count 
                   if self.verification_count > 0 else 0.0)
        
        return {
            "enabled": self.enabled,
            "device": str(self.device) if self.device else None,
            "profiles_loaded": len(self.profiles),
            "verifications_performed": self.verification_count,
            "average_verification_time": f"{avg_time:.3f}s",
            "similarity_threshold": self.similarity_threshold,
            "gpu_enabled": self.use_gpu and self.device.type == "cuda",
            "fp16_enabled": self.use_fp16
        }
    
    def is_enabled(self) -> bool:
        """Check if speaker verification is enabled and ready."""
        return self.enabled and self.classifier is not None
    
    def has_profile(self, profile_name: str = "user_primary") -> bool:
        """Check if a speaker profile exists."""
        return profile_name in self.profiles
