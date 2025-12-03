import os
import base64
import re

def bundle_secrets():
    """
    Reads WEATHER_API_KEY from .env and bundles it into core/secrets_loader.py
    """
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    loader_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'core', 'secrets_loader.py')
    
    if not os.path.exists(env_path):
        print(f"Error: .env file not found at {env_path}")
        return

    api_key = None
    
    # Try reading with different encodings
    content = ""
    for encoding in ['utf-8', 'utf-16', 'utf-16le']:
        try:
            with open(env_path, 'r', encoding=encoding) as f:
                content = f.read()
            break
        except UnicodeError:
            continue
            
    for line in content.splitlines():
        if line.strip().startswith('WEATHER_API_KEY='):
            api_key = line.strip().split('=', 1)[1].strip()
            break
    
    if not api_key:
        print("Error: WEATHER_API_KEY not found in .env")
        return

    # Obfuscate
    encoded_key = base64.b64encode(api_key.encode('utf-8')).decode('utf-8')
    
    # Read loader
    with open(loader_path, 'r') as f:
        content = f.read()
    
    # Replace
    new_content = re.sub(
        r'obfuscated_key = ".*?"',
        f'obfuscated_key = "{encoded_key}"',
        content
    )
    
    with open(loader_path, 'w') as f:
        f.write(new_content)
        
    print(f"Successfully bundled API Key into {loader_path}")

if __name__ == "__main__":
    bundle_secrets()
