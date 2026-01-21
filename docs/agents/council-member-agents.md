### Council Member Agents

**Purpose**: Provide initial independent responses to user queries.

**Stage**: Stage 1 (Individual Responses)

**Capabilities**:
- Respond to open-ended questions across any domain
- Process context from conversation history (when multi-turn is enabled)
- Support reasoning mode for step-by-step thinking (Grok models)
- Generate responses with variable length and depth

**Configuration**:
```python
# In backend/config.py
COUNCIL_MODELS = [
    "google/gemini-3-flash-preview",
    "x-ai/grok-4-fast",
    "x-ai/grok-4.1-fast",
    "openai/gpt-5-nano",
]
```

**Input Format**:
```json
{
  "messages": [
    {"role": "user", "content": "What causes climate change?"}
  ]
}
```

**Output Format**:
```json
{
  "model": "google/gemini-3-flash-preview",
  "instance": 0,
  "response": "Climate change is primarily caused by...",
  "response_time_ms": 1234,
  "reasoning_details": []  // Optional: for Grok models
}
```

**Implementation Details**:
- Executes via `stage1_collect_responses()` in `backend/council.py`
- Queries run in parallel using `asyncio.gather()` for minimal latency
- Handles duplicate models by assigning instance numbers
- Preserves `reasoning_details` for Grok models with reasoning mode enabled
- Returns only successful responses (graceful degradation on failures)

**Model Requirements**:
- Must support OpenRouter chat completions API
- Should provide reasonable response times (<30 seconds recommended)
- No specific context window requirement (system uses single-turn by default)

