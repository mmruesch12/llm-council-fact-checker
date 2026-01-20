# Using the /api/synthesize Endpoint

This guide shows how to use the new `/api/synthesize` endpoint to integrate LLM Council's synthesis capability into your own applications.

## Overview

The `/api/synthesize` endpoint provides a simplified way to get a chairman's synthesized answer without running the full council UI workflow. It supports two modes:

1. **Fast Path**: Provide your own responses and get a synthesis
2. **Full Council**: Let the backend generate responses and synthesize them

## Prerequisites

- Backend running on `http://localhost:8001` (or your deployed URL)
- OpenRouter API key configured (if using full council mode)

## Quick Start Examples

### Example 1: Fast Path (Pre-provided Responses)

This is the recommended approach for external integrations where you already have responses from your own sources.

```python
import httpx

# Your existing responses from various sources
responses = [
    {
        "model": "openai/gpt-5.1",
        "content": "The sky appears blue due to Rayleigh scattering..."
    },
    {
        "model": "anthropic/claude-sonnet-4.5",
        "content": "Blue sky color results from atmospheric scattering..."
    }
]

# Get synthesized answer
response = httpx.post("http://localhost:8001/api/synthesize", json={
    "question": "Why is the sky blue?",
    "responses": responses,
    "chairman_model": "x-ai/grok-4.1-fast"
})

result = response.json()
print(f"Chairman: {result['chairman_model']}")
print(f"Answer: {result['answer']}")
```

### Example 2: Full Council Mode

Let the backend run the complete council process.

```python
import httpx

response = httpx.post("http://localhost:8001/api/synthesize", json={
    "question": "What is quantum computing?",
    "council_models": [
        "openai/gpt-5.1",
        "google/gemini-3-pro-preview",
        "anthropic/claude-sonnet-4.5"
    ],
    "chairman_model": "x-ai/grok-4.1-fast",
    "fact_checking_enabled": True,
    "include_metadata": True
})

result = response.json()
print(f"Answer: {result['answer']}")
print(f"Metadata: {result['metadata']}")
```

### Example 3: With Metadata

Request additional metadata about the synthesis process.

```python
import httpx

response = httpx.post("http://localhost:8001/api/synthesize", json={
    "question": "How does photosynthesis work?",
    "responses": [...],  # Your responses
    "include_metadata": True
})

result = response.json()
print(f"Answer: {result['answer']}")

# Metadata tells you about the synthesis
metadata = result['metadata']
print(f"Responses provided: {metadata['responses_provided']}")
print(f"Full council run: {metadata['full_council_run']}")
```

## Integration Patterns

### Pattern 1: Multi-Source Aggregator

Collect responses from multiple AI providers and synthesize them:

```python
import asyncio
import httpx

async def get_responses_from_multiple_sources(question):
    """Get responses from your various AI sources."""
    # Example: call different APIs
    responses = []
    
    # Source 1: OpenAI
    openai_response = await call_openai_api(question)
    responses.append({
        "model": "openai/gpt-5.1",
        "content": openai_response
    })
    
    # Source 2: Anthropic
    anthropic_response = await call_anthropic_api(question)
    responses.append({
        "model": "anthropic/claude-sonnet-4.5",
        "content": anthropic_response
    })
    
    return responses

async def synthesize_answer(question):
    """Get responses and synthesize them."""
    # Gather responses
    responses = await get_responses_from_multiple_sources(question)
    
    # Synthesize using LLM Council
    async with httpx.AsyncClient() as client:
        result = await client.post(
            "http://localhost:8001/api/synthesize",
            json={
                "question": question,
                "responses": responses,
                "chairman_model": "x-ai/grok-4.1-fast"
            }
        )
        return result.json()

# Usage
answer = asyncio.run(synthesize_answer("What is AI?"))
print(answer['answer'])
```

### Pattern 2: Custom RAG Pipeline

Integrate with your Retrieval-Augmented Generation system:

```python
import httpx

def rag_with_synthesis(question, documents):
    """Use RAG to get candidate answers, then synthesize."""
    # Generate responses using your RAG system
    responses = []
    
    for doc_context in documents:
        rag_answer = your_rag_model.generate(question, doc_context)
        responses.append({
            "model": f"rag-{doc_context['source']}",
            "content": rag_answer
        })
    
    # Synthesize the RAG responses
    result = httpx.post("http://localhost:8001/api/synthesize", json={
        "question": question,
        "responses": responses
    })
    
    return result.json()['answer']
```

### Pattern 3: Chatbot Integration

Add synthesis to your chatbot:

```python
class ChatbotWithSynthesis:
    def __init__(self):
        self.api_url = "http://localhost:8001/api/synthesize"
    
    def get_answer(self, user_question):
        """Get a synthesized answer for user question."""
        # Option 1: Full council (slower, more comprehensive)
        response = httpx.post(self.api_url, json={
            "question": user_question,
            "council_models": ["openai/gpt-5.1", "anthropic/claude-sonnet-4.5"],
            "fact_checking_enabled": False  # Faster without fact-checking
        })
        
        return response.json()['answer']

# Usage
bot = ChatbotWithSynthesis()
answer = bot.get_answer("What is machine learning?")
print(answer)
```

## API Reference

### Request Schema

```typescript
{
  question: string;              // Required: The question to answer
  responses?: Array<{           // Optional: Pre-provided responses
    model: string;
    content: string;
  }>;
  council_models?: string[];    // Optional: Models to use (if responses not provided)
  chairman_model?: string;      // Optional: Chairman model (default: from config)
  fact_checking_enabled?: boolean;  // Optional: Enable fact-checking (default: false)
  include_metadata?: boolean;   // Optional: Include metadata (default: false)
}
```

### Response Schema

```typescript
{
  answer: string;               // The synthesized answer
  chairman_model: string;       // Chairman model used
  metadata?: {                  // Only if include_metadata=true
    responses_provided?: number;
    responses_count?: number;
    fact_checking_enabled: boolean;
    full_council_run: boolean;
    council_models?: string[];
    aggregate_rankings?: Array<{
      model: string;
      instance: number;
      average_rank: number;
      rankings_count: number;
    }>;
    aggregate_fact_checks?: Array<{
      model: string;
      instance: number;
      consensus_rating: string;
      average_score: number;
      ratings_count: number;
      most_reliable_votes: number;
    }>;
  };
}
```

## Error Handling

Always handle potential errors:

```python
import httpx

try:
    response = httpx.post("http://localhost:8001/api/synthesize", json={
        "question": "What is AI?",
        "responses": [...]
    }, timeout=60.0)
    
    response.raise_for_status()
    result = response.json()
    print(result['answer'])
    
except httpx.HTTPError as e:
    print(f"HTTP error: {e}")
except httpx.RequestError as e:
    print(f"Request error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Performance Tips

1. **Use Fast Path**: If you already have responses, use the fast path to skip stages 1-3
2. **Disable Fact-Checking**: Set `fact_checking_enabled: false` for faster responses
3. **Choose Fast Models**: Use models like `google/gemini-2.5-flash` for quicker synthesis
4. **Parallel Requests**: The endpoint is stateless and can handle parallel requests
5. **Set Timeouts**: Use appropriate timeouts (60s for fast path, 120s+ for full council)

## Authentication

If authentication is enabled on the backend, include credentials:

```python
import httpx

# Using cookies (after OAuth login)
cookies = {"session": "your-session-token"}
response = httpx.post(
    "http://localhost:8001/api/synthesize",
    json={"question": "..."},
    cookies=cookies
)

# Or use the auth flow
# 1. Direct user to /auth/login
# 2. Handle callback at /auth/callback
# 3. Use session cookie for subsequent requests
```

## Deployment Considerations

### Production URL

Update the base URL for production:

```python
# Development
API_URL = "http://localhost:8001/api/synthesize"

# Production (example)
API_URL = "https://your-api.onrender.com/api/synthesize"
```

### Rate Limiting

Implement rate limiting on your end:

```python
from ratelimit import limits, sleep_and_retry

@sleep_and_retry
@limits(calls=10, period=60)  # 10 calls per minute
def call_synthesis_api(question, responses):
    return httpx.post(API_URL, json={
        "question": question,
        "responses": responses
    })
```

## Support

For issues or questions:
- Check the main README.md
- Review the OpenAPI docs at `http://localhost:8001/docs`
- File an issue on GitHub
