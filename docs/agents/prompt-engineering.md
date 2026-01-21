## Prompt Engineering Guidelines

### General Principles

1. **Be Explicit About Format**: Agents follow structured output requirements strictly
2. **Use Examples**: Show the exact format expected (especially in summaries)
3. **Separate Instructions from Content**: Use clear section dividers
4. **Emphasize Key Requirements**: Use capitalization, bold, or repetition
5. **Provide Context Hierarchy**: Most important information first

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
