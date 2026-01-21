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
    )
    
    return final_answer
```

**Example: Content Moderation**:
```python
async def moderate_content(content: str):
    question = f"Is this content safe and appropriate?\n\n{content}"
    
    # Use specialized council
    council_models = [
        "anthropic/claude-sonnet-4.5",  # Safety-focused
        "openai/gpt-5.1",               # Policy compliance
        "google/gemini-3-pro-preview",  # Nuance detection
    ]
    
    result = await run_council_process(question, council_models)
    return result
```

### Custom Agent Implementations

**Extending with New Agent Types**:

```python
# Custom Pre-Processing Agent
async def stage0_context_enrichment(user_query: str) -> str:
    """Enrich query with relevant context before council deliberation."""
    enrichment_prompt = f"""
    Analyze this question and provide relevant context that would help
    answer it more accurately:
    
    Question: {user_query}
    
    Provide:
    1. Key terms that need definition
    2. Relevant background information
    3. Common misconceptions to avoid
    """
    
    context = await query_model(CONTEXT_MODEL, [
        {"role": "user", "content": enrichment_prompt}
    ])
    
    return f"{user_query}\n\nContext: {context['content']}"

# Use in pipeline
enriched_query = await stage0_context_enrichment(user_query)
stage1_results = await stage1_collect_responses(enriched_query)
# ... continue with normal flow
```

**Custom Post-Processing Agent**:

```python
# Stage 5: Citation Verification
async def stage5_verify_citations(final_answer: str) -> Dict[str, Any]:
    """Verify all factual claims in final answer have citations."""
    verification_prompt = f"""
    Review this answer and identify any factual claims that lack citations:
    
    {final_answer}
    
    For each uncited claim, provide:
    1. The claim text
    2. Whether it needs a citation
    3. A suggested source (if possible)
    """
    
    verification = await query_model(VERIFICATION_MODEL, [
        {"role": "user", "content": verification_prompt}
    ])
    
    return {
        "verified_answer": final_answer,
        "citation_analysis": verification['content']
    }
```

---

## Future Enhancements
