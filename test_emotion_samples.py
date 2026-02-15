"""
Generate different emotion samples with cloned af_heart voice using Coqui XTTS

Emotions are conveyed through:
1. Text content and phrasing
2. Speed adjustments
3. Punctuation cues (XTTS responds to !, ?, ...)
"""

import os
import sys
from pathlib import Path

# Emotion samples with text optimized for XTTS
# Key improvements:
# - Longer, more natural sentences (better prosody inference)
# - Avoid short exclamations that cause artifacts
# - No speed adjustment (causes librosa artifacts)
# - Text written to naturally convey emotion without relying on punctuation tricks

EMOTION_SAMPLES = {
    "neutral": {
        "text": "Hello, I am Nexa, your personal AI assistant. I'm here to help you with whatever you need today. Just let me know what's on your mind.",
        "speed": 1.0,
        "description": "Calm, informative tone"
    },
    "happy": {
        "text": "That's wonderful news, I'm really glad to hear that! I'd love to help you with this, it sounds like such a fun project to work on together.",
        "speed": 1.0,  # No speed change - let XTTS handle prosody naturally
        "description": "Upbeat, enthusiastic"
    },
    "sad": {
        "text": "I'm truly sorry to hear you're going through this. That sounds really difficult, and I want you to know that I'm here for you. We can take this slowly.",
        "speed": 1.0,
        "description": "Slow, empathetic, somber"
    },
    "excited": {
        "text": "This is absolutely incredible, I can hardly believe it! What an amazing achievement, you should be so proud of yourself! I'm thrilled for you!",
        "speed": 1.0,
        "description": "Fast, high energy"
    },
    "calm": {
        "text": "Let's take a moment to breathe. Everything is going to be okay. We'll work through this together, one small step at a time, there's no rush.",
        "speed": 1.0,
        "description": "Soothing, reassuring"
    },
    "curious": {
        "text": "That's really interesting, I hadn't thought of it that way before. Could you tell me a bit more about how that works? I'd love to understand better.",
        "speed": 1.0,
        "description": "Inquisitive, engaged"
    },
    "apologetic": {
        "text": "I'm really sorry about that mistake, it was my fault and I take full responsibility. Please let me make it up to you by fixing this right away.",
        "speed": 1.0,
        "description": "Regretful, sincere"
    },
    "confident": {
        "text": "Don't worry about a thing, I know exactly what to do here. I've handled situations like this many times before. You can count on me.",
        "speed": 1.0,
        "description": "Assured, capable"
    },
    "playful": {
        "text": "Oh you caught me! I was hoping you wouldn't notice that. Alright, alright, I admit it, that was pretty silly of me, wasn't it?",
        "speed": 1.0,
        "description": "Light, teasing"
    },
    "concerned": {
        "text": "Hold on, are you feeling alright? Something seems a bit off here, and I want to make sure everything is okay with you before we continue.",
        "speed": 1.0,
        "description": "Worried, attentive"
    }
}


def generate_emotion_samples():
    """Generate all emotion samples using XTTS with cloned af_heart voice."""
    print("=" * 60)
    print("🎭 Generating Emotion Samples with Cloned af_heart Voice")
    print("=" * 60)
    
    try:
        from TTS.api import TTS
        import torch
        import soundfile as sf
        
        # Check for reference audio
        ref_audio = Path("voice/af_heart_reference.wav")
        if not ref_audio.exists():
            print(f"❌ Reference audio not found: {ref_audio}")
            print("Run test_coqui_clone.py first to generate reference audio.")
            return
        
        # Check GPU
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🖥️ Using device: {device}")
        
        # Load XTTS model
        print("⏳ Loading XTTS model...")
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
        
        # Create output directory
        output_dir = Path("voice/emotion_samples")
        output_dir.mkdir(exist_ok=True)
        
        generated_files = []
        
        # Generate each emotion
        for emotion, config in EMOTION_SAMPLES.items():
            print(f"\n🎤 Generating '{emotion}' ({config['description']})...")
            
            output_path = output_dir / f"af_heart_{emotion}.wav"
            
            try:
                # Generate with XTTS
                # Note: XTTS doesn't have native speed control in tts_to_file,
                # but emotional text content influences prosody
                tts.tts_to_file(
                    text=config["text"],
                    file_path=str(output_path),
                    speaker_wav=str(ref_audio),
                    language="en"
                )
                
                # Apply speed adjustment using soundfile if needed
                if config["speed"] != 1.0:
                    apply_speed_adjustment(str(output_path), config["speed"])
                
                print(f"   ✅ Saved: {output_path}")
                generated_files.append((emotion, str(output_path), config["description"]))
                
            except Exception as e:
                print(f"   ❌ Failed: {e}")
        
        # Summary
        print("\n" + "=" * 60)
        print("✅ Emotion samples generated!")
        print("=" * 60)
        print(f"\n📁 Output folder: {output_dir.absolute()}\n")
        
        for emotion, path, desc in generated_files:
            print(f"  🎭 {emotion:12} - {desc}")
        
        return generated_files
        
    except ImportError as e:
        print(f"❌ Coqui TTS not installed: {e}")
        print("Install with: uv pip install coqui-tts")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def apply_speed_adjustment(audio_path: str, speed: float):
    """Apply speed adjustment to audio file using librosa."""
    try:
        import librosa
        import soundfile as sf
        import numpy as np
        
        # Load audio
        y, sr = librosa.load(audio_path, sr=None)
        
        # Time stretch (speed up or slow down)
        # stretch factor < 1 = slower, > 1 = faster
        y_stretched = librosa.effects.time_stretch(y, rate=speed)
        
        # Save back
        sf.write(audio_path, y_stretched, sr)
        
    except Exception as e:
        print(f"   ⚠️ Could not apply speed adjustment: {e}")


def play_samples():
    """Play all generated emotion samples."""
    output_dir = Path("voice/emotion_samples")
    
    if not output_dir.exists():
        print("No emotion samples found. Run generation first.")
        return
    
    try:
        import pygame
        pygame.mixer.init()
        
        samples = sorted(output_dir.glob("af_heart_*.wav"))
        
        for sample in samples:
            emotion = sample.stem.replace("af_heart_", "")
            config = EMOTION_SAMPLES.get(emotion, {})
            
            print(f"\n🔊 Playing: {emotion} - {config.get('description', '')}")
            print(f"   Text: \"{config.get('text', '')}\"")
            
            pygame.mixer.music.load(str(sample))
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            
            # Small pause between samples
            pygame.time.wait(500)
        
        pygame.mixer.quit()
        print("\n✅ Playback complete!")
        
    except Exception as e:
        print(f"Could not play audio: {e}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate emotion samples with cloned voice")
    parser.add_argument("--play", action="store_true", help="Play generated samples")
    parser.add_argument("--generate", action="store_true", help="Generate new samples")
    args = parser.parse_args()
    
    if args.play:
        play_samples()
    elif args.generate or not any([args.play]):
        # Default: generate
        files = generate_emotion_samples()
        if files:
            print("\n🎧 Playing samples...")
            play_samples()


if __name__ == "__main__":
    main()
