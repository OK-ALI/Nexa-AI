"""
NEXA Import Migration - Phase 5+6 (Cognition + UI grouping)
"""
import os
import re

BASE = r"d:\Projects\Nexa-MyAI"

REPLACEMENTS = [
    # === Cognition layer (core.X -> core.cognition.X) ===
    (r'from \.context_manager import', 'from core.cognition.context_manager import'),
    (r'from core\.context_manager import', 'from core.cognition.context_manager import'),
    (r'from \.prompt_builder import', 'from core.cognition.prompt_builder import'),
    (r'from core\.prompt_builder import', 'from core.cognition.prompt_builder import'),
    (r'from \.clarification_handler import', 'from core.cognition.clarification_handler import'),
    (r'from core\.clarification_handler import', 'from core.cognition.clarification_handler import'),
    (r'from \.reference_resolver import', 'from core.cognition.reference_resolver import'),
    (r'from core\.reference_resolver import', 'from core.cognition.reference_resolver import'),
    (r'from \.text_processing import', 'from core.cognition.text_processing import'),
    (r'from core\.text_processing import', 'from core.cognition.text_processing import'),
    (r'from \.text_refiner import', 'from core.cognition.text_refiner import'),
    (r'from core\.text_refiner import', 'from core.cognition.text_refiner import'),
    (r'from \.natural_responses import', 'from core.cognition.natural_responses import'),
    (r'from core\.natural_responses import', 'from core.cognition.natural_responses import'),
    (r'from \.input_validator import', 'from core.cognition.input_validator import'),
    (r'from core\.input_validator import', 'from core.cognition.input_validator import'),
    (r'from \.response_cache import', 'from core.cognition.response_cache import'),
    (r'from core\.response_cache import', 'from core.cognition.response_cache import'),
    (r'from \.dynamic_preprocessor import', 'from core.cognition.dynamic_preprocessor import'),
    (r'from core\.dynamic_preprocessor import', 'from core.cognition.dynamic_preprocessor import'),
    (r'from \.command_detection import', 'from core.cognition.command_detection import'),
    (r'from core\.command_detection import', 'from core.cognition.command_detection import'),
    (r'from \.conditional_handler import', 'from core.cognition.conditional_handler import'),
    (r'from core\.conditional_handler import', 'from core.cognition.conditional_handler import'),
    
    # === UI Pet grouping (ui.pet_X -> ui.pet.pet_X) ===
    (r'from ui\.pet_config import', 'from ui.pet.pet_config import'),
    (r'from ui\.pet_idle_manager import', 'from ui.pet.pet_idle_manager import'),
    (r'from ui\.pet_personality import', 'from ui.pet.pet_personality import'),
    (r'from ui\.pet_quick_actions import', 'from ui.pet.pet_quick_actions import'),
    (r'from ui\.pet_radial_menu import', 'from ui.pet.pet_radial_menu import'),
    (r'from ui\.pet_settings_panel import', 'from ui.pet.pet_settings_panel import'),
    (r'from ui\.pet_speech_bubble import', 'from ui.pet.pet_speech_bubble import'),
    (r'from ui\.nexa_pet_widget import', 'from ui.pet.nexa_pet_widget import'),
    (r'from ui\.sprite_pet_widget import', 'from ui.pet.sprite_pet_widget import'),
    
    # === UI Widget grouping ===
    (r'from ui\.loading_dialog import', 'from ui.widgets.loading_dialog import'),
    (r'from ui\.status_widget import', 'from ui.widgets.status_widget import'),
    (r'from ui\.typing_animator import', 'from ui.widgets.typing_animator import'),
    (r'from ui\.web_orb_widget import', 'from ui.widgets.web_orb_widget import'),
    (r'from ui\.web_neural_graph import', 'from ui.widgets.web_neural_graph import'),
    (r'from ui\.nexa_orb_ui import', 'from ui.widgets.nexa_orb_ui import'),
    (r'from ui\.download_progress import', 'from ui.widgets.download_progress import'),
    (r'from ui\.live2d_widget import', 'from ui.widgets.live2d_widget import'),
    (r'from ui\.memory_detail_card import', 'from ui.widgets.memory_detail_card import'),
    (r'from ui\.content_box_formatter import', 'from ui.widgets.content_box_formatter import'),
]

def rewrite_file(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    original = content
    changes = []
    
    for pattern, replacement in REPLACEMENTS:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            changes.append(f"  {pattern} -> {replacement}")
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return changes
    return []

def scan_and_rewrite(directory):
    skip_dirs = {'.venv', '__pycache__', '.git', 'backups', 'build', 'dist'}
    total = 0
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in files:
            if not f.endswith('.py'):
                continue
            fp = os.path.join(root, f)
            rel = os.path.relpath(fp, directory)
            changes = rewrite_file(fp)
            if changes:
                print(f"✅ {rel}:")
                for c in changes:
                    print(c)
                total += len(changes)
    return total

if __name__ == '__main__':
    print("Phase 5+6 Import Migration (Cognition + UI)")
    print("=" * 50)
    n = scan_and_rewrite(BASE)
    print(f"\nTotal rewrites: {n}")
