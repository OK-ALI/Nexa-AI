import base64

def get_weather_api_key():
    """
    Returns the bundled OpenWeather API Key.
    The key is obfuscated to prevent simple text searching in the binary.
    """
    # This value will be replaced by utils/setup_secrets.py
    obfuscated_key = "REBMQUNFX01FX1dJVEhfUkVBTF9LRVk=" 
    
    try:
        return base64.b64decode(obfuscated_key).decode('utf-8')
    except Exception:
        return None
