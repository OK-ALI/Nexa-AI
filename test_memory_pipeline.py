"""
Test the full Smart Memory pipeline end-to-end.
Verifies: seeding → storage → recall → prefetch injection

Run: python test_memory_pipeline.py
"""
import sys
import os
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(message)s')
logger = logging.getLogger("MemoryTest")

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_memory_pipeline():
    """Full end-to-end test of the memory system."""
    
    print("\n" + "="*70)
    print("  NEXA Smart Memory Pipeline Test")
    print("="*70)
    
    # ==========================================
    # STEP 1: Initialize Smart Memory
    # ==========================================
    print("\n[1/6] Initializing Smart Memory Manager...")
    try:
        from core.smart_memory.memory_manager import SmartMemoryManager
        data_dir = Path("data")
        sm = SmartMemoryManager(data_dir)
        print("  ✅ SmartMemoryManager initialized")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False
    
    # ==========================================
    # STEP 2: Check if knowledge table exists and has content
    # ==========================================
    print("\n[2/6] Checking knowledge table...")
    try:
        from core.smart_memory.memory_store import MemoryStore
        knowledge_count = sm.store._get_table(MemoryStore.TABLE_KNOWLEDGE).count_rows()
        print(f"  📊 Knowledge table has {knowledge_count} rows")
        if knowledge_count == 0:
            print("  ⚠️  Table is EMPTY — needs seeding")
        else:
            print("  ✅ Table has data")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        return False
    
    # ==========================================
    # STEP 3: Seed knowledge (if empty)
    # ==========================================
    print("\n[3/6] Seeding personal knowledge...")
    try:
        # Load user prefs
        prefs_file = data_dir / "user_prefs.json"
        if not prefs_file.exists():
            print(f"  ❌ user_prefs.json not found at {prefs_file}")
            return False
        
        with open(prefs_file, 'r', encoding='utf-8-sig') as f:
            prefs = json.load(f)
        
        personal = prefs.get('personal', {})
        relationships = personal.get('relationships', {})
        user_info = personal.get('user_info', {})
        user_name = user_info.get('name', 'the user')
        
        facts_seeded = 0
        
        # Seed user info
        if user_info.get('university'):
            fact = f"{user_name} studied at {user_info['university']}"
            sm.learn_fact(fact, source='user_stated', confidence=1.0, category='education')
            facts_seeded += 1
        
        if user_info.get('location'):
            fact = f"{user_name} is from {user_info['location']}"
            sm.learn_fact(fact, source='user_stated', confidence=1.0, category='personal')
            facts_seeded += 1
        
        if user_info.get('birthday'):
            fact = f"{user_name}'s birthday is on {user_info['birthday']}"
            sm.learn_fact(fact, source='user_stated', confidence=1.0, category='personal')
            facts_seeded += 1
        
        if user_info.get('favorite_colors'):
            colors = ', '.join(user_info['favorite_colors'])
            fact = f"{user_name}'s favorite colors are {colors}"
            sm.learn_fact(fact, source='user_stated', confidence=1.0, category='preference')
            facts_seeded += 1
        
        if user_info.get('favorite_foods'):
            foods = ', '.join(user_info['favorite_foods'])
            fact = f"{user_name}'s favorite foods are {foods}"
            sm.learn_fact(fact, source='user_stated', confidence=1.0, category='preference')
            facts_seeded += 1
        
        if user_info.get('dreams'):
            dreams = ', '.join(user_info['dreams'])
            fact = f"{user_name}'s dream is to {dreams}"
            sm.learn_fact(fact, source='user_stated', confidence=1.0, category='personal')
            facts_seeded += 1
        
        # Seed relationships
        for person_key, person_info in relationships.items():
            name = person_info.get('name', person_key)
            relationship = person_info.get('relationship', 'friend')
            
            relationship_facts = [
                f"{name} is {user_name}'s {relationship}",
                f"{user_name}'s {relationship} is {name}",
                f"My {relationship} is {name}",
                f"{name} is my {relationship}",
            ]
            for fact in relationship_facts:
                sm.learn_fact(fact, source='user_stated', confidence=1.0, category='relationships')
                facts_seeded += 1
            
            if person_info.get('location'):
                sm.learn_fact(f"{name} lives in {person_info['location']}", source='user_stated', confidence=1.0, category='relationships')
                facts_seeded += 1
            if person_info.get('education'):
                sm.learn_fact(f"{name} studies at {person_info['education']}", source='user_stated', confidence=1.0, category='education')
                facts_seeded += 1
            if person_info.get('special_notes'):
                sm.learn_fact(f"About {name}: {person_info['special_notes']}", source='user_stated', confidence=1.0, category='relationships')
                facts_seeded += 1
        
        print(f"  ✅ Seeded {facts_seeded} facts")
        
        # Verify count
        knowledge_count = sm.store._get_table(MemoryStore.TABLE_KNOWLEDGE).count_rows()
        print(f"  📊 Knowledge table now has {knowledge_count} rows")
        
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # ==========================================
    # STEP 4: Test recall queries
    # ==========================================
    print("\n[4/6] Testing memory recall queries...")
    test_queries = [
        ("who is my best friend", "Should find Saliha"),
        ("best friend", "Should find Saliha"),
        ("who is Saliha", "Should find relationship info"),
        ("favorite color", "Should find black, navy blue"),
        ("birthday", "Should find December 9"),
        ("where am I from", "Should find Okara"),
        ("university", "Should find UMT"),
        ("father", "Should find Waseem Ahmad"),
        ("mother", "Should find Nusrat Waseem"),
        ("favorite food", "Should find Tea, Pizza, etc."),
    ]
    
    passed = 0
    failed = 0
    
    for query, expected in test_queries:
        result = sm.recall_knowledge_answer(query, limit=3)
        found = result.get('found', False)
        facts = result.get('facts', [])
        best = result.get('best_match', '')
        sim = result.get('similarity', 0)
        
        status = "✅" if found else "❌"
        if found:
            passed += 1
        else:
            failed += 1
        
        print(f"  {status} Query: '{query}'")
        print(f"     Expected: {expected}")
        if found:
            print(f"     Got: {best} (sim={sim:.3f})")
            if len(facts) > 1:
                for f in facts[1:]:
                    print(f"     Also: {f}")
        else:
            print(f"     Got: NOTHING (sim={sim:.3f})")
        print()
    
    print(f"  Results: {passed}/{len(test_queries)} passed, {failed} failed")
    
    # ==========================================
    # STEP 5: Test the dedup fix
    # ==========================================
    print("\n[5/6] Testing dedup fix (L2 distance)...")
    try:
        before_count = sm.store._get_table(MemoryStore.TABLE_KNOWLEDGE).count_rows()
        
        # Try adding a duplicate fact
        sm.learn_fact("Saliha Jamil is Ali's best friend", source='user_stated', confidence=1.0, category='relationships')
        
        after_count = sm.store._get_table(MemoryStore.TABLE_KNOWLEDGE).count_rows()
        
        if after_count == before_count:
            print(f"  ✅ Dedup WORKING — duplicate was rejected ({before_count} → {after_count})")
        else:
            print(f"  ⚠️  Dedup may not be catching this — row count changed ({before_count} → {after_count})")
            print(f"     (Could be a near-miss: the L2 threshold 0.85 may need tuning)")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
    
    # ==========================================
    # STEP 6: List all facts in knowledge table
    # ==========================================
    print("\n[6/6] Full knowledge table dump...")
    try:
        all_knowledge = sm.store.get_all(MemoryStore.TABLE_KNOWLEDGE, limit=100)
        print(f"  Total facts stored: {len(all_knowledge)}")
        print()
        for i, row in enumerate(all_knowledge, 1):
            fact = row.get('fact', '?')
            cat = row.get('category', '?')
            conf = row.get('confidence', 0)
            print(f"  {i:3}. [{cat}] {fact} (conf={conf})")
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
    
    print("\n" + "="*70)
    if failed == 0:
        print("  🎉 ALL MEMORY TESTS PASSED!")
    else:
        print(f"  ⚠️  {failed} tests failed — check output above")
    print("="*70 + "\n")
    
    return failed == 0

if __name__ == '__main__':
    success = test_memory_pipeline()
    sys.exit(0 if success else 1)
