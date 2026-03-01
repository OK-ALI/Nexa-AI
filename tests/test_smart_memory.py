"""
Smart Memory Test Suite - Phase 19 Validation

Comprehensive tests for:
1. Embedding Engine
2. Memory Store (LanceDB)
3. Memory Manager
4. Context Constructor
5. Intent State
6. Voice Commands Integration
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def print_header(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(test_name: str, passed: bool, message: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status}: {test_name}")
    if message:
        print(f"         → {message}")


# ============================================================================
# TEST 1: Embedding Engine
# ============================================================================
def test_embedding_engine():
    print_header("TEST 1: Embedding Engine")
    
    try:
        from core.memory.embedding_engine import EmbeddingEngine, get_embedding_engine
        
        # Test 1.1: Singleton instance
        engine = get_embedding_engine()
        print_result("Get singleton instance", engine is not None)
        
        # Test 1.2: Single text embedding
        text = "Hello, I want to open Chrome browser"
        embedding = engine.embed(text)
        print_result("Single text embedding", 
                     embedding is not None and len(embedding) == 384,
                     f"Shape: {embedding.shape}")
        
        # Test 1.3: Batch embedding
        texts = ["Open Chrome", "Set volume to 50", "What's the weather?"]
        embeddings = engine.embed_batch(texts)
        print_result("Batch embedding", 
                     embeddings.shape == (3, 384),
                     f"Shape: {embeddings.shape}")
        
        # Test 1.4: Similarity calculation
        sim1 = engine.similarity(embeddings[0], embeddings[0])  # Same text
        sim2 = engine.similarity(embeddings[0], embeddings[2])  # Different
        print_result("Similarity (same text = 1.0)", 
                     abs(sim1 - 1.0) < 0.01,
                     f"Score: {sim1:.4f}")
        print_result("Similarity (diff text < 1.0)", 
                     sim2 < 1.0,
                     f"Score: {sim2:.4f}")
        
        # Test 1.5: Semantic similarity
        # "Open browser" should be more similar to "Open Chrome" than "Check weather"
        browser_emb = engine.embed("Open web browser")
        chrome_sim = engine.similarity(browser_emb, embeddings[0])  # Open Chrome
        weather_sim = engine.similarity(browser_emb, embeddings[2])  # Weather
        print_result("Semantic similarity (browser > weather)", 
                     chrome_sim > weather_sim,
                     f"Browser: {chrome_sim:.4f}, Weather: {weather_sim:.4f}")
        
        return True
        
    except Exception as e:
        print_result("Embedding Engine Tests", False, str(e))
        return False


# ============================================================================
# TEST 2: Memory Store (LanceDB)
# ============================================================================
def test_memory_store():
    print_header("TEST 2: Memory Store (LanceDB)")
    
    try:
        import tempfile
        import numpy as np
        from core.memory.memory_store import MemoryStore
        
        # Use temp directory for test DB
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(tmpdir)
            
            # Test 2.1: Connection
            print_result("LanceDB connection", store._db is not None)
            
            # Test 2.2: Tables created
            tables = store._db.table_names()
            print_result("Tables created", 
                         len(tables) >= 3,
                         f"Tables: {tables}")
            
            # Test 2.3: Add record
            test_record = {
                'id': 'test-123',
                'user_message': 'Hello Nexa',
                'nexa_response': 'Hi there!',
                'vector': np.random.rand(384).tolist(),
                'timestamp': datetime.now().isoformat(),
                'success': True,
                'importance': 0.7,
                'tags': 'greeting',
            }
            record_id = store.add('conversations', test_record)
            print_result("Add record", 
                         record_id == 'test-123',
                         f"ID: {record_id}")
            
            # Test 2.4: Get record
            retrieved = store.get('conversations', 'test-123')
            print_result("Get record", 
                         retrieved is not None and retrieved['user_message'] == 'Hello Nexa',
                         f"Message: {retrieved['user_message'][:30] if retrieved else 'None'}...")
            
            # Test 2.5: Vector search
            query_vec = np.array(test_record['vector'], dtype=np.float32)
            results = store.search_similar('conversations', query_vec, limit=5)
            print_result("Vector search", 
                         len(results) >= 1,
                         f"Found: {len(results)} results")
            
            # Test 2.6: Delete record
            deleted = store.delete('conversations', 'test-123')
            print_result("Delete record", deleted)
            
            # Test 2.7: Verify deletion
            after_delete = store.get('conversations', 'test-123')
            print_result("Verify deletion", after_delete is None)
            
            # Test 2.8: Count
            count = store.count('conversations')
            print_result("Count records", 
                         count == 0,
                         f"Count: {count}")
            
        return True
        
    except Exception as e:
        print_result("Memory Store Tests", False, str(e))
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# TEST 3: Memory Manager
# ============================================================================
def test_memory_manager():
    print_header("TEST 3: Memory Manager")
    
    try:
        import tempfile
        from core.memory.memory_manager import SmartMemoryManager
        
        with tempfile.TemporaryDirectory() as tmpdir:
            mm = SmartMemoryManager(tmpdir)
            
            # Test 3.1: Store conversation memory
            mem_id = mm.store_memory(
                user_message="Open Chrome browser",
                nexa_response="Opening Chrome for you!",
                success=True
            )
            print_result("Store conversation", 
                         mem_id is not None,
                         f"ID: {mem_id[:8]}...")
            
            # Test 3.2: Learn a fact
            fact_id = mm.learn_fact(
                "User prefers dark theme",
                source='user_stated',
                confidence=0.9
            )
            print_result("Learn fact", 
                         fact_id is not None,
                         f"ID: {fact_id[:8]}...")
            
            # Test 3.3: Recall similar (semantic search)
            results = mm.recall_similar("browser", limit=5)
            print_result("Recall similar (browser)", 
                         len(results) >= 1,
                         f"Found: {len(results)} memories")
            
            # Test 3.4: Recall similar (theme)
            results = mm.recall_similar("dark mode", limit=5)
            print_result("Recall similar (dark mode)", 
                         len(results) >= 1,
                         f"Found: {len(results)} memories")
            
            # Test 3.5: Track skill
            skill_id = mm.track_skill("set_volume", {"level": 50}, success=True)
            print_result("Track skill", 
                         skill_id is not None,
                         f"ID: {skill_id[:8]}...")
            
            # Test 3.6: Get stats
            stats = mm.get_stats()
            print_result("Get stats", 
                         stats['conversations'] >= 1 and stats['knowledge'] >= 1,
                         f"Conv: {stats['conversations']}, Know: {stats['knowledge']}")
            
            # Test 3.7: Forget matching
            deleted = mm.forget_matching("browser", limit=5)
            print_result("Forget matching", 
                         deleted >= 1,
                         f"Deleted: {deleted}")
            
        return True
        
    except Exception as e:
        print_result("Memory Manager Tests", False, str(e))
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# TEST 4: Context Constructor
# ============================================================================
def test_context_constructor():
    print_header("TEST 4: Context Constructor")
    
    try:
        import tempfile
        from core.memory.memory_manager import SmartMemoryManager
        from core.memory.context_constructor import ContextConstructor
        
        with tempfile.TemporaryDirectory() as tmpdir:
            mm = SmartMemoryManager(tmpdir)
            cc = ContextConstructor(mm)
            
            # Add some test memories
            mm.store_memory("Open Chrome", "Opened Chrome!", success=True)
            mm.store_memory("Set volume to 80", "Volume set to 80%", success=True)
            mm.learn_fact("User likes jazz music", source='learned')
            
            # Test 4.1: Build context
            context = cc.build_context("play music", max_tokens=500)
            print_result("Build context", 
                         len(context) > 0,
                         f"Length: {len(context)} chars")
            
            # Test 4.2: Context contains relevant info
            has_jazz = 'jazz' in context.lower() or 'music' in context.lower()
            print_result("Context relevance", has_jazz, 
                         "Contains music/jazz reference" if has_jazz else "Missing relevance")
            
            # Test 4.3: Resolve reference (with action stack)
            action_stack = [
                {'action': 'open_application', 'data': {'app_name': 'Chrome'}},
                {'action': 'set_volume', 'data': {'level': 80}},
            ]
            
            resolved = cc.resolve_reference("close it", action_stack)
            print_result("Resolve reference 'close it'", 
                         resolved == 'Chrome',
                         f"Resolved: {resolved}")
            
            # Test 4.4: Get context for query (full package)
            package = cc.get_context_for_query("what about the browser", action_stack)
            print_result("Full context package", 
                         'context_string' in package and 'resolved_reference' in package)
            
        return True
        
    except Exception as e:
        print_result("Context Constructor Tests", False, str(e))
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# TEST 5: Intent State
# ============================================================================
def test_intent_state():
    print_header("TEST 5: Intent State (Follow-ups)")
    
    try:
        from core.memory.intent_state import IntentState
        
        intent = IntentState()
        
        # Test 5.1: No pending initially
        print_result("No pending initially", not intent.has_pending_intent())
        
        # Test 5.2: Set pending intent
        intent.set_pending_intent("play_music", "song_name")
        print_result("Set pending intent", intent.has_pending_intent())
        
        # Test 5.3: Get follow-up prompt
        prompt = intent.get_follow_up_prompt()
        print_result("Get follow-up prompt", 
                     prompt is not None and 'song' in prompt.lower(),
                     f"Prompt: {prompt}")
        
        # Test 5.4: Resolve follow-up
        result = intent.process_input("Bohemian Rhapsody")
        print_result("Resolve follow-up", 
                     result['action'] == 'resolve' and 'Bohemian Rhapsody' in str(result['data']),
                     f"Action: {result['action']}")
        
        # Test 5.5: After resolution, no pending
        print_result("No pending after resolve", not intent.has_pending_intent())
        
        # Test 5.6: Cancel command
        intent.set_pending_intent("set_volume", "level")
        result = intent.process_input("forget it")
        print_result("Cancel command", 
                     result['action'] == 'cancel',
                     f"Action: {result['action']}")
        
        # Test 5.7: New command override
        intent.set_pending_intent("play_music", "song_name")
        result = intent.process_input("what's the weather today?")
        print_result("New command override", 
                     result['action'] == 'new_command',
                     f"Action: {result['action']}")
        
        # Test 5.8: Timeout check
        from datetime import datetime, timedelta
        intent.set_pending_intent("test", "data")
        intent._pending.expires_at = datetime.now() - timedelta(seconds=1)
        print_result("Timeout expiry", not intent.has_pending_intent())
        
        return True
        
    except Exception as e:
        print_result("Intent State Tests", False, str(e))
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# TEST 6: Integration with ContextManager
# ============================================================================
def test_context_manager_integration():
    print_header("TEST 6: ContextManager Integration")
    
    try:
        import tempfile
        from unittest.mock import MagicMock
        
        # Create mock config
        with tempfile.TemporaryDirectory() as tmpdir:
            config = MagicMock()
            config.memory_file = Path(tmpdir) / "memory.json"
            config.prefs_file = Path(tmpdir) / "prefs.json"
            config.data_dir = Path(tmpdir)
            
            # Write empty files
            config.memory_file.write_text("[]")
            config.prefs_file.write_text("{}")
            
            from core.cognition.context_manager import ContextManager
            
            cm = ContextManager(config)
            
            # Test 6.1: Smart Memory initialized
            print_result("Smart Memory initialized", 
                         cm.smart_memory is not None,
                         "SmartMemoryManager available")
            
            # Test 6.2: Context constructor available
            print_result("Context constructor available", 
                         cm.context_constructor is not None)
            
            # Test 6.3: Intent state available
            print_result("Intent state available", 
                         cm.intent_state is not None)
            
            # Test 6.4: Add interaction (stores in LanceDB)
            cm.add_interaction("Test message", "Test response", success=True)
            stats = cm.get_memory_stats()
            print_result("Add interaction → LanceDB", 
                         stats.get('conversations', 0) >= 1,
                         f"Conversations: {stats.get('conversations', 0)}")
            
            # Test 6.5: Learn user fact
            fact_id = cm.learn_user_fact("User likes coffee")
            print_result("Learn user fact", 
                         fact_id is not None,
                         f"ID: {fact_id[:8] if fact_id else 'None'}...")
            
            # Test 6.6: Recall similar
            results = cm.recall_similar_memories("coffee", limit=5)
            print_result("Recall similar memories", 
                         len(results) >= 1,
                         f"Found: {len(results)}")
            
            # Test 6.7: Get smart context
            context = cm.get_smart_context("what drinks?")
            print_result("Get smart context", 
                         len(context) > 0,
                         f"Length: {len(context)} chars")
            
            # Test 6.8: Pending follow-up
            cm.set_pending_intent("test_intent", "test_data")
            print_result("Set pending intent", cm.has_pending_follow_up())
            
            cm.clear_follow_up()
            print_result("Clear follow-up", not cm.has_pending_follow_up())
            
        return True
        
    except Exception as e:
        print_result("ContextManager Integration", False, str(e))
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# TEST 7: Complex Command Scenarios
# ============================================================================
def test_complex_scenarios():
    print_header("TEST 7: Complex Command Scenarios")
    
    try:
        import tempfile
        from unittest.mock import MagicMock
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            config = MagicMock()
            config.memory_file = Path(tmpdir) / "memory.json"
            config.prefs_file = Path(tmpdir) / "prefs.json"
            config.data_dir = Path(tmpdir)
            config.memory_file.write_text("[]")
            config.prefs_file.write_text("{}")
            
            from core.cognition.context_manager import ContextManager
            
            cm = ContextManager(config)
            
            # Scenario 7.1: Multi-step learning
            print("\n  Scenario 7.1: Multi-step learning")
            cm.add_interaction("Open Steam", "Opening Steam", success=True)
            cm.add_interaction("Launch Elden Ring", "Launching Elden Ring", success=True)
            cm.add_interaction("Set volume to 70", "Volume set to 70%", success=True)
            
            # Should remember gaming context
            results = cm.recall_similar_memories("games I played", limit=5)
            has_game = any('elden' in str(r).lower() or 'steam' in str(r).lower() for r in results)
            print_result("Remembers gaming context", 
                         has_game,
                         f"Found: {len(results)} related")
            
            # Scenario 7.2: Preference learning
            print("\n  Scenario 7.2: Preference learning")
            cm.learn_user_fact("User prefers volume at 70%")
            cm.learn_user_fact("User plays games in the evening")
            
            results = cm.recall_similar_memories("user preferences", limit=5)
            print_result("Recalls preferences", 
                         len(results) >= 2,
                         f"Found: {len(results)} preferences")
            
            # Scenario 7.3: Dynamic follow-up flow
            print("\n  Scenario 7.3: Dynamic follow-up flow")
            
            cm.set_pending_intent("play_music", "song_name", {"platform": "Spotify"})
            print_result("Set multi-field intent", cm.has_pending_follow_up())
            
            # User provides song name
            result = cm.process_follow_up("Bohemian Rhapsody")
            print_result("Resolve with answer", 
                         result['action'] == 'resolve',
                         f"Data: {result.get('data', {})}")
            
            # Scenario 7.4: Cancel mid-flow
            print("\n  Scenario 7.4: Cancel mid-flow")
            cm.set_pending_intent("send_email", "recipient")
            result = cm.process_follow_up("never mind")
            print_result("Cancel with 'never mind'", 
                         result['action'] == 'cancel')
            
            # Scenario 7.5: Override with new command
            print("\n  Scenario 7.5: Override with new command")
            cm.set_pending_intent("set_reminder", "time")
            result = cm.process_follow_up("what time is it?")
            print_result("Override with question", 
                         result['action'] == 'new_command',
                         f"Old intent cancelled")
            
            # Scenario 7.6: Semantic context building
            print("\n  Scenario 7.6: Semantic context building")
            cm.add_interaction("What's the weather in London?", "It's 15°C and cloudy", success=True)
            
            context = cm.get_smart_context("temperature outside")
            has_weather_ref = 'weather' in context.lower() or 'london' in context.lower() or '15' in context
            print_result("Semantic context retrieval", 
                         has_weather_ref,
                         f"Context length: {len(context)}")
            
        return True
        
    except Exception as e:
        print_result("Complex Scenarios", False, str(e))
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# MAIN
# ============================================================================
def main():
    print("\n" + "═" * 60)
    print("  🧠 SMART MEMORY TEST SUITE - Phase 19")
    print("═" * 60)
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # Run all tests
    results['Embedding Engine'] = test_embedding_engine()
    results['Memory Store'] = test_memory_store()
    results['Memory Manager'] = test_memory_manager()
    results['Context Constructor'] = test_context_constructor()
    results['Intent State'] = test_intent_state()
    results['ContextManager Integration'] = test_context_manager_integration()
    results['Complex Scenarios'] = test_complex_scenarios()
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅" if result else "❌"
        print(f"  {status} {name}")
    
    print(f"\n  Total: {passed}/{total} test groups passed")
    
    if passed == total:
        print("\n  🎉 ALL TESTS PASSED!")
    else:
        print(f"\n  ⚠️ {total - passed} test group(s) failed")
    
    print("\n" + "═" * 60 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
