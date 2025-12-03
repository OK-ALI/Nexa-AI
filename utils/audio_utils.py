"""
Audio Utilities
Helper functions for audio processing and manipulation.
"""

import numpy as np
from typing import Tuple


def calculate_rms(audio_data: bytes) -> float:
    """
    Calculate RMS (Root Mean Square) of audio data.
    
    Args:
        audio_data: Raw audio bytes
        
    Returns:
        RMS value
    """
    samples = np.frombuffer(audio_data, dtype=np.int16)
    return np.sqrt(np.mean(samples**2))


def detect_silence(audio_data: bytes, threshold: float = 500.0) -> bool:
    """
    Detect if audio contains silence.
    
    Args:
        audio_data: Raw audio bytes
        threshold: RMS threshold for silence
        
    Returns:
        True if silence detected
    """
    rms = calculate_rms(audio_data)
    return rms < threshold


def normalize_audio(audio_data: bytes, target_rms: float = 3000.0) -> bytes:
    """
    Normalize audio to target RMS level.
    
    Args:
        audio_data: Raw audio bytes
        target_rms: Target RMS level
        
    Returns:
        Normalized audio bytes
    """
    samples = np.frombuffer(audio_data, dtype=np.int16)
    current_rms = np.sqrt(np.mean(samples**2))
    
    if current_rms > 0:
        scaling_factor = target_rms / current_rms
        normalized = (samples * scaling_factor).astype(np.int16)
        return normalized.tobytes()
    
    return audio_data


def resample_audio(
    audio_data: bytes,
    original_rate: int,
    target_rate: int
) -> bytes:
    """
    Resample audio to different sample rate.
    
    Args:
        audio_data: Raw audio bytes
        original_rate: Original sample rate
        target_rate: Target sample rate
        
    Returns:
        Resampled audio bytes
    """
    # This is a placeholder - real resampling requires scipy or librosa
    # For now, just return original data
    return audio_data
