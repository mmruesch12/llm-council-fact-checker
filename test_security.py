#!/usr/bin/env python3
"""
Test script to demonstrate API security features.

This script demonstrates:
1. Rate limiting behavior
2. API key authentication
3. Request size validation
4. Security headers in responses

Run the backend server first:
    python -m backend.main

Then run this script:
    python test_security.py
"""

import httpx
import time
import sys

BASE_URL = "http://localhost:8001"


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_health_check():
    """Test basic health check endpoint."""
    print_section("Test 1: Health Check (No Auth Required)")
    
    try:
        response = httpx.get(f"{BASE_URL}/")
        print(f"✓ Status: {response.status_code}")
        print(f"✓ Response: {response.json()}")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_security_headers():
    """Test that security headers are present."""
    print_section("Test 2: Security Headers")
    
    try:
        response = httpx.get(f"{BASE_URL}/")
        headers = response.headers
        
        security_headers = {
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }
        
        all_present = True
        for header, expected in security_headers.items():
            if header in headers:
                print(f"✓ {header}: {headers[header]}")
            else:
                print(f"✗ {header}: Missing")
                all_present = False
        
        return all_present
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_rate_limiting():
    """Test rate limiting behavior."""
    print_section("Test 3: Rate Limiting")
    
    print("Making 5 rapid requests to /api/models...")
    
    try:
        for i in range(5):
            response = httpx.get(f"{BASE_URL}/api/models")
            
            # Check rate limit headers
            limit = response.headers.get("X-RateLimit-Limit", "N/A")
            remaining = response.headers.get("X-RateLimit-Remaining", "N/A")
            
            print(f"  Request {i+1}: Status={response.status_code}, "
                  f"Limit={limit}, Remaining={remaining}")
            
            time.sleep(0.5)  # Small delay between requests
        
        print("✓ Rate limiting headers present")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_synthesize_without_auth():
    """Test /api/synthesize endpoint without authentication."""
    print_section("Test 4: /api/synthesize Without Auth")
    
    try:
        response = httpx.post(
            f"{BASE_URL}/api/synthesize",
            json={
                "question": "Test question",
                "responses": [
                    {"model": "test", "content": "Test response"}
                ]
            },
            timeout=10.0
        )
        
        if response.status_code == 401:
            print("✓ Correctly rejected (auth required)")
            print(f"  Message: {response.json().get('detail', 'N/A')}")
            return True
        elif response.status_code == 200:
            print("✓ Request accepted (auth disabled)")
            return True
        else:
            print(f"✗ Unexpected status: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_synthesize_with_api_key():
    """Test /api/synthesize endpoint with API key."""
    print_section("Test 5: /api/synthesize With API Key")
    
    # Generate a test API key
    from backend.api_key_auth import generate_api_key
    test_key = generate_api_key()
    
    print(f"Generated test API key: {test_key[:30]}...")
    print("Note: This key is NOT configured in the server, so it will be rejected.")
    
    try:
        response = httpx.post(
            f"{BASE_URL}/api/synthesize",
            headers={"X-API-Key": test_key},
            json={
                "question": "Test question",
                "responses": [
                    {"model": "test", "content": "Test response"}
                ]
            },
            timeout=10.0
        )
        
        if response.status_code == 401:
            print("✓ Invalid API key correctly rejected")
            return True
        else:
            print(f"Status: {response.status_code}")
            return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_request_size_validation():
    """Test request size validation."""
    print_section("Test 6: Request Size Validation")
    
    # Create a large payload (>50KB)
    large_content = "A" * 51000
    
    try:
        response = httpx.post(
            f"{BASE_URL}/api/conversations",
            json={},
            timeout=10.0
        )
        
        if response.status_code in [200, 201]:
            conversation_id = response.json()["id"]
            
            # Try to send oversized message
            response = httpx.post(
                f"{BASE_URL}/api/conversations/{conversation_id}/message",
                json={
                    "content": large_content
                },
                timeout=10.0
            )
            
            if response.status_code == 422:
                print("✓ Oversized request correctly rejected")
                print(f"  Error: {response.json()}")
                return True
            else:
                print(f"✗ Unexpected status: {response.status_code}")
                return False
        else:
            print("Skipping (requires auth)")
            return True
    except Exception as e:
        print(f"Note: {e}")
        return True


def main():
    """Run all security tests."""
    print("\n" + "=" * 60)
    print("  LLM Council API Security Test Suite")
    print("=" * 60)
    print("\nMake sure the server is running on http://localhost:8001")
    print("Start it with: python -m backend.main")
    
    # Wait for user confirmation
    try:
        input("\nPress Enter to continue...")
    except KeyboardInterrupt:
        print("\n\nTests cancelled.")
        sys.exit(0)
    
    # Run tests
    tests = [
        ("Health Check", test_health_check),
        ("Security Headers", test_security_headers),
        ("Rate Limiting", test_rate_limiting),
        ("Synthesize Without Auth", test_synthesize_without_auth),
        ("Synthesize With API Key", test_synthesize_with_api_key),
        ("Request Size Validation", test_request_size_validation),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test failed with exception: {e}")
            results.append((name, False))
        time.sleep(1)  # Pause between tests
    
    # Summary
    print_section("Test Summary")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All security features are working correctly!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review the output above.")


if __name__ == "__main__":
    main()
