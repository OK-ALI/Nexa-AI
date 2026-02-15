"""
Test Coqui XTTS Voice Cloning with af_heart voice from Kokoro

This script:
1. Generates a reference audio sample using Kokoro's af_heart voice
2. Uses Coqui XTTS to clone that voice
3. Generates test speech with the cloned voice
"""

import os
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent))

def generate_reference_audio():
    """Generate a reference audio sample using Kokoro's af_heart voice."""
    print("📢 Step 1: Generating reference audio with Kokoro af_heart...")
    
    try:
        import os
        import torch
        import soundfile as sf
        import numpy as np
        
        # Set espeak path before import
        espeak_path = Path(__file__).parent / "voice" / "espeak-ng-data"
        if espeak_path.exists():
            os.environ['PHONEMIZER_ESPEAK_DATA'] = str(espeak_path)
        
        from kokoro_onnx import Kokoro
        from kokoro_onnx.config import SAMPLE_RATE
        
        # Initialize Kokoro
        model_path = Path("voice/kokoro_models/kokoro-v1.0.onnx")
        voices_path = Path("voice/kokoro_models/voices-v1.0.bin")
        
        if not model_path.exists() or not voices_path.exists():
            print(f"❌ Kokoro model files not found!")
            print(f"   Expected: {model_path} and {voices_path}")
            return None
        
        kokoro = Kokoro(str(model_path), str(voices_path))
        
        # Generate a clear reference sample (10-15 seconds is ideal for cloning)
        reference_text = """
        Hello, I am Nexa, your friendly AI assistant. 
        I was created by Ali Adil Waseem to help you with your daily tasks.
        I can control your computer, play music, and answer your questions.
        Let me know how I can assist you today.
        """
        
        # Generate audio
        print("🎤 Generating with af_heart voice...")
        audio, _ = kokoro.create(
            reference_text.strip(),
            voice="af_heart",
            speed=1.0
        )
        
        # Save reference audio
        ref_path = Path("voice/af_heart_reference.wav")
        ref_path.parent.mkdir(exist_ok=True)
        sf.write(str(ref_path), audio, SAMPLE_RATE)
        print(f"✅ Reference audio saved: {ref_path}")
        return str(ref_path)
            
    except Exception as e:
        print(f"❌ Kokoro error: {e}")
        import traceback
        traceback.print_exc()
        return None


def clone_voice_with_coqui(reference_audio_path: str):
    """Use Coqui XTTS to clone the voice and generate test audio."""
    print("\n📢 Step 2: Cloning voice with Coqui XTTS...")
    
    try:
        # Try new package name first (coqui-tts), fallback to old (TTS)
        try:
            from TTS.api import TTS
        except ImportError:
            from coqui_tts.api import TTS
        import torch
        
        # Check GPU
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🖥️ Using device: {device}")
        
        # Initialize XTTS model (will download if not present)
        print("⏳ Loading XTTS model (may take a while on first run)...")
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
        
        # Test text for cloned voice
        test_text = "This is a test of voice cloning using Coqui XTTS. The voice should sound similar to the original af heart voice from Kokoro."
        
        # Generate cloned audio
        output_path = "voice/coqui_cloned_af_heart.wav"
        print(f"🎤 Generating cloned speech...")
        
        tts.tts_to_file(
            text=test_text,
            file_path=output_path,
            speaker_wav=reference_audio_path,
            language="en"
        )
        
        print(f"✅ Cloned audio saved: {output_path}")
        return output_path
        
    except ImportError as e:
        print(f"❌ Coqui TTS not installed: {e}")
        print("Install with: uv pip install coqui-tts")
        return None
    except Exception as e:
        print(f"❌ Coqui error: {e}")
        import traceback
        traceback.print_exc()
        return None


def play_audio(audio_path: str):
    """Play the generated audio."""
    print(f"\n🔊 Playing: {audio_path}")
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(audio_path)
        pygame.mixer.music.play()
        
        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        
        pygame.mixer.quit()
    except Exception as e:
        print(f"Could not play audio: {e}")
        print(f"Audio file is at: {audio_path}")


def main():
    print("=" * 60)
    print("🎤 Coqui XTTS Voice Cloning Test - af_heart")
    print("=" * 60)
    
    # Step 1: Generate reference audio with Kokoro
    ref_audio = generate_reference_audio()
    
    if not ref_audio:
        # Try using existing reference if available
        existing_ref = Path("voice/af_heart_reference.wav")
        if existing_ref.exists():
            print(f"📂 Using existing reference: {existing_ref}")
            ref_audio = str(existing_ref)
        else:
            print("❌ Could not generate reference audio")
            return
    
    # Step 2: Clone with Coqui
    cloned_audio = clone_voice_with_coqui(ref_audio)
    
    if cloned_audio and Path(cloned_audio).exists():
        # Play both for comparison
        print("\n🎧 Playing ORIGINAL (Kokoro af_heart):")
        play_audio(ref_audio)
        
        print("\n🎧 Playing CLONED (Coqui XTTS):")
        play_audio(cloned_audio)
        
        print("\n" + "=" * 60)
        print("✅ Voice cloning test complete!")
        print(f"📁 Reference: {ref_audio}")
        print(f"📁 Cloned: {cloned_audio}")
        print("=" * 60)
    else:
        print("❌ Voice cloning failed")


if __name__ == "__main__":
    main()
