"""OpenRouter API client for making LLM requests."""

import httpx
import time
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator, Callable
from .config import OPENROUTER_API_KEY, OPENROUTER_API_URL


def is_grok_model(model: str) -> bool:
    """
    Check if a model is a Grok model that supports reasoning mode.
    
    Args:
        model: OpenRouter model identifier
        
    Returns:
        True if the model is a Grok model, False otherwise
    """
    return model.lower().startswith('x-ai/grok')


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
    
    # Enable reasoning mode for Grok models
    if is_grok_model(model):
        payload["reasoning"] = {"enabled": True}

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


async def query_model_streaming(
    model: str,
    messages: List[Dict[str, str]],
    instance: int,
    on_chunk: Callable[[str, str, int, str], None],
    timeout: float = 120.0
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via OpenRouter API with streaming.
    Calls on_chunk callback for each token received.

    Args:
        model: OpenRouter model identifier
        messages: List of message dicts with 'role' and 'content'
        instance: Index of this model in the council (for identifying chunks)
        on_chunk: Callback function (model, instance, chunk_text) -> None
        timeout: Request timeout in seconds

    Returns:
        Complete response dict with 'content' and 'response_time_ms', or None if failed
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    
    # Enable reasoning mode for Grok models
    if is_grok_model(model):
        payload["reasoning"] = {"enabled": True}

    start_time = time.time()
    full_content = ""
    reasoning_details = None

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                OPENROUTER_API_URL,
                headers=headers,
                json=payload
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            import json
                            data = json.loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                chunk_text = delta.get("content", "")
                                if chunk_text:
                                    full_content += chunk_text
                                    # Call the callback with chunk info
                                    await on_chunk(model, instance, chunk_text)
                                # Capture reasoning_details if present
                                if "reasoning_details" in delta:
                                    reasoning_details = delta.get("reasoning_details")
                        except (json.JSONDecodeError, KeyError, IndexError):
                            pass

        end_time = time.time()
        response_time_ms = round((end_time - start_time) * 1000)

        return {
            'content': full_content,
            'reasoning_details': reasoning_details,
            'response_time_ms': response_time_ms
        }

    except Exception as e:
        print(f"Error streaming model {model}: {e}")
        return None


async def query_models_parallel_streaming(
    models: List[str],
    messages: List[Dict[str, str]],
    on_chunk: Callable[[str, int, str], None]
) -> List[Dict[str, Any]]:
    """
    Query multiple models in parallel with streaming.
    Each model's tokens are streamed via the on_chunk callback.

    Args:
        models: List of OpenRouter model identifiers (may contain duplicates)
        messages: List of message dicts to send to each model
        on_chunk: Async callback function (model, instance, chunk_text) -> None

    Returns:
        List of dicts, each containing 'model', 'instance', and response data.
    """
    # Create streaming tasks for all models
    tasks = [
        query_model_streaming(model, messages, idx, on_chunk)
        for idx, model in enumerate(models)
    ]

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
