"""
Qwen3-TTS Voice Testing Script
Test different voices and emotions for NEXA AI Assistant

RTX 3080 8GB: Use 0.6B model for safe VRAM usage
For 1.7B model, requires flash_attention_2 to fit in 8GB

Installation:
    pip install qwen-tts soundfile
    pip install flash-attn --no-build-isolation  # Optional, for 1.7B model
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import torch
import soundfile as sf


def check_gpu():
    """Check GPU availability and VRAM."""
    if not torch.cuda.is_available():
        print("❌ CUDA not available! Qwen3-TTS requires GPU.")
        return False
    
    gpu_name = torch.cuda.get_device_name(0)
    vram_total = torch.cuda.get_device_properties(0).total_memory / 1024**3
    vram_free = (torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated(0)) / 1024**3
    
    print(f"✅ GPU: {gpu_name}")
    print(f"   VRAM: {vram_total:.1f} GB total, ~{vram_free:.1f} GB free")
    
    if vram_total < 6:
        print("⚠️ Warning: Less than 6GB VRAM - may have issues with 0.6B model")
    elif vram_total < 8:
        print("💡 Tip: 6-8GB VRAM - Use 0.6B model for best stability")
    else:
        print("💡 Tip: 8GB+ VRAM - Can try 1.7B model with flash_attention_2")
    
    return True


def test_voices():
    """Test Qwen3-TTS with various voices and emotions."""
    try:
        from qwen_tts import Qwen3TTSModel
    except ImportError:
        print("❌ qwen-tts not installed!")
        print("   Run: pip install qwen-tts")
        return
    
    # Output directory
    output_dir = project_root / "tests" / "qwen3_tts_samples"
    output_dir.mkdir(exist_ok=True)
    print(f"\n📁 Output directory: {output_dir}")
    
    # Choose model based on VRAM (0.6B is safer for 8GB)
    # Change to "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice" for higher quality if VRAM allows
    model_name = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
    
    print(f"\n🔄 Loading model: {model_name}")
    print("   This may take a few minutes on first run (downloading ~2GB)...")
    
    try:
        model = Qwen3TTSModel.from_pretrained(
            model_name,
            device_map="cuda:0",
            dtype=torch.bfloat16,
        )
    except Exception as e:
        if "memory" in str(e).lower():
            print(f"❌ Out of Memory! Try closing other apps or use smaller model.")
        else:
            print(f"❌ Failed to load model: {e}")
        return
    
    print("✅ Model loaded!\n")
    
    # Get available speakers and languages
    speakers = model.get_supported_speakers()
    languages = model.get_supported_languages()
    
    print(f"📢 Available speakers ({len(speakers)}):")
    for i, speaker in enumerate(speakers):
        print(f"   {i+1}. {speaker}")
    
    print(f"\n🌍 Available languages: {', '.join(languages)}")
    
    # Test sentences for NEXA
    test_cases = [
        # (text, speaker, language, instruct/emotion, filename)
        ("Hello! I'm Nexa, your personal AI assistant. How can I help you today?", 
         "Vivian", "English", "", "01_vivian_neutral"),
        
        ("Hello! I'm Nexa, your personal AI assistant. How can I help you today?", 
         "Vivian", "English", "Speak warmly and friendly", "02_vivian_warm"),
        
        ("I found 3 new emails in your inbox. Would you like me to read them?",
         "Vivian", "English", "Speak helpfully and professionally", "03_vivian_helpful"),
        
        ("Your meeting starts in 10 minutes. Should I prepare the presentation?",
         "Vivian", "English", "Speak with gentle urgency", "04_vivian_urgent"),
        
        ("Great job! You've completed all your tasks for today.",
         "Vivian", "English", "Speak happily and encouragingly", "05_vivian_happy"),
        
        ("I'm sorry, but I couldn't complete that request. Let me try a different approach.",
         "Vivian", "English", "Speak apologetically but reassuringly", "06_vivian_apologetic"),
        
        # Try different speakers for comparison
        ("Hello! I'm Nexa, your personal AI assistant.",
         "Ryan", "English", "Speak warmly and professionally", "07_ryan_warm"),
        
        ("Hello! I'm Nexa, your personal AI assistant.",
         "Emma", "English", "Speak warmly and professionally", "08_emma_warm"),
        
        ("Hello! I'm Nexa, your personal AI assistant.",
         "Sophia", "English", "Speak warmly and professionally", "09_sophia_warm"),
    ]
    
    print(f"\n🎤 Generating {len(test_cases)} voice samples...\n")
    
    for i, (text, speaker, language, instruct, filename) in enumerate(test_cases):
        print(f"[{i+1}/{len(test_cases)}] {filename}")
        print(f"    Speaker: {speaker} | Emotion: {instruct or 'neutral'}")
        
        try:
            wavs, sr = model.generate_custom_voice(
                text=text,
                language=language,
                speaker=speaker,
                instruct=instruct if instruct else None,
            )
            
            output_path = output_dir / f"{filename}.wav"
            sf.write(str(output_path), wavs[0], sr)
            print(f"    ✅ Saved: {output_path.name}")
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
        
        # Clear cache between generations to prevent OOM
        torch.cuda.empty_cache()
    
    print(f"\n✅ Done! Check the samples in: {output_dir}")
    print("\n💡 Listen to the samples and decide which voice/style fits NEXA best!")


def test_voice_cloning():
    """Test voice cloning feature (optional)."""
    try:
        from qwen_tts import Qwen3TTSModel
    except ImportError:
        print("❌ qwen-tts not installed!")
        return
    
    output_dir = project_root / "tests" / "qwen3_tts_samples"
    output_dir.mkdir(exist_ok=True)
    
    # Use Base model for voice cloning
    model_name = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
    
    print(f"\n🔄 Loading voice cloning model: {model_name}")
    
    model = Qwen3TTSModel.from_pretrained(
        model_name,
        device_map="cuda:0",
        dtype=torch.bfloat16,
    )
    
    # Example: Clone from sample audio URL
    ref_audio = "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-TTS-Repo/clone.wav"
    ref_text = "Okay. Yeah. I resent you. I love you. I respect you. But you know what? You blew it!"
    
    print("🎤 Generating cloned voice sample...")
    
    wavs, sr = model.generate_voice_clone(
        text="Hello! I'm Nexa, your personal AI assistant. How can I help you today?",
        language="English",
        ref_audio=ref_audio,
        ref_text=ref_text,
    )
    
    output_path = output_dir / "10_voice_clone_test.wav"
    sf.write(str(output_path), wavs[0], sr)
    print(f"✅ Saved: {output_path}")


if __name__ == "__main__":
    print("=" * 60)
    print("🎵 Qwen3-TTS Voice Testing for NEXA")
    print("=" * 60)
    
    if not check_gpu():
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("Choose test mode:")
    print("  1. Test preset voices (recommended first)")
    print("  2. Test voice cloning")
    print("  3. Both")
    print("=" * 60)
    
    choice = input("\nEnter choice [1/2/3] (default: 1): ").strip() or "1"
    
    if choice in ["1", "3"]:
        test_voices()
    
    if choice in ["2", "3"]:
        test_voice_cloning()
    
    print("\n🎉 Testing complete!")
