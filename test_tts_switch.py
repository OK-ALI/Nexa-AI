"""
Test TTS Engine Switching - Kokoro vs Coqui XTTS

This script tests the ability to switch between TTS engines.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

def test_tts_engines():
    """Test both TTS engines."""
    print("=" * 60)
    print("🔊 TTS Engine Switch Test")
    print("=" * 60)
    
    from config.settings import Config
    
    # Test Kokoro (default)
    print("\n📌 Testing Kokoro TTS (default)...")
    config = Config()
    config.tts_engine = 'kokoro'
    
    from core.interface.tts_engine import TTSEngine
    kokoro = TTSEngine(config)
    
    print("🎤 Speaking with Kokoro...")
    kokoro.speak("This is the Kokoro voice engine. Fast and lightweight.")
    
    import time
    time.sleep(0.5)
    kokoro.cleanup()
    
    # Test Coqui
    print("\n📌 Testing Coqui TTS (cloned voice)...")
    config.tts_engine = 'coqui'
    
    # Check if reference audio exists
    ref_audio = config.voice_dir / "af_heart_reference.wav"
    if not ref_audio.exists():
        print(f"❌ Reference audio not found: {ref_audio}")
        print("   Run test_coqui_clone.py first to generate it.")
        return
    
    from core.interface.tts_coqui import CoquiTTSEngine
    coqui = CoquiTTSEngine(config)
    
    print("🎤 Speaking with Coqui XTTS (cloned voice)...")
    coqui.speak("This is the Coqui voice engine. It uses the cloned voice with better emotional range.")
    
    time.sleep(0.5)
    coqui.cleanup()
    
    print("\n✅ TTS engine test complete!")
    print("=" * 60)


if __name__ == "__main__":
    test_tts_engines()
