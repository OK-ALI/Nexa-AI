"""
NEXA Import Migration Script
Rewrites old core.X imports to new capabilities.X paths.
Run this after files have been copied to capabilities/.
"""
import os
import re

BASE = r"d:\Projects\Nexa-MyAI"

# Mapping: old module name -> new absolute import path
MIGRATION_MAP = {
    # === capabilities/system/ ===
    "system_control": "capabilities.system.system_control",
    "application_controller": "capabilities.system.app_controller",
    "app_discovery": "capabilities.system.app_discovery",
    "app_name_mapper": "capabilities.system.app_name_mapper",
    "file_manager": "capabilities.system.file_manager",
    "window_manager": "capabilities.system.window_manager",
    "volume_controller": "capabilities.system.volume_controller",
    "brightness_controller": "capabilities.system.brightness_controller",
    "mouse_controller": "capabilities.system.mouse_controller",
    "screen_controller": "capabilities.system.screen_controller",
    "battery_manager": "capabilities.system.battery_manager",
    "wifi_controller": "capabilities.system.wifi_controller",
    "system_info_controller": "capabilities.system.system_info",
    
    # === capabilities/media/ ===
    "youtube_service": "capabilities.media.youtube_service",
    "music_manager": "capabilities.media.music_manager",
    "content_mode_handler": "capabilities.media.media_controller",
    
    # === capabilities/vision/ ===
    "screen_reader": "capabilities.vision.screen_reader",
    "screenshot_manager": "capabilities.vision.screenshot_manager",
    "notification_reader": "capabilities.vision.notification_reader",
    "live2d_engine": "capabilities.vision.live2d_engine",
    
    # === capabilities/llm/ ===
    "llm_manager": "capabilities.llm.llm_manager",
    "gpu_monitor": "capabilities.llm.gpu_monitor",
    
    # === capabilities/web/ ===
    "web_scraper": "capabilities.web.web_scraper",
    "weather_service": "capabilities.web.weather_service",
    "sharing_service": "capabilities.web.sharing_service",
    "share_helper": "capabilities.web.share_helper",
    "file_share_handler": "capabilities.web.file_share_handler",
    "auth_manager": "capabilities.web.auth_manager",
    
    # === capabilities/creative/ ===
    "pdf_generator": "capabilities.creative.pdf_generator",
    "game_manager": "capabilities.creative.game_manager",
    
    # === capabilities/ (top-level) ===
    "executor": "capabilities.executor",
    "function_registry": "capabilities.function_registry",
    "function_validation": "capabilities.function_validation",
}

def rewrite_imports_in_file(filepath):
    """Rewrite imports in a single file using MIGRATION_MAP."""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    original = content
    changes = []
    
    for old_module, new_path in MIGRATION_MAP.items():
        # Pattern 1: "from core.old_module import X"
        pattern1 = rf'from core\.{re.escape(old_module)} import'
        replacement1 = f'from {new_path} import'
        if re.search(pattern1, content):
            content = re.sub(pattern1, replacement1, content)
            changes.append(f"  core.{old_module} -> {new_path}")
        
        # Pattern 2: "from .old_module import X" (relative imports)
        pattern2 = rf'from \.{re.escape(old_module)} import'
        replacement2 = f'from {new_path} import'
        if re.search(pattern2, content):
            content = re.sub(pattern2, replacement2, content)
            changes.append(f"  .{old_module} -> {new_path}")
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return changes
    return []

def scan_and_rewrite(directory, skip_dirs=None):
    """Scan all .py files and rewrite imports."""
    skip_dirs = skip_dirs or {'.venv', '__pycache__', '.git', 'backups', 'build', 'dist'}
    
    total_changes = 0
    for root, dirs, files in os.walk(directory):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for fname in files:
            if not fname.endswith('.py'):
                continue
            
            filepath = os.path.join(root, fname)
            rel_path = os.path.relpath(filepath, directory)
            
            changes = rewrite_imports_in_file(filepath)
            if changes:
                print(f"✅ {rel_path}:")
                for c in changes:
                    print(c)
                total_changes += len(changes)
    
    return total_changes

if __name__ == '__main__':
    print("=" * 60)
    print("NEXA Import Migration")
    print("=" * 60)
    print()
    
    n = scan_and_rewrite(BASE)
    
    print()
    print(f"Total import rewrites: {n}")
    print("Done!")
