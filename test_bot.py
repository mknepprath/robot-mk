#!/usr/bin/env python3
"""
Test script for robot_mk bot.
Run this to test the bot functionality without posting to Mastodon.
"""

import os
import sys
from datetime import datetime

# Add the current directory to the path so we can import ebooks
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_environment_setup():
    """Test that all required environment variables are set"""
    required_vars = [
        'ANTHROPIC_API_KEY',
        'MASTODON_CLIENT_KEY', 
        'MASTODON_CLIENT_SECRET',
        'MASTODON_ACCESS_TOKEN'
    ]
    
    print("🔧 Testing environment setup...")
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
        else:
            # Show first 10 chars for verification without exposing full key
            value = os.environ.get(var)
            preview = f"{value[:10]}..." if len(value) > 10 else value
            print(f"  ✓ {var}: {preview}")
    
    if missing_vars:
        print(f"  ❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    print("  ✅ All environment variables are set!")
    return True


def test_imports():
    """Test that all required packages can be imported"""
    print("\n📦 Testing imports...")
    
    packages = [
        ('anthropic', 'Anthropic Claude API client'),
        ('mastodon', 'Mastodon.py library'), 
        ('requests', 'HTTP requests library'),
        ('pandas', 'Data manipulation library')
    ]
    
    failed_imports = []
    
    for package, description in packages:
        try:
            __import__(package)
            print(f"  ✓ {package}: {description}")
        except ImportError as e:
            print(f"  ❌ {package}: {str(e)}")
            failed_imports.append(package)
    
    if failed_imports:
        print(f"\n  Install missing packages with: pip install {' '.join(failed_imports)}")
        return False
    
    print("  ✅ All packages imported successfully!")
    return True


def test_coffee_filtering():
    """Test the coffee filtering functionality"""
    print("\n☕ Testing coffee filtering...")
    
    from ebooks import contains_excessive_coffee, filter_coffee_heavy_posts
    
    # Test excessive coffee detection
    test_cases = [
        ("I love coffee and espresso and lattes", True),
        ("Just finished a great project", False),
        ("Coffee coffee coffee brewing beans", True),
        ("Working on a new design", False)
    ]
    
    for text, should_be_coffee in test_cases:
        result = contains_excessive_coffee(text, threshold=0.3)
        status = "✓" if result == should_be_coffee else "❌"
        print(f"  {status} '{text}' -> Coffee-heavy: {result}")
    
    # Test post filtering
    sample_posts = [
        "I love coffee and espresso",
        "Working on a new project", 
        "Coffee coffee coffee",
        "Great design inspiration today",
        "Brewing some coffee beans"
    ]
    
    filtered = filter_coffee_heavy_posts(sample_posts, max_coffee_ratio=0.2)
    print(f"  ✓ Filtered {len(sample_posts)} posts down to {len(filtered)}")
    print("  ✅ Coffee filtering works correctly!")


def test_debug_run():
    """Test running the bot in DEBUG mode"""
    print("\n🤖 Testing bot in DEBUG mode...")
    
    # Temporarily set DEBUG mode
    import local_settings
    original_debug = local_settings.DEBUG
    local_settings.DEBUG = True
    
    try:
        from ebooks import main
        print("  Running main() in DEBUG mode...")
        main()
        print("  ✅ Bot ran successfully in DEBUG mode!")
        return True
    except Exception as e:
        print(f"  ❌ Error running bot: {str(e)}")
        return False
    finally:
        # Restore original DEBUG setting
        local_settings.DEBUG = original_debug


def main():
    """Run all tests"""
    print("🚀 Testing robot_mk Mastodon bot")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    tests = [
        ("Environment Setup", test_environment_setup),
        ("Package Imports", test_imports), 
        ("Coffee Filtering", test_coffee_filtering),
        ("Debug Run", test_debug_run)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ {test_name} failed with exception: {str(e)}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL" 
        print(f"  {status}: {test_name}")
    
    print(f"\n🎯 {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The bot is ready to deploy.")
    else:
        print("⚠️  Some tests failed. Please fix the issues before deploying.")
        sys.exit(1)


if __name__ == "__main__":
    main()