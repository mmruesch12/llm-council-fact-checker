# AGENTS.md - LLM Council Agent Architecture

This document describes the agent-based architecture of the LLM Council Fact-Checker system, including specifications for each agent type, their roles, prompt engineering guidelines, and integration patterns.

## Table of Contents

- [Overview](#overview)
- [Agent Types](#agent-types)
  - [Council Member Agents](#council-member-agents)
  - [Fact-Checker Agents](#fact-checker-agents)
  - [Peer Review Agents](#peer-review-agents)
  - [Chairman Agent](#chairman-agent)
- [Agent Lifecycle](#agent-lifecycle)
- [Technical Specifications](#technical-specifications)
- [Prompt Engineering Guidelines](#prompt-engineering-guidelines)
- [Model Selection Best Practices](#model-selection-best-practices)
- [Integration Patterns](#integration-patterns)
- [Future Enhancements](#future-enhancements)

## Overview

The LLM Council is a **multi-agent deliberative system** that uses four distinct types of AI agents working in sequence to produce fact-checked, peer-reviewed answers to user questions. Unlike traditional single-LLM systems, this architecture leverages:

1. **Collective Intelligence**: Multiple models with different strengths contribute perspectives
2. **Anonymized Peer Review**: Prevents bias through blind evaluation
3. **Fact-Checking Layer**: Dedicated accuracy verification before final synthesis
4. **Transparent Validation**: All intermediate steps are visible for user trust

### Core Principles

- **Graceful Degradation**: System continues if individual agents fail
- **Parallel Execution**: Agents of the same type run simultaneously for speed
- **Structured Output**: Agents follow strict formatting requirements for parsing
- **Model Agnosticism**: Any OpenRouter-compatible model can serve as any agent type

## Agent Types

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

---

### Fact-Checker Agents

**Purpose**: Verify factual accuracy of all council member responses through rigorous analysis.

**Stage**: Stage 2 (Fact-Checking)

**Capabilities**:
- Evaluate multiple anonymized responses simultaneously
- Identify accurate, inaccurate, and unverifiable claims
- Detect missing important information
- Classify errors by type (hallucination, outdated info, etc.)
- Rate overall reliability on a 5-point scale
- Vote for the most reliable response

**Anonymization Strategy**:
- Responses presented as "Response A", "Response B", etc.
- Model identities hidden to prevent bias
- Mapping stored server-side: `{"Response A": "openai/gpt-5.1", ...}`
- De-anonymization happens client-side for display transparency

**Input Format** (Prompt Template):
```
You are a fact-checker evaluating different AI responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

Response A:
{response_content_a}

Response B:
{response_content_b}

...

Your task is to fact-check each response thoroughly:

1. For EACH response, identify:
   - **Accurate Claims**: List specific claims that are factually correct
   - **Inaccurate Claims**: List specific claims that are factually incorrect or misleading, and explain why
   - **Unverifiable Claims**: List claims that cannot be easily verified or are speculative
   - **Missing Important Information**: Note any crucial information the response failed to include

2. At the very end of your analysis, provide a summary section.

IMPORTANT: Your summary MUST be formatted EXACTLY as follows:
- Start with the line "FACT CHECK SUMMARY:" (all caps, with colon)
- For each response, on a new line write: "Response X: [ACCURATE/MOSTLY ACCURATE/MIXED/MOSTLY INACCURATE/INACCURATE]"
- After rating all responses, add a line: "MOST RELIABLE: Response X" (the single most factually reliable response)

Example of the correct format for your summary:

FACT CHECK SUMMARY:
Response A: MOSTLY ACCURATE
Response B: MIXED
Response C: ACCURATE
MOST RELIABLE: Response C
```

**Output Format**:
```json
{
  "model": "x-ai/grok-4-fast",
  "instance": 0,
  "fact_check": "Full text analysis with FACT CHECK SUMMARY at end...",
  "parsed_summary": {
    "ratings": {
      "Response A": "MOSTLY ACCURATE",
      "Response B": "MIXED",
      "Response C": "ACCURATE"
    },
    "most_reliable": "Response C"
  },
  "response_time_ms": 2456
}
```

**Error Classification**:

When inaccurate claims are identified, they should be categorized using the predefined taxonomy:

1. **Hallucinated Fact**: Made-up information with no factual basis
2. **Outdated Information**: Was true but no longer accurate
3. **Numerical/Statistical Error**: Wrong numbers, percentages, dates
4. **Misattribution**: Attributed to wrong source/person
5. **Overgeneralization**: Stated as universal when only partially true
6. **Conflation**: Mixed up two distinct concepts/events
7. **Omission of Critical Context**: Technically true but misleading
8. **Logical Fallacy**: Faulty reasoning leading to wrong conclusion
9. **Other**: Doesn't fit above categories

**Implementation Details**:
- Executes via `stage2_fact_check()` in `backend/council.py`
- Same models as council members perform fact-checking (different role)
- Each fact-checker evaluates ALL responses (N models × N responses evaluations)
- Parsing extracts structured summary via regex: `parse_fact_check_from_text()`
- Aggregate accuracy calculated across all fact-checkers for consensus view

**Aggregate Calculation**:
```python
# Converts ratings to numeric scores and averages
ACCURATE = 5
MOSTLY ACCURATE = 4
MIXED = 3
MOSTLY INACCURATE = 2
INACCURATE = 1

# Responses sorted by average accuracy score
```

**Model Requirements**:
- Strong factual knowledge across domains
- Ability to identify subtle inaccuracies
- Consistent adherence to output format
- Critical thinking skills to avoid false positives

---

### Peer Review Agents

**Purpose**: Rank all responses based on overall quality, incorporating fact-check findings.

**Stage**: Stage 3 (Peer Rankings)

**Capabilities**:
- Evaluate responses holistically (accuracy + completeness + clarity)
- Synthesize multiple fact-check analyses
- Weight factual accuracy appropriately in rankings
- Provide rankings in structured format
- Justify ranking decisions with reasoning

**Input Format** (Prompt Template):
```
You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

Response A:
{response_content_a}

Response B:
{response_content_b}

...

---

Here are the fact-check analyses from peer reviewers:

Fact-checker 1:
{fact_check_analysis_1}

Fact-checker 2:
{fact_check_analysis_2}

...

---

Your task:
1. Consider both the quality of each response AND the fact-check findings.
2. Evaluate each response individually, taking into account:
   - Factual accuracy (as revealed by the fact-checks)
   - Completeness and helpfulness
   - Clarity and reasoning
3. Then, at the very end of your response, provide a final ranking.

IMPORTANT: End your response with "FINAL RANKING:" followed by a numbered list.

Example format:

FINAL RANKING:
1. Response C
2. Response A
3. Response B
```

**Output Format**:
```json
{
  "model": "openai/gpt-5-nano",
  "instance": 0,
  "ranking": "Full evaluation text ending with FINAL RANKING: section...",
  "parsed_ranking": ["Response C", "Response A", "Response B"],
  "response_time_ms": 1823
}
```

**Aggregate Rankings**:
```python
# Calculate average position for each response across all rankers
# Response with lowest average position wins
# Example:
# Response A: Positions [1, 2, 1] → Average: 1.33
# Response B: Positions [2, 1, 3] → Average: 2.00
# Response C: Positions [3, 3, 2] → Average: 2.67
# Winner: Response A
```

**Implementation Details**:
- Executes via `stage3_collect_rankings()` in `backend/council.py`
- Receives full fact-check context from Stage 2
- Parsing extracts ranked list via regex: `parse_ranking_from_text()`
- Fallback parsing if format not followed: extract any "Response X" mentions in order
- Aggregate ranking calculated via average position: `calculate_aggregate_rankings()`

**Model Requirements**:
- Strong analytical and comparative reasoning
- Ability to synthesize multiple information sources
- Consistent ranking format adherence
- Balanced judgment (not overly harsh or lenient)

---

### Chairman Agent

**Purpose**: Synthesize all prior work into a comprehensive, fact-checked final answer.

**Stage**: Stage 4 (Chairman Synthesis)

**Capabilities**:
- Integrate insights from all council members
- Incorporate fact-check findings into synthesis
- Consider peer rankings in emphasis
- Validate fact-checkers themselves (meta-review)
- Produce authoritative, comprehensive answers
- Provide structured output with clear sections

**Configuration**:
```python
# In backend/config.py
CHAIRMAN_MODEL = "x-ai/grok-4-fast"
```

**Input Format** (Prompt Template):
```
You are the Chairman of an LLM Council that has deliberated on the following question:

Question: {user_query}

---

STAGE 1: INDIVIDUAL RESPONSES

Response A (from {model_name_a}):
{response_content_a}

Response B (from {model_name_b}):
{response_content_b}

...

---

STAGE 2: FACT-CHECK ANALYSES

Fact-checker 1 ({model_name_1}):
{fact_check_1}

Fact-checker 2 ({model_name_2}):
{fact_check_2}

...

Aggregate Accuracy Ratings (consensus across all fact-checkers):
{aggregate_accuracy_summary}

---

STAGE 3: PEER RANKINGS

Ranker 1 ({model_name_1}):
{ranking_1}

Ranker 2 ({model_name_2}):
{ranking_2}

...

Aggregate Rankings:
{aggregate_ranking_summary}

---

Your task as Chairman:

1. Synthesize the best insights from all responses
2. Validate the fact-check analyses themselves (did fact-checkers make errors?)
3. Produce a comprehensive, accurate final answer
4. Structure your response in THREE sections:

## Fact-Check Synthesis
[Summarize what was confirmed accurate/inaccurate across fact-checkers]

## Fact-Checker Validation
[Review the fact-checkers themselves - any errors in their analyses?]

## Final Council Answer
[Comprehensive, fact-validated answer incorporating all insights]
```

**Output Format**:
```json
{
  "synthesis": "## Fact-Check Synthesis\n...\n\n## Fact-Checker Validation\n...\n\n## Final Council Answer\n...",
  "chairman_model": "x-ai/grok-4-fast",
  "response_time_ms": 3456
}
```

**Implementation Details**:
- Executes via `stage4_synthesize_final()` in `backend/council.py`
- Receives complete context from all prior stages
- De-anonymization happens at this stage for transparency
- No parsing required (output is final formatted answer)
- Can be same or different model from council members

**Model Requirements**:
- Exceptional synthesis and reasoning capabilities
- Strong factual knowledge to validate fact-checkers
- Excellent writing clarity and structure
- Ability to handle long context (all prior stages as input)

---

## Agent Lifecycle

### Execution Flow

```
User Query
    ↓
┌─────────────────────────────────────────────────┐
│ Stage 1: Council Member Agents (Parallel)       │
│ - N agents answer independently                 │
│ - Responses stored with model IDs               │
│ - Reasoning details captured (if supported)     │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ Anonymization                                   │
│ - Responses labeled A, B, C, ...                │
│ - Mapping stored: label → model                 │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ Stage 2: Fact-Checker Agents (Parallel)         │
│ - Same N agents fact-check anonymized responses │
│ - Each evaluates ALL responses                  │
│ - Output: ratings + most reliable vote          │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ Aggregate Fact-Check Calculation                │
│ - Convert ratings to numeric scores             │
│ - Average across all fact-checkers              │
│ - Sort responses by accuracy                    │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ Stage 3: Peer Review Agents (Parallel)          │
│ - Same N agents rank responses                  │
│ - Context includes fact-check analyses          │
│ - Output: ordered ranking with justification    │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ Aggregate Ranking Calculation                   │
│ - Calculate average position for each response  │
│ - Sort by average position (lower = better)     │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ Stage 4: Chairman Agent (Single)                │
│ - Receives all prior context                    │
│ - Synthesizes final answer                      │
│ - Validates fact-checkers                       │
│ - Produces structured output                    │
└─────────────────────────────────────────────────┘
    ↓
Final Answer (with full transparency trail)
```

### State Management

**Ephemeral Metadata** (not persisted to storage):
- `label_to_model`: Anonymization mapping
- `aggregate_rankings`: Consensus rankings across peers
- `aggregate_fact_checks`: Consensus accuracy ratings across fact-checkers

**Persisted Data** (saved to `data/conversations/`):
```json
{
  "id": "conversation_id",
  "created_at": "2026-01-21T19:00:00Z",
  "messages": [
    {
      "role": "user",
      "content": "What causes climate change?"
    },
    {
      "role": "assistant",
      "stage1": [...],           // Council member responses
      "fact_check": [...],       // Fact-checker analyses
      "stage3": [...],           // Peer rankings
      "stage4": "..."            // Chairman synthesis
    }
  ]
}
```

### Error Handling

**Graceful Degradation**:
- If a council member fails → continue with remaining members
- If a fact-checker fails → continue with remaining fact-checkers
- If a peer reviewer fails → continue with remaining reviewers
- If chairman fails → return error (chairman is critical)
- If ALL agents of a type fail → return error for that stage

**Retry Logic**:
- No automatic retries (keeps system responsive)
- Failed queries logged but not exposed to user
- User can retry entire conversation if needed

**Validation**:
- Response format validation via regex parsing
- Fallback parsing for non-compliant formats
- Empty parsed results if format completely invalid

---

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
- Implementation: Render `reasoning_details` in frontend

**7. Adaptive Council Composition**
- Analyze question complexity
- Dynamically select optimal council members
- Adjust council size based on question type
- Implementation: Question classifier + routing logic

**8. Consensus Metrics**
- Measure agreement levels across council
- Flag high-controversy answers
- Provide confidence scores
- Implementation: Statistical analysis of rankings/ratings

### Long-Term Vision

**9. Specialized Sub-Councils**
- Math council for numerical questions
- Code council for programming questions
- Medical council for health questions
- Implementation: Question classifier + specialized configs

**10. Adversarial Testing**
- Dedicated "devil's advocate" agent
- Challenge consensus answers
- Identify blind spots in council
- Implementation: Stage 2.5 adversarial review

**11. Human-in-the-Loop Validation**
- Flag uncertain answers for human review
- Incorporate human feedback into agent prompts
- Build expert validation dataset
- Implementation: Confidence scoring + review queue

**12. Cross-Language Support**
- Multilingual council members
- Translation validation across languages
- Language-specific fact-checking
- Implementation: Language detection + specialized models

**13. Agent Learning**
- Track which prompts produce best results
- A/B test prompt variations
- Evolutionary prompt optimization
- Implementation: Prompt versioning + outcome tracking

**14. Export Formats**
- PDF with full deliberation trail
- Academic citation format
- API response format
- Implementation: Template-based export system

---

## Best Practices Summary

### Do's ✅

- **Use diverse council compositions** - Mix providers, sizes, and capabilities
- **Test prompt formats rigorously** - Agents must follow structured output
- **Implement graceful degradation** - Continue despite individual failures
- **Preserve transparency** - Show all agent outputs to users
- **Optimize for parallel execution** - Use asyncio for concurrent queries
- **Monitor aggregate metrics** - Track consensus across agents
- **Provide clear examples** - Show exact format expected in prompts
- **Balance cost and quality** - Use tiered approach (fast council + premium chairman)

### Don'ts ❌

- **Don't use only one provider** - Reduces diversity of perspectives
- **Don't skip fact-checking** - Core value proposition of the system
- **Don't hide agent identities** - Transparency builds trust
- **Don't fail on single agent failure** - System should degrade gracefully
- **Don't ignore parsing failures** - Implement fallback extraction
- **Don't hardcode model names in prompts** - Keep agents model-agnostic
- **Don't expose API keys** - Use environment variables only
- **Don't skip de-anonymization** - Users should see which models said what

---

## Conclusion

The LLM Council agent architecture demonstrates that **collective intelligence** can exceed individual model capabilities through:

1. **Structured deliberation** across four distinct stages
2. **Anonymized peer review** to eliminate bias
3. **Fact-checking layer** for accuracy verification
4. **Transparent validation** for user trust

By following the guidelines in this document, developers can effectively configure, deploy, and extend the council system for diverse use cases while maintaining the core principles of factual accuracy, transparency, and collaborative intelligence.

For technical implementation details, see [CLAUDE.md](CLAUDE.md).

For API usage and integration examples, see [SYNTHESIZE_API.md](SYNTHESIZE_API.md).

For security best practices, see [API_SECURITY.md](API_SECURITY.md).
