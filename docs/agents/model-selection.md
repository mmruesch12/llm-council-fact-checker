2. **Long Context**: Can handle all prior stages as input
3. **Writing Quality**: Produces clear, well-structured prose
4. **Factual Accuracy**: Strong knowledge base to validate fact-checkers

**Recommended Chairman Models**:
- `openai/gpt-5.1` - Excellent all-around synthesis
- `anthropic/claude-sonnet-4.5` - Superior writing quality
- `google/gemini-3-pro-preview` - Strong factual knowledge
- `x-ai/grok-4` - Good balance of speed and quality

**Chairman ≠ Council Member**:
- Chairman can be different from council members
- Often beneficial to use a stronger model as chairman
- Example: Council of fast models, chairman is flagship model

### Cost Optimization

**Tiered Approach**:
```python
# Stage 1-3: Fast, cost-effective models
COUNCIL_MODELS = [
    "openai/gpt-5-nano",
    "google/gemini-3-flash-preview",
    "x-ai/grok-4-fast",
]

# Stage 4: Premium model for final synthesis
CHAIRMAN_MODEL = "openai/gpt-5.1"
```

**Dynamic Scaling**:
- Use fewer council members for simple questions
- Use more for complex/controversial topics
- Implement question complexity detection (future enhancement)

### Performance Tuning

**Latency-Sensitive Applications**:
```python
# All fast models for sub-10s total latency
COUNCIL_MODELS = [
    "openai/gpt-5-nano",
    "google/gemini-3-flash-preview",
    "x-ai/grok-4-fast",
    "x-ai/grok-4.1-fast",
]
CHAIRMAN_MODEL = "x-ai/grok-4-fast"
```

**Quality-Focused Applications**:
```python
# Premium models for best results
COUNCIL_MODELS = [
    "openai/gpt-5.1",
    "anthropic/claude-sonnet-4.5",
    "google/gemini-3-pro-preview",
]
CHAIRMAN_MODEL = "openai/gpt-5.1"
```

---

## Integration Patterns

### External API Integration

**Simplified Synthesis Endpoint** (`/api/synthesize`):

```python
import httpx

# Mode 1: Fast Path (pre-provided responses)
response = httpx.post("http://localhost:8001/api/synthesize", json={
    "question": "What causes climate change?",
    "responses": [
        {"model": "gpt-5", "content": "Response 1..."},
        {"model": "gemini-3", "content": "Response 2..."},
    ],
    "chairman_model": "x-ai/grok-4-fast"
})

# Mode 2: Full Council (generate responses)
response = httpx.post("http://localhost:8001/api/synthesize", json={
    "question": "What causes climate change?",
    "council_models": ["model1", "model2"],
    "chairman_model": "x-ai/grok-4-fast",
    "fact_checking_enabled": True
})
```

**Use Cases**:
1. **Fact-check external LLM outputs**: Run responses through council validation
2. **API Gateway Pattern**: Hide multi-model complexity behind single endpoint
3. **Batch Processing**: Process many questions with council deliberation
4. **Hybrid Systems**: Use council for critical decisions, single LLM for routine

### Embedding in Applications

**Example: Research Assistant**:
```python
async def research_question(question: str):
    # Stage 1: Get diverse perspectives
    perspectives = await stage1_collect_responses(question)
    
    # Stage 2: Fact-check all claims
    fact_checks, label_map = await stage2_fact_check(question, perspectives)
    
    # Stage 3: Rank by reliability
    rankings = await stage3_collect_rankings(question, perspectives, fact_checks, label_map)
    
    # Stage 4: Synthesize with citations
    final_answer = await stage4_synthesize_final(
        question, perspectives, fact_checks, rankings, label_map
