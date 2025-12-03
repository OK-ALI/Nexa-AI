"""
Nexa AI Assistant - Build Script
Creates distributable Windows application using PyInstaller.

Usage:
    python build_nexa.py          # Standard build
    python build_nexa.py --debug  # Debug build with console window
    python build_nexa.py --clean  # Clean build (removes previous artifacts)

Author: Ali Adil Waseem
Date: December 1, 2025
"""

import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
SPEC_FILE = PROJECT_ROOT / "nexa_build.spec"

def clean_build():
    """Remove previous build artifacts."""
    print("🧹 Cleaning previous build artifacts...")
    
    # Remove dist folder
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
        print(f"  ✓ Removed {DIST_DIR}")
    
    # Remove build folder
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
        print(f"  ✓ Removed {BUILD_DIR}")
    
    # Remove PyInstaller cache
    cache_dir = PROJECT_ROOT / "__pycache__"
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
        print(f"  ✓ Removed {cache_dir}")
    
    print("✅ Clean complete!")

def verify_dependencies():
    """Verify all required dependencies are installed."""
    print("🔍 Verifying dependencies...")
    
    required = [
        'PyInstaller',  # Capital letters for import
        'PySide6',
        'faster_whisper',
        'kokoro_onnx',
        'espeakng_loader',
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✓ {package.lower()}")
        except ImportError:
            print(f"  ✗ {package.lower()} NOT FOUND")
            missing.append(package.lower())
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("Install with: pip install " + " ".join(missing))
        return False
    
    print("✅ All dependencies verified!")
    return True

def verify_data_files():
    """Verify all required data files exist."""
    print("🔍 Verifying data files...")
    
    required_files = [
        PROJECT_ROOT / "assets" / "icon.ico",
        PROJECT_ROOT / "voice" / "kokoro_models" / "kokoro-v1.0.onnx",
        PROJECT_ROOT / "voice" / "kokoro_models" / "voices-v1.0.bin",
        PROJECT_ROOT / "Themes" / "themes.json",
        PROJECT_ROOT / "config" / "ui_preferences.json",
    ]
    
    missing = []
    for filepath in required_files:
        if filepath.exists():
            print(f"  ✓ {filepath.relative_to(PROJECT_ROOT)}")
        else:
            print(f"  ✗ {filepath.relative_to(PROJECT_ROOT)} NOT FOUND")
            missing.append(filepath)
    
    # Check espeak-ng data
    try:
        import espeakng_loader
        espeak_data = Path(espeakng_loader.get_data_path())
        if espeak_data.exists():
            print(f"  ✓ espeak-ng-data: {espeak_data}")
        else:
            print(f"  ✗ espeak-ng-data NOT FOUND at {espeak_data}")
            missing.append(espeak_data)
    except ImportError:
        print("  ✗ espeakng_loader not installed")
        missing.append("espeakng_loader")
    
    if missing:
        print(f"\n❌ Missing files: {len(missing)} files not found")
        return False
    
    print("✅ All data files verified!")
    return True

def build_application(debug=False):
    """Build the application using PyInstaller."""
    print("\n🔨 Building Nexa AI Assistant...")
    print(f"  Mode: {'Debug (with console)' if debug else 'Release (no console)'}")
    
    # Modify spec file for debug mode if needed
    if debug:
        # Read spec file
        spec_content = SPEC_FILE.read_text()
        # Temporarily enable console
        spec_content = spec_content.replace("console=False", "console=True")
        debug_spec = PROJECT_ROOT / "nexa_build_debug.spec"
        debug_spec.write_text(spec_content)
        spec_to_use = debug_spec
    else:
        spec_to_use = SPEC_FILE
    
    # Run PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        str(spec_to_use)
    ]
    
    print(f"  Command: {' '.join(cmd)}")
    print("-" * 60)
    
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    
    # Clean up debug spec if created
    if debug:
        debug_spec.unlink(missing_ok=True)
    
    if result.returncode != 0:
        print("\n❌ Build failed!")
        return False
    
    print("\n✅ Build successful!")
    
    # Print output location
    output_dir = DIST_DIR / "Nexa AI"
    if output_dir.exists():
        exe_file = output_dir / "Nexa AI.exe"
        if exe_file.exists():
            size_mb = exe_file.stat().st_size / (1024 * 1024)
            print(f"\n📦 Output: {output_dir}")
            print(f"   Executable: {exe_file}")
            print(f"   Size: {size_mb:.1f} MB")
    
    return True

def test_build():
    """Run a quick test of the built application."""
    print("\n🧪 Testing build...")
    
    exe_file = DIST_DIR / "Nexa AI" / "Nexa AI.exe"
    if not exe_file.exists():
        print(f"❌ Executable not found: {exe_file}")
        return False
    
    print(f"  Launching: {exe_file}")
    print("  (Check if application starts without errors)")
    
    # Run with console to see any errors
    result = subprocess.run([str(exe_file)], timeout=30, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"\n❌ Application exited with error code: {result.returncode}")
        if result.stderr:
            print(f"Stderr: {result.stderr[:500]}")
        return False
    
    print("✅ Test passed!")
    return True

def main():
    parser = argparse.ArgumentParser(description="Build Nexa AI Assistant")
    parser.add_argument("--debug", action="store_true", help="Build with console window for debugging")
    parser.add_argument("--clean", action="store_true", help="Clean previous build artifacts")
    parser.add_argument("--skip-verify", action="store_true", help="Skip dependency verification")
    parser.add_argument("--test", action="store_true", help="Test build after completion")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  NEXA AI ASSISTANT - BUILD SYSTEM")
    print("=" * 60)
    
    # Clean if requested
    if args.clean:
        clean_build()
    
    # Verify dependencies
    if not args.skip_verify:
        if not verify_dependencies():
            sys.exit(1)
        if not verify_data_files():
            sys.exit(1)
    
    # Build
    if not build_application(debug=args.debug):
        sys.exit(1)
    
    # Test if requested
    if args.test:
        test_build()
    
    print("\n" + "=" * 60)
    print("  BUILD COMPLETE!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Test the build: dist\\Nexa AI\\Nexa AI.exe")
    print("  2. Create installer with Inno Setup using setup.iss")
    print("  3. Distribute the installer to users")

if __name__ == "__main__":
    main()
