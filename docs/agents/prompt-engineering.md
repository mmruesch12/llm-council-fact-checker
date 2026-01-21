
### Format Enforcement Strategies

**Strong Format Cues**:
```
IMPORTANT: Your summary MUST be formatted EXACTLY as follows:
- Start with the line "FACT CHECK SUMMARY:" (all caps, with colon)
- For each response, on a new line write: "Response X: [RATING]"
...

Example of the correct format:

FACT CHECK SUMMARY:
Response A: MOSTLY ACCURATE
Response B: MIXED
```

**Fallback Parsing**:
- Always implement regex-based extraction with fallbacks
- Don't fail if format is slightly off
- Extract what you can, log what you can't

### Domain-Specific Prompting

**For Factual Questions**:
- Emphasize accuracy verification in fact-checker prompts
- Request specific citations when possible
- Ask for uncertainty acknowledgment

**For Subjective Questions**:
- Adjust fact-checker prompt to evaluate reasoning quality
- Focus on logical consistency over factual correctness
- Weight completeness and perspective diversity higher

**For Technical Questions**:
- Consider specialized council models (e.g., code-focused)
- Request working examples in responses
- Fact-check against documentation/specs

### Anti-Bias Techniques

**Anonymization**:
- Use alphabetical labels (A, B, C) not numeric (prevents ordering bias)
- Randomize label assignment order
- Never reveal model identities until final synthesis

**Prompt Phrasing**:
- Avoid "evaluate which is best" → use "evaluate each independently"
- Don't prime for disagreement or agreement
- Neutral tone throughout

---

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
