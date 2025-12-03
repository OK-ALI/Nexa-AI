content = """# Nexa Configuration

# Gemini API Configuration
GEMINI_API_KEY=AIzaSyDqcdbj3-AR_ODOGy_i4aw45HpCt66DCbI
GEMINI_MODEL=gemini-2.0-flash-exp

# Faster-Whisper settings (GPU acceleration with CUDA)
WHISPER_MODEL_NAME=tiny.en
WHISPER_DEVICE=cuda

# === Weather Service ===
OPENWEATHERMAP_API_KEY=45511811070b0243de583c51bf1c355b
WEATHER_DEFAULT_LOCATION=
WEATHER_CACHE_MINUTES=30

# Audio Settings
CHANNELS=1
VOICE_SPEED=1.0
"""
# Update the bundled .env file in dist
with open(r"dist\Nexa AI\_internal\.env", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated bundled .env")
