#!/usr/bin/env python3
"""
Test runner for Daisy Assistant 0.6
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import test modules
import importlib.util

def run_test_module(module_name):
    """Run all tests in a module"""
    print(f"\n{'='*60}")
    print(f"Running {module_name}...")
    print('='*60)
    
    try:
        # Import the module
        spec = importlib.util.spec_from_file_location(
            module_name,
            Path(__file__).parent / f"{module_name}.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find all test functions
        test_functions = [
            name for name in dir(module)
            if name.startswith('test_') and callable(getattr(module, name))
        ]
        
        passed = 0
        failed = 0
        
        for test_name in test_functions:
            test_func = getattr(module, test_name)
            try:
                test_func()
                print(f"  ✅ {test_name}")
                passed += 1
            except AssertionError as e:
                print(f"  ❌ {test_name}: {e}")
                failed += 1
            except Exception as e:
                print(f"  ❌ {test_name}: {type(e).__name__}: {e}")
                failed += 1
        
        return passed, failed
    
    except Exception as e:
        print(f"  ❌ Failed to load module: {e}")
        return 0, 1


def main():
    """Run all tests"""
    print("🧪 Daisy Assistant 0.6 - Test Suite")
    print("="*60)
    
    test_modules = [
        "test_schemas",
        "test_config",
        "test_safety",
        "test_action_service",
        "test_brain_service",
        "test_persistence",
    ]
    
    total_passed = 0
    total_failed = 0
    
    for module in test_modules:
        passed, failed = run_test_module(module)
        total_passed += passed
        total_failed += failed
    
    print(f"\n{'='*60}")
    print("📊 Test Results")
    print('='*60)
    print(f"✅ Passed: {total_passed}")
    print(f"❌ Failed: {total_failed}")
    print(f"📈 Total:  {total_passed + total_failed}")
    
    if total_failed == 0:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total_failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())



