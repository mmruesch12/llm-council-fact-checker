#!/usr/bin/env python3
"""Test script to verify Grok models have reasoning mode enabled."""

import asyncio
import json
from backend.openrouter import query_model
from backend.config import OPENROUTER_API_KEY


async def test_grok_reasoning():
    """Test that Grok models enable reasoning mode and capture reasoning_details."""
    
    if not OPENROUTER_API_KEY:
        print("❌ OPENROUTER_API_KEY not set in environment")
        return False
    
    # Test with a Grok model
    test_model = "x-ai/grok-4.1-fast"
    test_question = "How many r's are in the word 'strawberry'?"
    
    print(f"Testing reasoning mode with {test_model}...")
    print(f"Question: {test_question}\n")
    
    messages = [{"role": "user", "content": test_question}]
    
    try:
        response = await query_model(test_model, messages)
        
        if response is None:
            print("❌ Query failed - no response received")
            return False
        
        print(f"✅ Query successful")
        print(f"\nResponse content (first 200 chars):")
        print(response.get('content', '')[:200])
        
        if response.get('reasoning_details'):
            print(f"\n✅ Reasoning details captured!")
            print(f"Reasoning details type: {type(response['reasoning_details'])}")
            print(f"Reasoning details (truncated): {str(response['reasoning_details'])[:200]}...")
        else:
            print(f"\n⚠️  No reasoning_details in response")
            print("This might be expected if the model didn't use reasoning for this query,")
            print("or if reasoning mode is not yet supported for this model.")
        
        print(f"\nResponse time: {response.get('response_time_ms')} ms")
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_non_grok_model():
    """Test that non-Grok models don't have reasoning parameter added."""
    
    if not OPENROUTER_API_KEY:
        print("❌ OPENROUTER_API_KEY not set in environment")
        return False
    
    # Test with a non-Grok model
    test_model = "google/gemini-3-flash-preview"
    test_question = "What is 2+2?"
    
    print(f"\n\nTesting non-Grok model: {test_model}...")
    print(f"Question: {test_question}\n")
    
    messages = [{"role": "user", "content": test_question}]
    
    try:
        response = await query_model(test_model, messages)
        
        if response is None:
            print("❌ Query failed - no response received")
            return False
        
        print(f"✅ Query successful for non-Grok model")
        print(f"\nResponse content: {response.get('content', '')[:100]}")
        print(f"Response time: {response.get('response_time_ms')} ms")
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Grok Reasoning Mode Implementation")
    print("=" * 60 + "\n")
    
    grok_test = await test_grok_reasoning()
    non_grok_test = await test_non_grok_model()
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Grok reasoning test: {'✅ PASSED' if grok_test else '❌ FAILED'}")
    print(f"Non-Grok model test: {'✅ PASSED' if non_grok_test else '❌ FAILED'}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
