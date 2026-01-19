#!/usr/bin/env python3
"""
Test script to verify OAuth callback URL configuration.
This demonstrates that the OAUTH_CALLBACK_URL environment variable works correctly.
"""

import os
import sys

def test_oauth_callback_url():
    """Test that OAUTH_CALLBACK_URL is used when set."""
    print("=" * 60)
    print("Testing OAuth Callback URL Configuration")
    print("=" * 60)
    print()
    
    # Test 1: No environment variable (auto-detection)
    print("Test 1: Auto-detection (no OAUTH_CALLBACK_URL set)")
    print("-" * 60)
    if 'OAUTH_CALLBACK_URL' in os.environ:
        del os.environ['OAUTH_CALLBACK_URL']
    
    # Need to reload config module to pick up env changes
    if 'backend.config' in sys.modules:
        del sys.modules['backend.config']
    
    from backend.config import OAUTH_CALLBACK_URL as url1
    print(f"OAUTH_CALLBACK_URL: {url1}")
    assert url1 is None, "Should be None when env var not set"
    print("✓ PASS: Returns None for auto-detection")
    print()
    
    # Test 2: Explicit environment variable
    print("Test 2: Explicit callback URL")
    print("-" * 60)
    test_url = "https://llm-council-api-9zfj.onrender.com/auth/callback"
    os.environ['OAUTH_CALLBACK_URL'] = test_url
    
    # Reload config
    if 'backend.config' in sys.modules:
        del sys.modules['backend.config']
    
    from backend.config import OAUTH_CALLBACK_URL as url2
    print(f"OAUTH_CALLBACK_URL: {url2}")
    assert url2 == test_url, f"Should be {test_url}"
    print("✓ PASS: Returns explicit URL from environment variable")
    print()
    
    # Test 3: Verify it's used in auth module
    print("Test 3: Auth module uses OAUTH_CALLBACK_URL")
    print("-" * 60)
    from backend.auth import OAUTH_CALLBACK_URL as auth_url
    print(f"Auth module OAUTH_CALLBACK_URL: {auth_url}")
    assert auth_url == test_url, "Auth module should import the same URL"
    print("✓ PASS: Auth module correctly imports OAUTH_CALLBACK_URL")
    print()
    
    # Test 4: Demonstrate the fallback logic
    print("Test 4: Fallback logic demonstration")
    print("-" * 60)
    print("In auth.py, the callback URL is determined by:")
    print('  callback_url = OAUTH_CALLBACK_URL or str(request.url_for("oauth_callback"))')
    print()
    print("When OAUTH_CALLBACK_URL is set:")
    print(f"  ✓ Uses explicit URL: {test_url}")
    print()
    print("When OAUTH_CALLBACK_URL is None:")
    print("  ✓ Falls back to auto-detection from request")
    print()
    
    print("=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
    print()
    print("Configuration Summary:")
    print("-" * 60)
    print("Local Development:")
    print("  - No OAUTH_CALLBACK_URL needed")
    print("  - Auto-detects as http://localhost:8001/auth/callback")
    print()
    print("Production (Render):")
    print("  - Set OAUTH_CALLBACK_URL in environment")
    print("  - Uses https://llm-council-api-9zfj.onrender.com/auth/callback")
    print()

if __name__ == "__main__":
    try:
        test_oauth_callback_url()
        sys.exit(0)
    except AssertionError as e:
        print(f"✗ FAIL: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
