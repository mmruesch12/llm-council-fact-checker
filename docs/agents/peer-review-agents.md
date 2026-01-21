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
