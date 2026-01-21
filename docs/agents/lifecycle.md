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

