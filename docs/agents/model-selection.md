## Model Selection Best Practices

### Council Member Selection

**Diversity Over Uniformity**:
- ✅ Mix model providers (OpenAI, Google, Anthropic, xAI)
- ✅ Mix model sizes (large flagship + fast smaller)
- ✅ Mix model generations (latest + stable previous gen)
- ❌ Don't use only one provider
- ❌ Don't use only tiny models or only huge models

**Example Balanced Council**:
```python
COUNCIL_MODELS = [
    "openai/gpt-5.1",              # Strong reasoning
    "google/gemini-3-flash-preview",  # Fast + broad knowledge
    "anthropic/claude-sonnet-4.5",    # Excellent at nuance
    "x-ai/grok-4-fast",               # Real-time knowledge
]
```

**Specialized Councils**:
```python
# Code Review Council
COUNCIL_MODELS = [
    "openai/gpt-5.1",
    "x-ai/grok-code-fast-1",
    "google/gemini-3-pro-preview",
]

# Research Paper Analysis Council
COUNCIL_MODELS = [
    "anthropic/claude-sonnet-4.5",
    "openai/gpt-5.1",
    "google/gemini-3-pro-preview",
    "deepseek/deepseek-r1",
]
```

### Chairman Selection

**Qualities to Prioritize**:
1. **Synthesis Ability**: Excellent at combining multiple sources
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
