    
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

### Short-Term Improvements

**1. Multi-Turn Conversations**
- Include conversation history in agent context
- Preserve reasoning chains across turns (for Grok models)
- Allow follow-up questions that reference prior answers
- Implementation: Extend `messages` array in `query_model()`

**2. Configurable Council via UI**
- Dynamic model selection from frontend
- Save custom council configurations
- Per-conversation model selection
- Implementation: Add model selection to `/api/conversations/{id}/message`

**3. Performance Analytics**
- Track model accuracy over time
- Identify best council compositions
- Measure agreement/disagreement patterns
- Implementation: Extend error catalog with analytics

**4. Custom Fact-Checking Criteria**
- Domain-specific fact-check prompts
- Adjustable rigor levels (strict vs. lenient)
- Custom error taxonomies per use case
- Implementation: Parameterize fact-check prompt template

### Medium-Term Enhancements

**5. Web Search Integration**
- Fact-checkers can query search engines
- Verify claims against authoritative sources
- Include source links in fact-check reports
- Implementation: Tool-calling integration for fact-checkers

**6. Reasoning Chain Visualization**
- Display Grok model reasoning steps in UI
- Interactive exploration of thinking process
- Compare reasoning across models
