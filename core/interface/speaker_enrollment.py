"""
Speaker Enrollment Module
Handles interactive voice enrollment process for speaker verification.
"""

import logging
import numpy as np
import time
from typing import List, Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


class SpeakerEnrollment:
    """
    Manages speaker enrollment process with guided prompts and validation.
    """
    
    # SIMPLIFIED: Easy-to-say enrollment prompts with natural commands
    # Covers different tones, volumes, and speeds while being SHORT and EASY
    ENROLLMENT_PROMPTS = [
        # Sample 1: Normal greeting (short, neutral tone)
        {
            "text": "Hey Nexa, how are you doing today?",
            "instruction": "Say this in your normal speaking voice",
            "category": "normal"
        },
        # Sample 2: Loud/Clear (short command, higher volume)
        {
            "text": "Nexa, please open my browser",
            "instruction": "Say this LOUDLY and clearly",
            "category": "loud"
        },
        # Sample 3: Soft/Quiet (short question, lower volume)
        {
            "text": "What time is it right now?",
            "instruction": "Say this SOFTLY and quietly",
            "category": "soft"
        },
        # Sample 4: Fast speech (natural command, rapid delivery)
        {
            "text": "Play some music and check the weather",
            "instruction": "Say this QUICKLY, like you're in a hurry",
            "category": "fast"
        },
        # Sample 5: Slow/Deliberate (natural request, slow delivery)
        {
            "text": "Can you tell me about the news today?",
            "instruction": "Say this SLOWLY and clearly",
            "category": "slow"
        },
        # Sample 6: Excited/Happy (medium length, higher energy)
        {
            "text": "That's awesome! Thanks for your help Nexa!",
            "instruction": "Say this happily and enthusiastically",
            "category": "happy"
        },
        # Sample 7: Natural conversation (medium length, conversational)
        {
            "text": "I need you to recognize my voice every time",
            "instruction": "Say this naturally, like normal conversation",
            "category": "conversational"
        }
    ]
    
    def __init__(self, speaker_verification, audio_listener, tts_engine):
        """
        Initialize enrollment manager.
        
        Args:
            speaker_verification: SpeakerVerification instance
            audio_listener: AudioListener instance for recording
            tts_engine: TTSEngine for speaking prompts
        """
        self.speaker_verifier = speaker_verification
        self.listener = audio_listener
        self.tts = tts_engine
        
        self.is_enrolling = False
        self.enrollment_samples: List[np.ndarray] = []
        self.current_prompt_index = 0
        
        # NEW: Profile merging support (for adding samples to existing profile)
        self.is_merging_profile = False
        self.existing_profile_embedding = None
        self.existing_profile_sample_count = 0
        
    def start_enrollment(self, num_samples: int = 5, profile_name: str = "user_primary",
                        on_complete: Optional[Callable] = None) -> bool:
        """
        Start interactive enrollment process.
        
        Args:
            num_samples: Number of voice samples to record (3-8 recommended)
            profile_name: Name for the voice profile
            on_complete: Callback function when enrollment completes
            
        Returns:
            True if enrollment started successfully
        """
        if not self.speaker_verifier.is_enabled():
            logger.error("❌ Speaker verification not initialized")
            return False
        
        if self.is_enrolling:
            logger.warning("⚠️ Enrollment already in progress")
            return False
        
        try:
            logger.info(f"🎤 Starting voice enrollment: {num_samples} samples")
            
            self.is_enrolling = True
            self.enrollment_samples = []
            self.current_prompt_index = 0
            self.profile_name = profile_name
            self.num_samples = min(num_samples, len(self.ENROLLMENT_PROMPTS))
            self.on_complete_callback = on_complete
            
            # Welcome message
            welcome_msg = (
                f"Let's set up your voice profile! "
                f"I'll need {self.num_samples} voice samples. "
                f"Please speak clearly and naturally."
            )
            
            logger.info(f"💬 {welcome_msg}")
            if self.tts:
                self.tts.speak(welcome_msg)
                time.sleep(0.5)  # Brief pause
            
            # Start first prompt
            self._prompt_next_sample()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start enrollment: {e}")
            self.is_enrolling = False
            return False
    
    def _prompt_next_sample(self):
        """Prompt user for next voice sample with guided instructions."""
        if self.current_prompt_index >= self.num_samples:
            # All samples collected
            self._finalize_enrollment()
            return
        
        sample_num = self.current_prompt_index + 1
        prompt_data = self.ENROLLMENT_PROMPTS[self.current_prompt_index]
        
        # NEW: Extract prompt components
        prompt_text = prompt_data["text"]
        instruction = prompt_data["instruction"]
        category = prompt_data["category"]
        
        # Build enhanced instruction message
        full_instruction = (
            f"Sample {sample_num} of {self.num_samples}. "
            f"{instruction}. "
            f"Ready? Say: {prompt_text}"
        )
        
        logger.info(f"📝 Sample {sample_num}/{self.num_samples} ({category})")
        logger.info(f"   Instruction: {instruction}")
        logger.info(f"   Prompt: {prompt_text}")
        
        if self.tts:
            self.tts.speak(full_instruction)
        
        # Wait for TTS to finish, then start listening
        # Note: Actual recording happens via listener callback
        logger.debug("🎤 Ready to record sample...")
    
    def process_enrollment_audio(self, audio_data: np.ndarray, sample_rate: int = 16000) -> bool:
        """
        Process recorded audio during enrollment with ENHANCED quality validation.
        
        Args:
            audio_data: Recorded audio samples
            sample_rate: Sample rate
            
        Returns:
            True if sample accepted, False if rejected
        """
        if not self.is_enrolling:
            return False
        
        try:
            sample_num = self.current_prompt_index + 1
            logger.info(f"🔍 Processing enrollment sample {sample_num}/{self.num_samples}...")
            
            # ENHANCED: Comprehensive audio quality validation
            audio_duration = len(audio_data) / sample_rate
            rms_energy = np.sqrt(np.mean(audio_data ** 2))
            audio_range = np.max(np.abs(audio_data))
            
            logger.debug(f"   Audio metrics: duration={audio_duration:.2f}s, RMS={rms_energy:.4f}, range={audio_range:.4f}")
            
            # Check 1: Minimum duration (at least 2 seconds for good embeddings)
            min_duration = 2.0  # Longer than verification (need quality samples for enrollment)
            if audio_duration < min_duration:
                logger.warning(f"⚠️ Audio too short ({audio_duration:.1f}s < {min_duration}s)")
                if self.tts:
                    self.tts.speak(f"That was too short. Please say the full sentence clearly. Try again.")
                self._prompt_next_sample()  # Retry same prompt
                return False
            
            # Check 2: Energy level (avoid too quiet)
            min_energy = 0.015  # Slightly higher than verification threshold
            if rms_energy < min_energy:
                logger.warning(f"⚠️ Audio too quiet (RMS={rms_energy:.4f} < {min_energy})")
                if self.tts:
                    self.tts.speak("I couldn't hear you well. Please speak louder and try again.")
                self._prompt_next_sample()  # Retry same prompt
                return False
            
            # Check 3: Dynamic range (avoid flat/clipped audio)
            min_range = 0.01
            max_range = 0.95  # Detect clipping
            if audio_range < min_range:
                logger.warning(f"⚠️ Audio has no dynamic range ({audio_range:.4f})")
                if self.tts:
                    self.tts.speak("Audio quality issue detected. Please try again.")
                self._prompt_next_sample()
                return False
            elif audio_range > max_range:
                logger.warning(f"⚠️ Audio is clipping ({audio_range:.4f} > {max_range}) - too loud!")
                if self.tts:
                    self.tts.speak("That was too loud and may be distorted. Please speak a bit quieter.")
                self._prompt_next_sample()
                return False
            
            # Check 4: Extract embedding to validate voice features
            embedding = self.speaker_verifier.extract_embedding_from_audio_data(audio_data, sample_rate)
            
            if embedding is None:
                logger.warning("⚠️ Failed to extract voice features - trying again")
                if self.tts:
                    self.tts.speak("I couldn't process that sample. Let's try again.")
                self._prompt_next_sample()  # Retry same prompt
                return False
            
            # ✅ Sample is GOOD - save it
            logger.info(f"✅ Sample {sample_num} accepted - Quality: GOOD")
            logger.info(f"   Duration: {audio_duration:.2f}s, RMS: {rms_energy:.4f}, Range: {audio_range:.4f}")
            self.enrollment_samples.append(audio_data)
            logger.info(f"✅ Sample {self.current_prompt_index + 1} recorded successfully")
            
            if self.tts:
                self.tts.speak("Good!")
                time.sleep(0.3)
            
            # Move to next sample
            self.current_prompt_index += 1
            self._prompt_next_sample()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error processing enrollment audio: {e}")
            if self.tts:
                self.tts.speak("An error occurred. Let's try again.")
            self._prompt_next_sample()
            return False
    
    def _finalize_enrollment(self):
        """Complete enrollment and create voice profile."""
        try:
            logger.info(f"🎯 Finalizing enrollment with {len(self.enrollment_samples)} samples...")
            
            if self.tts:
                self.tts.speak("Processing your voice profile...")
            
            # Check if merging with existing profile
            if self.is_merging_profile:
                success = self._finalize_enrollment_with_merge()
            else:
                # Create new profile using speaker verification
                success = self.speaker_verifier.enroll_speaker(
                    audio_samples=self.enrollment_samples,
                    profile_name=self.profile_name,
                    sample_rate=16000
                )
            
            if success:
                completion_msg = (
                    "Perfect! Your voice profile is ready. "
                    "I'll now only respond to your voice."
                )
                logger.info(f"✅ {completion_msg}")
                if self.tts:
                    self.tts.speak(completion_msg)
                
                # Call completion callback if provided
                if self.on_complete_callback:
                    self.on_complete_callback(True, self.profile_name)
            else:
                error_msg = "Sorry, enrollment failed. Please try again later."
                logger.error(f"❌ {error_msg}")
                if self.tts:
                    self.tts.speak(error_msg)
                
                if self.on_complete_callback:
                    self.on_complete_callback(False, None)
            
        except Exception as e:
            logger.error(f"❌ Failed to finalize enrollment: {e}")
            if self.tts:
                self.tts.speak("An error occurred during enrollment. Please try again.")
            
            if self.on_complete_callback:
                self.on_complete_callback(False, None)
        
        finally:
            # Reset enrollment state
            self.is_enrolling = False
            self.enrollment_samples = []
            self.current_prompt_index = 0
    
    def cancel_enrollment(self):
        """Cancel ongoing enrollment process."""
        if not self.is_enrolling:
            return
        
        logger.info("🛑 Enrollment cancelled by user")
        if self.tts:
            self.tts.speak("Enrollment cancelled.")
        
        self.is_enrolling = False
        self.enrollment_samples = []
        self.current_prompt_index = 0
        
        if self.on_complete_callback:
            self.on_complete_callback(False, None)
    
    def get_enrollment_status(self) -> dict:
        """Get current enrollment status."""
        return {
            "is_enrolling": self.is_enrolling,
            "samples_collected": len(self.enrollment_samples),
            "samples_required": self.num_samples if self.is_enrolling else 0,
            "current_prompt": (self.ENROLLMENT_PROMPTS[self.current_prompt_index] 
                              if self.is_enrolling and self.current_prompt_index < len(self.ENROLLMENT_PROMPTS)
                              else None)
        }
    
    def check_voice_profile(self, profile_name: str = "user_primary") -> Optional[dict]:
        """
        Get information about existing voice profile.
        
        Args:
            profile_name: Name of profile to check
            
        Returns:
            Profile metadata dict or None if not found
        """
        try:
            if profile_name in self.speaker_verifier.profile_metadata:
                metadata = self.speaker_verifier.profile_metadata[profile_name]
                
                # Build user-friendly message
                enrolled_date = metadata.get("enrolled_at", "Unknown")
                sample_count = metadata.get("sample_count", "Unknown")
                threshold = metadata.get("similarity_threshold", self.speaker_verifier.similarity_threshold)
                
                info_msg = (
                    f"Your voice profile was created on {enrolled_date} "
                    f"using {sample_count} voice samples. "
                    f"Current verification threshold is {threshold * 100:.0f}%."
                )
                
                logger.info(f"📊 Profile info: {info_msg}")
                if self.tts:
                    self.tts.speak(info_msg)
                
                return metadata
            else:
                no_profile_msg = "No voice profile found. Say 'enroll my voice' to create one."
                logger.info(f"❌ {no_profile_msg}")
                if self.tts:
                    self.tts.speak(no_profile_msg)
                return None
                
        except Exception as e:
            logger.error(f"❌ Error checking profile: {e}")
            return None
    
    def add_voice_samples(self, num_new_samples: int = 3, profile_name: str = "user_primary") -> bool:
        """
        Add additional samples to existing profile (merge with current).
        
        Args:
            num_new_samples: Number of new samples to add (default 3)
            profile_name: Profile to update
            
        Returns:
            True if successful
        """
        try:
            # Check if profile exists
            if profile_name not in self.speaker_verifier.profiles:
                logger.warning(f"⚠️ Profile '{profile_name}' not found - use 'enroll voice' instead")
                if self.tts:
                    self.tts.speak("No existing profile found. Please enroll your voice first.")
                return False
            
            logger.info(f"🔄 Adding {num_new_samples} samples to existing profile: {profile_name}")
            
            if self.tts:
                msg = (
                    f"I'll add {num_new_samples} new voice samples to your existing profile. "
                    f"This will improve recognition accuracy."
                )
                self.tts.speak(msg)
                time.sleep(0.5)
            
            # Store existing embedding for later merging
            self.existing_profile_embedding = self.speaker_verifier.profiles[profile_name].copy()
            self.existing_profile_sample_count = self.speaker_verifier.profile_metadata[profile_name].get("sample_count", 5)
            
            # Start enrollment process (will merge in _finalize_enrollment_with_merge)
            self.is_merging_profile = True
            return self.start_enrollment(num_samples=num_new_samples, profile_name=profile_name)
            
        except Exception as e:
            logger.error(f"❌ Error adding voice samples: {e}")
            return False
    
    def _finalize_enrollment_with_merge(self):
        """
        Finalize enrollment by MERGING new samples with existing profile.
        This is called instead of _finalize_enrollment when adding samples.
        """
        try:
            logger.info(f"🔄 Merging {len(self.enrollment_samples)} new samples with existing profile...")
            
            # Extract embeddings from new samples
            new_embeddings = []
            for i, audio in enumerate(self.enrollment_samples):
                embedding = self.speaker_verifier.extract_embedding_from_audio_data(audio, 16000)
                if embedding is not None:
                    new_embeddings.append(embedding)
            
            if len(new_embeddings) == 0:
                logger.error("❌ No valid new embeddings - merge failed")
                return False
            
            # Calculate weighted average:
            # - Existing profile (from N samples)
            # - New samples (M samples)
            # Final = (N * existing + M * new_avg) / (N + M)
            
            old_weight = self.existing_profile_sample_count
            new_weight = len(new_embeddings)
            total_weight = old_weight + new_weight
            
            new_avg_embedding = np.mean(new_embeddings, axis=0)
            
            merged_embedding = (
                (old_weight * self.existing_profile_embedding) +
                (new_weight * new_avg_embedding)
            ) / total_weight
            
            # Renormalize
            merged_embedding = merged_embedding / np.linalg.norm(merged_embedding)
            
            # Save updated profile
            profile_path = self.speaker_verifier.profiles_dir / f"{self.profile_name}.npy"
            np.save(profile_path, merged_embedding)
            
            # Update in-memory profile
            self.speaker_verifier.profiles[self.profile_name] = merged_embedding
            
            # Update metadata
            self.speaker_verifier.profile_metadata[self.profile_name].update({
                "sample_count": total_weight,
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            
            logger.info(f"✅ Profile updated: {old_weight} + {new_weight} = {total_weight} total samples")
            
            if self.tts:
                msg = f"Great! Your voice profile now includes {total_weight} samples and should recognize you even better."
                self.tts.speak(msg)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error merging profiles: {e}")
            return False
        finally:
            self.is_merging_profile = False
            self.existing_profile_embedding = None
            self.existing_profile_sample_count = 0
