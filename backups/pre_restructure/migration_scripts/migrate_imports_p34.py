"""
NEXA Import Migration - Phase 3+4 (Memory + Interface)
"""
import os
import re

BASE = r"d:\Projects\Nexa-MyAI"

MIGRATION_MAP = {
    # === Phase 3: Memory ===
    # "from .smart_memory.X" or "from core.smart_memory.X" -> "from core.memory.X"
    # Also handle "from .conversation_history" -> "from core.memory.conversation_memory"
    
    # === Phase 4: Interface ===
    # "from .listener" -> "from core.interface.voice_listener"
    # "from .tts " -> "from core.interface.tts_engine"
    # etc.
}

# More complex replacements need exact pattern matching
REPLACEMENTS = [
    # Memory layer
    (r'from \.smart_memory\.memory_manager import', 'from core.memory.memory_manager import'),
    (r'from \.smart_memory\.memory_store import', 'from core.memory.memory_store import'),
    (r'from \.smart_memory\.memory_types import', 'from core.memory.memory_types import'),
    (r'from \.smart_memory\.embedding_engine import', 'from core.memory.embedding_engine import'),
    (r'from \.smart_memory\.context_constructor import', 'from core.memory.context_constructor import'),
    (r'from \.smart_memory\.intelligent_learner import', 'from core.memory.intelligent_learner import'),
    (r'from \.smart_memory\.intent_state import', 'from core.memory.intent_state import'),
    (r'from \.smart_memory import', 'from core.memory import'),
    (r'from core\.smart_memory\.memory_manager import', 'from core.memory.memory_manager import'),
    (r'from core\.smart_memory\.memory_store import', 'from core.memory.memory_store import'),
    (r'from core\.smart_memory\.memory_types import', 'from core.memory.memory_types import'),
    (r'from core\.smart_memory\.embedding_engine import', 'from core.memory.embedding_engine import'),
    (r'from core\.smart_memory\.context_constructor import', 'from core.memory.context_constructor import'),
    (r'from core\.smart_memory\.intelligent_learner import', 'from core.memory.intelligent_learner import'),
    (r'from core\.smart_memory\.intent_state import', 'from core.memory.intent_state import'),
    (r'from core\.smart_memory import', 'from core.memory import'),
    
    # conversation_history -> conversation_memory
    (r'from \.conversation_history import', 'from core.memory.conversation_memory import'),
    (r'from core\.conversation_history import', 'from core.memory.conversation_memory import'),
    
    # Interface layer
    (r'from \.listener import', 'from core.interface.voice_listener import'),
    (r'from core\.listener import', 'from core.interface.voice_listener import'),
    (r'from \.tts import', 'from core.interface.tts_engine import'),
    (r'from core\.tts import', 'from core.interface.tts_engine import'),
    (r'from \.tts_coqui import', 'from core.interface.tts_coqui import'),
    (r'from core\.tts_coqui import', 'from core.interface.tts_coqui import'),
    (r'from \.speaker_verification import', 'from core.interface.speaker_verification import'),
    (r'from core\.speaker_verification import', 'from core.interface.speaker_verification import'),
    (r'from \.speaker_enrollment import', 'from core.interface.speaker_enrollment import'),
    (r'from core\.speaker_enrollment import', 'from core.interface.speaker_enrollment import'),
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
    print("Phase 3+4 Import Migration")
    print("=" * 50)
    n = scan_and_rewrite(BASE)
    print(f"\nTotal rewrites: {n}")
