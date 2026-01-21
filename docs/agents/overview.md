# Overview

The LLM Council is a **multi-agent deliberative system** that uses four distinct types of AI agents working in sequence to produce fact-checked, peer-reviewed answers to user questions. Unlike traditional single-LLM systems, this architecture leverages:

1. **Collective Intelligence**: Multiple models with different strengths contribute perspectives
2. **Anonymized Peer Review**: Prevents bias through blind evaluation
3. **Fact-Checking Layer**: Dedicated accuracy verification before final synthesis
4. **Transparent Validation**: All intermediate steps are visible for user trust

## Core Principles

- **Graceful Degradation**: System continues if individual agents fail
- **Parallel Execution**: Agents of the same type run simultaneously for speed
- **Structured Output**: Agents follow strict formatting requirements for parsing
- **Model Agnosticism**: Any OpenRouter-compatible model can serve as any agent type
