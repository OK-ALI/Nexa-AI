"""
Phase 16: System Control Expansion - Test Suite
Tests all system control functions via the new SystemControl module.

Run with: python tests/test_phase16.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from capabilities.system.system_control import SystemControl


def test_safe_functions():
    """Test functions that don't change system state."""
    print("=" * 60)
    print("PHASE 16 TEST SUITE - SAFE FUNCTIONS")
    print("=" * 60)
    print()
    
    sc = SystemControl()
    
    # Test 1: Get Power Plan
    print("📋 TEST 1: get_power_plan()")
    print("-" * 40)
    result = sc.get_power_plan()
    print(f"Result: {result}")
    print()
    
    # Test 2: List Power Plans
    print("📋 TEST 2: list_power_plans()")
    print("-" * 40)
    result = sc.list_power_plans()
    print(f"Result:\n{result}")
    print()
    
    # Test 3: Get Bluetooth Status
    print("📋 TEST 3: get_bluetooth_status()")
    print("-" * 40)
    result = sc.get_bluetooth_status()
    print(f"Result:\n{result}")
    print()
    
    # Test 4: List Bluetooth Devices
    print("📋 TEST 4: list_bluetooth_devices()")
    print("-" * 40)
    result = sc.list_bluetooth_devices()
    print(f"Result:\n{result}")
    print()
    
    print("=" * 60)
    print("✅ SAFE TESTS COMPLETE")
    print("=" * 60)


def test_quick_settings():
    """Test quick settings functions (opens Windows settings)."""
    print()
    print("=" * 60)
    print("QUICK SETTINGS TESTS (opens Windows settings)")
    print("=" * 60)
    
    sc = SystemControl()
    
    tests = [
        ("Bluetooth Settings", sc.open_bluetooth_settings),
        ("Night Light", sc.toggle_night_light),
        ("Airplane Mode", sc.toggle_airplane_mode),
        ("Windows Update", sc.check_windows_update),
        ("Focus Assist", sc.open_focus_assist),
        ("Accessibility", sc.open_accessibility_settings),
        ("Display/Project", sc.open_display_project),
        ("Cast Settings", sc.open_cast_settings),
        ("Nearby Share", sc.open_nearby_share),
        ("Battery Saver", sc.enable_battery_saver),
    ]
    
    for name, func in tests:
        response = input(f"\nOpen {name}? (y/n/q to quit): ")
        if response.lower() == 'q':
            break
        if response.lower() == 'y':
            result = func()
            print(f"  Result: {result}")


def test_dangerous_functions():
    """Test functions that actually change system state."""
    print()
    print("=" * 60)
    print("⚠️ DANGEROUS TESTS (will perform actions)")
    print("=" * 60)
    
    sc = SystemControl()
    
    # Power Plan Test
    print("\n1. SET POWER PLAN")
    response = input("   Change power plan to 'balanced'? (y/n): ")
    if response.lower() == 'y':
        result = sc.set_power_plan("balanced")
        print(f"   Result: {result}")
        input("   Press Enter to check current plan...")
        print(f"   Current: {sc.get_power_plan()}")
    
    # Schedule Restart Test (NEW)
    print("\n2. SCHEDULE RESTART")
    response = input("   Schedule restart in 1 minute (can cancel)? (y/n): ")
    if response.lower() == 'y':
        result = sc.schedule_restart(1)
        print(f"   Result: {result}")
        response2 = input("   Cancel it now? (y/n): ")
        if response2.lower() == 'y':
            result = sc.cancel_shutdown()
            print(f"   Cancel result: {result}")
    
    # Lock Screen Test
    print("\n3. LOCK SCREEN")
    response = input("   Lock your screen? (y/n): ")
    if response.lower() == 'y':
        result = sc.lock_screen()
        print(f"   Result: {result}")
    
    print()
    print("=" * 60)
    print("✅ TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║         PHASE 16: SYSTEM CONTROL - TEST SUITE              ║")
    print("╠════════════════════════════════════════════════════════════╣")
    print("║  Functions: 22 total (via SystemControl module)            ║")
    print("║  - System Power: 8 (lock, sleep, hibernate, restart, etc.) ║")
    print("║  - Power Plans: 3 (get, list, set)                         ║")
    print("║  - Battery Saver: 2 (enable, disable)                      ║")
    print("║  - Bluetooth: 3 (status, devices, settings)                ║")
    print("║  - Quick Settings: 6 (airplane, night light, update, etc.) ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()
    
    # Always run safe tests
    test_safe_functions()
    
    # Ask about quick settings tests
    print()
    response = input("Run quick settings tests (opens Windows settings)? (y/n): ")
    if response.lower() == 'y':
        test_quick_settings()
    
    # Ask about dangerous tests
    print()
    response = input("Run dangerous tests (changes system state)? (y/n): ")
    if response.lower() == 'y':
        test_dangerous_functions()
    else:
        print("\n⚠️ Skipped dangerous tests. Run manually with caution.")
    
    print()
    print("Test suite complete!")
