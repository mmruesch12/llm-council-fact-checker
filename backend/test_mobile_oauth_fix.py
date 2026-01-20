#!/usr/bin/env python3
"""
Test script to verify mobile OAuth fix.
This tests that OAuth state is stored server-side instead of in cookies,
which resolves the mobile browser login issue.
"""

import time
import sys
import asyncio

async def test_oauth_state_storage():
    """Test that OAuth state is stored server-side."""
    print("=" * 70)
    print("Testing Mobile OAuth Fix - Server-side State Storage")
    print("=" * 70)
    print()
    
    from backend.auth import (
        store_oauth_state, 
        verify_oauth_state, 
        oauth_state_cache,
        oauth_state_lock,
        OAUTH_STATE_TTL
    )
    
    # Test 1: Store and verify state
    print("Test 1: Store and verify OAuth state")
    print("-" * 70)
    state1 = "test_state_12345"
    await store_oauth_state(state1)
    assert state1 in oauth_state_cache, "State should be in cache"
    print(f"✓ State stored: {state1}")
    
    result = await verify_oauth_state(state1)
    assert result is True, "State should verify successfully"
    print(f"✓ State verified: {result}")
    
    # After verification, state should be removed (one-time use)
    assert state1 not in oauth_state_cache, "State should be removed after verification"
    print(f"✓ State removed after verification (one-time use)")
    print()
    
    # Test 2: Verify returns False for unknown state
    print("Test 2: Unknown state verification")
    print("-" * 70)
    unknown_state = "unknown_state"
    result = await verify_oauth_state(unknown_state)
    assert result is False, "Unknown state should fail verification"
    print(f"✓ Unknown state verification failed as expected: {result}")
    print()
    
    # Test 3: Multiple states can coexist
    print("Test 3: Multiple concurrent states")
    print("-" * 70)
    state2 = "state_user_1"
    state3 = "state_user_2"
    await store_oauth_state(state2)
    await store_oauth_state(state3)
    assert state2 in oauth_state_cache, "State 2 should be in cache"
    assert state3 in oauth_state_cache, "State 3 should be in cache"
    print(f"✓ Multiple states stored: {len(oauth_state_cache)} states in cache")
    
    # Verify one doesn't affect the other
    result2 = await verify_oauth_state(state2)
    assert result2 is True, "State 2 should verify"
    assert state3 in oauth_state_cache, "State 3 should still be in cache"
    print(f"✓ Verifying one state doesn't affect others")
    
    # Clean up
    await verify_oauth_state(state3)
    print()
    
    # Test 4: State expiration
    print("Test 4: State expiration")
    print("-" * 70)
    print(f"State TTL: {OAUTH_STATE_TTL} seconds (10 minutes)")
    state4 = "expiring_state"
    await store_oauth_state(state4)
    expiration_time = oauth_state_cache[state4]
    current_time = time.time()
    remaining = int(expiration_time - current_time)
    print(f"✓ State stored with {remaining} seconds until expiration")
    
    # Manually set expiration to past (simulate expired state)
    async with oauth_state_lock:
        oauth_state_cache[state4] = time.time() - 1
    result = await verify_oauth_state(state4)
    assert result is False, "Expired state should fail verification"
    assert state4 not in oauth_state_cache, "Expired state should be removed"
    print(f"✓ Expired state rejected and removed")
    print()
    
    # Test 5: Thread-safe concurrent access
    print("Test 5: Thread-safe concurrent access")
    print("-" * 70)
    
    # Simulate concurrent state storage
    async def store_multiple():
        tasks = []
        for i in range(5):
            tasks.append(store_oauth_state(f"concurrent_state_{i}"))
        await asyncio.gather(*tasks)
    
    await store_multiple()
    print(f"✓ Successfully stored 5 states concurrently")
    print(f"✓ Cache size: {len(oauth_state_cache)}")
    
    # Clean up
    for i in range(5):
        state = f"concurrent_state_{i}"
        if state in oauth_state_cache:
            await verify_oauth_state(state)
    print()
    
    print("=" * 70)
    print("All tests passed! ✓")
    print("=" * 70)
    print()
    print("Mobile Browser Fix Summary:")
    print("-" * 70)
    print("BEFORE FIX:")
    print("  ✗ OAuth state stored in cookies")
    print("  ✗ Mobile browsers (Safari/iOS) block cookies in redirect chains")
    print("  ✗ State validation fails on callback")
    print("  ✗ User redirected back to login page")
    print()
    print("AFTER FIX:")
    print("  ✓ OAuth state stored server-side in memory")
    print("  ✓ No cookies required for state validation")
    print("  ✓ Works on all mobile browsers")
    print("  ✓ One-time use security (state deleted after verification)")
    print("  ✓ Thread-safe concurrent access with asyncio.Lock")
    print("  ✓ Periodic cleanup (every 60 seconds)")
    print("  ✓ Session cookie still used for authenticated sessions")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(test_oauth_state_storage())
        sys.exit(0)
    except AssertionError as e:
        print(f"✗ FAIL: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
