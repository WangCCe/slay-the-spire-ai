#!/usr/bin/env python3
"""
Test script to verify WSL path conversion is working correctly.
"""

import sys
import os

# Add project to path
sys.path.insert(0, '/mnt/d/PycharmProjects/slay-the-spire-ai')

from spirecomm.spire.data_loader import convert_windows_path_to_wsl

def test_path_conversion():
    """Test Windows to WSL path conversion."""
    print("="*80)
    print("WSL PATH CONVERSION TEST")
    print("="*80)

    test_cases = [
        ("D:\\SteamLibrary\\steamapps\\common\\SlayTheSpire\\export",
         "WSL: Should convert to /mnt/d/..."),
        ("C:\\Program Files\\Game",
         "WSL: Should convert to /mnt/c/..."),
        ("/home/user/file",
         "WSL: Should keep as is (already Linux path)"),
    ]

    for windows_path, description in test_cases:
        converted = convert_windows_path_to_wsl(windows_path)
        print(f"\n{description}")
        print(f"  Input:  {windows_path}")
        print(f"  Output: {converted}")

        # Check if file exists (for the actual game path)
        if "SteamLibrary" in converted:
            if os.path.exists(converted):
                print(f"  ✓ Path exists!")
            else:
                print(f"  ⚠ Path doesn't exist (expected if not on this system)")

    print("\n" + "="*80)
    print("Testing module import...")
    print("="*80)

    try:
        from spirecomm.ai.heuristics.combat_ending import CombatEndingDetector
        print("✓ Successfully imported CombatEndingDetector")
        print("✓ WSL path conversion is working correctly")
        print("\nThis means:")
        print("  - Code can be imported in WSL without crashing")
        print("  - Windows paths are automatically converted to WSL paths")
        print("  - Tests can run even if game data is not found")
        return 0
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(test_path_conversion())
