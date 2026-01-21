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

