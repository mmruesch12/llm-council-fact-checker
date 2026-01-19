"""
Test script for the /api/synthesize endpoint.
This demonstrates how external apps can use the endpoint.
"""

import httpx
import asyncio
import json

BASE_URL = "http://localhost:8001"


async def test_with_provided_responses():
    """Test the fast path - providing responses directly."""
    print("\n=== Test 1: With Pre-provided Responses (Fast Path) ===")
    
    request_data = {
        "question": "What are the main causes of climate change?",
        "responses": [
            {
                "model": "gpt-4",
                "content": "Climate change is primarily caused by greenhouse gas emissions from human activities, including burning fossil fuels, deforestation, and industrial processes."
            },
            {
                "model": "claude",
                "content": "The main drivers of climate change are carbon dioxide and other greenhouse gases released through fossil fuel combustion, agriculture, and land use changes."
            },
            {
                "model": "gemini",
                "content": "Climate change results from increased atmospheric greenhouse gases, mainly CO2 from fossil fuels, methane from agriculture, and deforestation reducing carbon absorption."
            }
        ],
        "chairman_model": "google/gemini-2.5-flash",
        "include_metadata": True
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/synthesize",
                json=request_data,
                timeout=60.0
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Success! Chairman: {result['chairman_model']}")
                print(f"\n📝 Synthesized Answer:\n{result['answer'][:500]}...")
                if result.get('metadata'):
                    print(f"\n📊 Metadata: {json.dumps(result['metadata'], indent=2)}")
            else:
                print(f"✗ Error: {response.status_code}")
                print(response.text)
        except Exception as e:
            print(f"✗ Exception: {e}")


async def test_without_responses():
    """Test the full path - running the entire council process."""
    print("\n=== Test 2: Without Pre-provided Responses (Full Council) ===")
    
    request_data = {
        "question": "What is 2+2?",
        "council_models": ["google/gemini-2.5-flash"],  # Use single fast model for testing
        "chairman_model": "google/gemini-2.5-flash",
        "fact_checking_enabled": False,
        "include_metadata": True
    }
    
    async with httpx.AsyncClient() as client:
        try:
            print("Running full council process (this may take a moment)...")
            response = await client.post(
                f"{BASE_URL}/api/synthesize",
                json=request_data,
                timeout=120.0
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Success! Chairman: {result['chairman_model']}")
                print(f"\n📝 Synthesized Answer:\n{result['answer']}")
                if result.get('metadata'):
                    print(f"\n📊 Metadata: {json.dumps(result['metadata'], indent=2)}")
            else:
                print(f"✗ Error: {response.status_code}")
                print(response.text)
        except Exception as e:
            print(f"✗ Exception: {e}")


async def test_simple_request():
    """Test the simplest possible request."""
    print("\n=== Test 3: Simplest Request (Just Question) ===")
    
    request_data = {
        "question": "What is Python?"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/synthesize",
                json=request_data,
                timeout=120.0
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Success! Chairman: {result['chairman_model']}")
                print(f"\n📝 Synthesized Answer:\n{result['answer'][:300]}...")
            else:
                print(f"✗ Error: {response.status_code}")
                print(response.text)
        except Exception as e:
            print(f"✗ Exception: {e}")


async def main():
    """Run all tests."""
    print("=" * 70)
    print("Testing /api/synthesize endpoint")
    print("=" * 70)
    print("\nNote: Make sure the backend is running on http://localhost:8001")
    print("Start it with: python -m backend.main")
    
    # Test if server is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/", timeout=5.0)
            if response.status_code == 200:
                print("✓ Server is running\n")
            else:
                print("✗ Server returned unexpected status code")
                return
    except Exception as e:
        print(f"✗ Cannot connect to server: {e}")
        print("\nPlease start the backend with: python -m backend.main")
        return
    
    # Run tests
    await test_with_provided_responses()
    # Uncomment to test full council (requires API key and takes longer)
    # await test_without_responses()
    # await test_simple_request()


if __name__ == "__main__":
    asyncio.run(main())
