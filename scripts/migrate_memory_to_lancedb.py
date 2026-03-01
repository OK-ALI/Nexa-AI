"""
Memory Migration Script - memory.json → LanceDB

Migrates existing conversation history from legacy JSON format
to the new LanceDB vector database for Smart Memory.

Usage:
    python scripts/migrate_memory_to_lancedb.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    print("=" * 60)
    print("  Memory Migration: memory.json → LanceDB")
    print("=" * 60)
    
    # Paths
    data_dir = project_root / "data"
    memory_file = data_dir / "memory.json"
    
    if not memory_file.exists():
        print(f"\n❌ No memory.json found at: {memory_file}")
        print("   Nothing to migrate.")
        return
    
    # Load existing memory
    print(f"\n📁 Loading: {memory_file}")
    
    try:
        with open(memory_file, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading memory.json: {e}")
        return
    
    # Get history
    history = data.get('history', [])
    if not history:
        print("   No conversation history found.")
        return
    
    print(f"   Found {len(history)} conversations to migrate")
    
    # Initialize Smart Memory
    print("\n🧠 Initializing Smart Memory (LanceDB)...")
    
    try:
        from core.memory import SmartMemoryManager
        
        sm = SmartMemoryManager(data_dir)
        print("   ✅ Smart Memory initialized")
    except Exception as e:
        print(f"   ❌ Failed to initialize: {e}")
        return
    
    # Migrate each conversation
    print(f"\n📦 Migrating {len(history)} conversations...")
    
    migrated = 0
    skipped = 0
    errors = 0
    
    for i, conv in enumerate(history):
        user_msg = conv.get('user', '').strip()
        nexa_resp = conv.get('nexa', '').strip()
        timestamp = conv.get('timestamp', '')
        
        # Skip empty or very short messages
        if len(user_msg) < 3:
            skipped += 1
            continue
        
        try:
            # Store in LanceDB
            sm.store_memory(
                user_message=user_msg,
                nexa_response=nexa_resp,
                success=True  # Assume success for legacy data
            )
            migrated += 1
            
            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"   Migrated {i + 1}/{len(history)}...")
                
        except Exception as e:
            errors += 1
            if errors <= 5:  # Only show first 5 errors
                print(f"   ⚠️ Error migrating: {user_msg[:30]}... - {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("  Migration Complete!")
    print("=" * 60)
    print(f"   ✅ Migrated: {migrated}")
    print(f"   ⏭️ Skipped: {skipped}")
    print(f"   ❌ Errors: {errors}")
    
    # Backup old file
    backup_file = memory_file.with_suffix('.json.bak')
    print(f"\n📋 Creating backup: {backup_file}")
    
    try:
        import shutil
        shutil.copy(memory_file, backup_file)
        print("   ✅ Backup created")
    except Exception as e:
        print(f"   ⚠️ Backup failed: {e}")
    
    # Ask to delete old file
    print("\n💡 The old memory.json is no longer needed.")
    print("   LanceDB is now the primary storage.")
    print(f"   Backup saved at: {backup_file}")
    
    # Get stats
    stats = sm.get_stats()
    print(f"\n📊 LanceDB Stats:")
    print(f"   • Conversations: {stats.get('conversations', 0)}")
    print(f"   • Knowledge: {stats.get('knowledge', 0)}")
    print(f"   • Skills: {stats.get('skills', 0)}")
    
    print("\n✅ Migration complete! Smart Memory is ready.")


if __name__ == "__main__":
    main()
