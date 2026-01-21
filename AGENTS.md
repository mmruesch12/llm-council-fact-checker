# AGENTS.md - LLM Council Agent Architecture

**Purpose**: This index provides an overview and navigation to detailed agent architecture documentation. Each section is loaded independently to minimize context usage.

## Quick Start

For a high-level understanding, see [Overview](docs/agents/overview.md).

For implementation details, see [CLAUDE.md](CLAUDE.md) (technical notes) and [SYNTHESIZE_API.md](SYNTHESIZE_API.md) (API usage).

## Architecture Overview

The LLM Council is a multi-agent deliberative system with four stages:

1. **Stage 1**: Council Member Agents provide independent responses
2. **Stage 2**: Fact-Checker Agents verify accuracy of all responses
3. **Stage 3**: Peer Review Agents rank responses based on quality
4. **Stage 4**: Chairman Agent synthesizes final fact-checked answer

📖 [Read full overview →](docs/agents/overview.md)

## Agent Types

Each agent type has specific responsibilities, capabilities, and requirements:

### Council Member Agents (Stage 1)
Provide initial independent responses to user queries.
- **Configuration**: Set in `backend/config.py` as `COUNCIL_MODELS`
- **Parallel Execution**: All models query simultaneously
- **Reasoning Support**: Grok models include step-by-step thinking

📖 [Full specifications →](docs/agents/council-member-agents.md)

### Fact-Checker Agents (Stage 2)
Verify factual accuracy of anonymized responses.
- **Anonymization**: Responses labeled A, B, C to prevent bias
- **Rating Scale**: ACCURATE → MOSTLY ACCURATE → MIXED → MOSTLY INACCURATE → INACCURATE
- **Error Classification**: 9 predefined error types tracked

📖 [Full specifications →](docs/agents/fact-checker-agents.md)

### Peer Review Agents (Stage 3)
Rank responses based on accuracy, completeness, and clarity.
- **Context-Aware**: Incorporates fact-check findings in rankings
- **Aggregate Rankings**: Calculates average position across all reviewers
- **Output Format**: Structured "FINAL RANKING:" with numbered list

📖 [Full specifications →](docs/agents/peer-review-agents.md)

### Chairman Agent (Stage 4)
Synthesizes comprehensive final answer from all prior work.
- **Meta-Review**: Validates fact-checkers themselves
- **Structured Output**: Fact-Check Synthesis + Fact-Checker Validation + Final Answer
- **Model Selection**: Can differ from council members (often premium model)

📖 [Full specifications →](docs/agents/chairman-agent.md)

## Implementation Guides

### Agent Lifecycle
Complete execution flow, state management, and error handling strategies.

📖 [View lifecycle details →](docs/agents/lifecycle.md)

### Technical Specifications
Parallel execution patterns, streaming support, reasoning mode, performance characteristics.

📖 [View technical specs →](docs/agents/technical-specs.md)

### Prompt Engineering
Guidelines for format enforcement, domain-specific prompting, and anti-bias techniques.

📖 [View prompt engineering guide →](docs/agents/prompt-engineering.md)

### Model Selection
Best practices for council composition, chairman selection, cost optimization, and performance tuning.

📖 [View model selection guide →](docs/agents/model-selection.md)

## Integration & Extension

### Integration Patterns
External API usage, application embedding, and custom agent implementations.

📖 [View integration patterns →](docs/agents/integration-patterns.md)

### Future Enhancements
Roadmap for short, medium, and long-term improvements.

📖 [View enhancement roadmap →](docs/agents/future-enhancements.md)

### Best Practices
Do's and Don'ts summary with common pitfalls to avoid.

📖 [View best practices →](docs/agents/best-practices.md)

## Key Concepts

### Anonymization
- Responses presented as "Response A", "Response B", etc.
- Model identities hidden during fact-checking and ranking
- De-anonymization happens client-side for display transparency

### Graceful Degradation
- System continues if individual agents fail
- Returns partial results rather than failing completely
- Logged errors don't block progress

### Parallel Execution
- Agents of same type run simultaneously using `asyncio.gather()`
- Total latency ≈ 4× single query (not 4N×)
- Supports streaming for real-time updates

## Related Documentation

- **[CLAUDE.md](CLAUDE.md)** - Technical implementation details and gotchas
- **[SYNTHESIZE_API.md](SYNTHESIZE_API.md)** - API usage guide for `/api/synthesize`
- **[API_SECURITY.md](API_SECURITY.md)** - Security best practices
- **[README.md](README.md)** - Project overview and setup instructions

## Contributing

When extending the agent system:

1. **Maintain format compatibility** - Agents rely on structured output parsing
2. **Preserve anonymization** - Prevents bias in fact-checking and ranking
3. **Test graceful degradation** - Ensure system handles failures gracefully
4. **Update documentation** - Keep relevant sections in `docs/agents/` up to date

---

*This modular documentation structure enables lazy loading - agents can reference specific sections as needed without loading the entire context.*
