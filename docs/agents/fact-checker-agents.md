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
