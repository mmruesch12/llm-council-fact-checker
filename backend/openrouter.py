"""OpenRouter API client for making LLM requests."""

import httpx
import time
from typing import List, Dict, Any, Optional
from .config import OPENROUTER_API_KEY, OPENROUTER_API_URL


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via OpenRouter API.

    Args:
        model: OpenRouter model identifier (e.g., "openai/gpt-4o")
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds

    Returns:
        Response dict with 'content', optional 'reasoning_details', and 'response_time_ms', or None if failed
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
    }

    start_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            end_time = time.time()
            response_time_ms = round((end_time - start_time) * 1000)

            data = response.json()
            message = data['choices'][0]['message']

            return {
                'content': message.get('content'),
                'reasoning_details': message.get('reasoning_details'),
                'response_time_ms': response_time_ms
            }

    except Exception as e:
        print(f"Error querying model {model}: {e}")
        return None


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]]
) -> List[Dict[str, Any]]:
    """
    Query multiple models in parallel.

    Args:
        models: List of OpenRouter model identifiers (may contain duplicates)
        messages: List of message dicts to send to each model

    Returns:
        List of dicts, each containing 'model', 'instance' (index), and response data.
        This preserves order and handles duplicate models correctly.
    """
    import asyncio

    # Create tasks for all models (including duplicates)
    tasks = [query_model(model, messages) for model in models]

    # Wait for all to complete
    responses = await asyncio.gather(*tasks)

    # Return as list preserving order and including instance index
    results = []
    for idx, (model, response) in enumerate(zip(models, responses)):
        results.append({
            "model": model,
            "instance": idx,
            "response": response
        })
    return results
