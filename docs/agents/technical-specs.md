## Technical Specifications

### Parallel Execution

**Implementation**:
```python
# backend/openrouter.py
async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Query multiple models in parallel using asyncio.gather()."""
    tasks = []
    for idx, model in enumerate(models):
        # Count instances for duplicate models
        instance = models[:idx].count(model)
        task = query_model(model, messages, instance=instance)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # Filter out failures, return successes
    return [r for r in results if r is not None]
```

**Performance Characteristics**:
- Stage 1 latency: `max(council_member_latencies)` not `sum()`
- Stage 2 latency: `max(fact_checker_latencies)`
- Stage 3 latency: `max(peer_reviewer_latencies)`
- Stage 4 latency: `chairman_latency`
- **Total latency**: ~4× single model query (not 4N×)

### Streaming Support

**Real-Time Updates**:
```python
# Server-Sent Events (SSE) for live streaming
async for chunk in query_model_streaming(model, messages):
    yield f"data: {json.dumps(chunk)}\n\n"
```

**Event Types**:
- `stage1_start`: Beginning Stage 1
- `stage1_update`: Token-by-token updates for each model
- `stage1_complete`: All Stage 1 responses complete
- `fact_check_start`: Beginning Stage 2
- `fact_check_complete`: All fact-checks complete
- `stage3_start`: Beginning Stage 3
- `stage3_complete`: All rankings complete
- `stage4_start`: Beginning Stage 4
- `stage4_complete`: Final answer ready

**Client Implementation**:
```javascript
// frontend/src/api.js
const eventSource = new EventSource('/api/conversations/{id}/message/stream');
eventSource.addEventListener('stage1_update', (event) => {
  const data = JSON.parse(event.data);
  // Update UI with streaming tokens
});
```

### Reasoning Mode Support

**Grok Models** (`x-ai/grok-*`):
```python
# Automatically enabled when model contains "grok"
if "grok" in model_id.lower():
    payload["reasoning"] = {"enabled": True}
```

**Reasoning Details**:
```json
{
  "content": "Final answer after reasoning...",
  "reasoning_details": [
    {"type": "thought", "content": "Let me think about..."},
    {"type": "analysis", "content": "Analyzing the data..."},
    {"type": "conclusion", "content": "Therefore..."}
  ]
}
```

**Storage**:
- Reasoning details preserved in Stage 1 results
- Not currently displayed in UI (future enhancement)
- Can be used for multi-turn conversations to maintain reasoning chain

---

## Prompt Engineering Guidelines

### General Principles

1. **Be Explicit About Format**: Agents follow structured output requirements strictly
2. **Use Examples**: Show the exact format expected (especially in summaries)
3. **Separate Instructions from Content**: Use clear section dividers
4. **Emphasize Key Requirements**: Use capitalization, bold, or repetition
