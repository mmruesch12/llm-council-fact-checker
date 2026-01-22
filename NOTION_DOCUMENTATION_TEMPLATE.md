# LLM Council Fact-Checker - Documentation Template for Notion

This template contains the structured content that would be created in Notion once the MCP integration is properly configured.

---

# LLM Council Fact-Checker
**High-Level Technical Overview**

## 📋 Overview

The LLM Council Fact-Checker is a multi-agent deliberative system that brings together multiple Large Language Models to collaboratively answer questions through a rigorous 4-stage fact-checking and synthesis process.

**Original Project**: Fork of [Andrej Karpathy's LLM Council](https://github.com/karpathy/llm-council)

**Key Innovation**: Instead of asking a single LLM, queries are sent to a "council" of models that independently respond, fact-check each other, peer-review the responses, and synthesize a final validated answer.

## 🎯 Core Concept

Traditional approach:
```
User Question → Single LLM → Answer
```

LLM Council approach:
```
User Question → Multiple LLMs → Fact-Checking → Peer Review → Synthesized Answer
```

## 🔄 The 4-Stage Process

### Stage 1: Individual Responses
- **What happens**: User query is sent to all council LLMs in parallel
- **Output**: Independent responses from each model (e.g., GPT-5, Gemini, Claude, Grok)
- **Features**: 
  - Real-time streaming of responses
  - Token-by-token display in grid view
  - Response time tracking for each model

### Stage 2: Fact-Checking
- **What happens**: Each council LLM receives all responses (anonymized as Response A, B, C, etc.)
- **Task**: Identify accurate claims, inaccurate claims, unverifiable claims, and missing information
- **Output**: 
  - Detailed fact-check analysis for each response
  - Accuracy ratings (ACCURATE → MOSTLY ACCURATE → MIXED → MOSTLY INACCURATE → INACCURATE)
  - Designation of "most reliable" response
- **Key Feature**: Anonymization prevents bias (models don't know which response came from which competitor)

### Stage 3: Peer Rankings
- **What happens**: Each LLM ranks all responses considering both quality and fact-check findings
- **Context**: Models have access to all fact-check analyses from Stage 2
- **Output**:
  - Ranked list from each model
  - Aggregate rankings with average positions
  - Vote counts for top positions

### Stage 4: Chairman Synthesis
- **What happens**: A designated "Chairman" LLM synthesizes the final answer
- **Inputs**: Original responses, fact-check analyses, peer rankings
- **Output Structure**:
  1. **Fact-Check Synthesis**: What was confirmed accurate/inaccurate
  2. **Fact-Checker Validation**: Review of the fact-checkers themselves
  3. **Final Council Answer**: Comprehensive, fact-validated response

## ✨ Key Features

### Real-Time Streaming
- Watch all council models generate responses simultaneously
- Grid view shows token-by-token streaming
- Powered by Server-Sent Events (SSE)

### Anonymized Evaluation
- Responses labeled as "Response A", "Response B", etc. during fact-checking
- Prevents models from favoring or discriminating against specific competitors
- De-anonymization happens client-side for transparency

### Error Cataloging System
Automatically tracks and classifies factual errors into 9 categories:
1. **Hallucinated Fact** - Completely fabricated information
2. **Outdated Information** - Correct in the past, now obsolete
3. **Numerical/Statistical Error** - Wrong numbers or statistics
4. **Misattribution** - Incorrectly attributed quotes or ideas
5. **Overgeneralization** - Broad claims without nuance
6. **Conflation** - Merging distinct concepts incorrectly
7. **Omission of Critical Context** - Missing important qualifications
8. **Logical Fallacy** - Flawed reasoning patterns
9. **Other** - Errors not fitting other categories

**Analytics**: Track error patterns by model and by error type over time

### Dynamic Model Selection
- Choose council members from UI sidebar
- Select chairman model independently
- Changes apply to next query
- Default configuration in `backend/config.py`

### Conversation Management
- Auto-save all conversations
- Auto-generated titles from first message
- Resume previous conversations
- Export to Markdown with full formatting

## 🏗️ Technical Architecture

### Backend (Python)
**Framework**: FastAPI (Python 3.10+)

**Core Modules**:
- `main.py` - FastAPI app, routes, and CORS configuration
- `council.py` - 4-stage orchestration logic
- `openrouter.py` - OpenRouter API client with streaming support
- `storage.py` - JSON-based conversation persistence
- `error_catalog.py` - Error tracking and classification
- `auth.py` - GitHub OAuth authentication
- `api_key_auth.py` - API key validation for external access

**Key Technologies**:
- async/await pattern with `asyncio.gather()` for parallel execution
- Server-Sent Events (SSE) for real-time streaming
- Pydantic for data validation
- OpenRouter for multi-model API access

### Frontend (React)
**Framework**: React 19 + Vite 7

**Core Components**:
- `App.jsx` - Main orchestration and state management
- `ChatInterface.jsx` - Chat UI with multiline input
- `StreamingGrid.jsx` - Real-time grid view of responses
- `Stage1-4.jsx` - Display components for each stage
- `FactCheck.jsx` - Fact-check visualization with color-coded ratings
- `ErrorCatalog.jsx` - Error analytics dashboard
- `Sidebar.jsx` - Navigation and model selection

**Key Features**:
- ReactMarkdown for formatted output
- Context API for auth and theme state
- Server-Sent Events for streaming
- Tab-based navigation for multi-model views

### Data Storage
**Format**: JSON files

**Structure**:
```
data/
├── conversations/
│   ├── {uuid}.json  # Individual conversation files
│   └── ...
└── error_catalog.json  # Aggregated error data
```

**Conversation Schema**:
```json
{
  "id": "uuid",
  "created_at": "ISO timestamp",
  "messages": [
    {
      "role": "user",
      "content": "question"
    },
    {
      "role": "assistant",
      "stage1": [...],
      "fact_check": [...],
      "stage3": [...],
      "stage4": "..."
    }
  ]
}
```

## 🔐 Security Features

### Authentication Methods

**1. GitHub OAuth (Web UI)**
- Session-based authentication
- Allow-list of GitHub usernames
- Secure cookie management
- Automatic session expiry

**2. API Key Authentication (External Access)**
- Protect `/api/synthesize` and error endpoints
- Keys prefixed with `sk-council-`
- Support for multiple keys
- Header-based authentication: `X-API-Key`

### Security Layers
- **Rate Limiting**: 10 req/min for expensive endpoints, 60 req/min for others
- **Request Size Validation**: 50KB limit to prevent abuse
- **Security Headers**: OWASP-recommended headers on all responses
- **CORS Protection**: Strict origin validation
- **Input Validation**: Pydantic models for all API requests

### Environment Variables
```bash
# Required
OPENROUTER_API_KEY=sk-or-v1-...

# Authentication (Optional)
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret
ALLOWED_GITHUB_USERS=username1,username2
API_KEYS=sk-council-...,sk-council-...

# Configuration
ERROR_CLASSIFICATION_ENABLED=true
RATE_LIMIT_GENERAL=60
RATE_LIMIT_EXPENSIVE=10
```

## 🌐 API Endpoints

### Core Endpoints
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| `GET` | `/` | Health check | No |
| `GET` | `/api/models` | Available models and defaults | No |
| `POST` | `/api/synthesize` | Synthesize answer from responses | API Key (if configured) |
| `GET` | `/api/conversations` | List all conversations | Session |
| `POST` | `/api/conversations` | Create new conversation | Session |
| `GET` | `/api/conversations/{id}` | Get conversation with messages | Session |
| `POST` | `/api/conversations/{id}/message` | Send message (non-streaming) | Session |
| `POST` | `/api/conversations/{id}/message/stream` | Send message with SSE | Session |
| `GET` | `/api/conversations/{id}/export` | Export to Markdown | Session |
| `GET` | `/api/errors` | Get error catalog | API Key (if configured) |
| `DELETE` | `/api/errors` | Clear error catalog | API Key (if configured) |

### Authentication Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/auth/status` | Check if auth is enabled |
| `GET` | `/auth/login` | Initiate GitHub OAuth flow |
| `GET` | `/auth/callback` | OAuth callback handler |
| `GET` | `/auth/me` | Get current user |
| `GET/POST` | `/auth/logout` | Log out |

### `/api/synthesize` - External Integration Endpoint

**Purpose**: Allow external applications to get fact-checked synthesis from the LLM Council

**Two Modes**:

1. **Fast Path** (with pre-provided responses):
```json
{
  "question": "What causes climate change?",
  "responses": [
    {"model": "gpt-5", "content": "..."},
    {"model": "gemini", "content": "..."}
  ],
  "chairman_model": "x-ai/grok-4-fast"
}
```

2. **Full Council** (generate responses):
```json
{
  "question": "What causes climate change?",
  "council_models": ["model1", "model2"],
  "fact_checking_enabled": true,
  "include_metadata": true
}
```

**Response**:
```json
{
  "answer": "Synthesized answer...",
  "chairman_model": "x-ai/grok-4-fast",
  "metadata": {
    "responses_provided": 3,
    "fact_checking_enabled": false,
    "full_council_run": false
  }
}
```

## 🚀 Deployment

### Local Development
```bash
# Backend (port 8001)
uv run python -m backend.main

# Frontend (port 5173)
cd frontend && npm run dev
```

### Production (Render.com)
- Uses `render.yaml` blueprint
- Automatic deployment from GitHub
- Two services:
  - `llm-council-api` (Web Service)
  - `llm-council-frontend` (Static Site)
- Environment variables configured via Render dashboard

## 📊 Performance Characteristics

### Latency Profile
- **Stage 1**: ~2-5 seconds (parallel execution of all models)
- **Stage 2**: ~3-6 seconds (parallel fact-checking)
- **Stage 3**: ~2-4 seconds (parallel ranking)
- **Stage 4**: ~2-5 seconds (chairman synthesis)
- **Total**: ~9-20 seconds (depends on model speeds)

### Cost Optimization
- Parallel execution minimizes total latency (4× single query, not 4N×)
- Graceful degradation if individual models fail
- Optional fact-checking toggle to reduce API calls
- Configurable model selection (mix of fast/premium models)

### Scalability
- Stateless design (JSON file storage)
- Async/await throughout for I/O efficiency
- No database overhead
- Horizontal scaling possible with shared storage

## 🔧 Configuration

### Default Model Setup
**Location**: `backend/config.py`

```python
COUNCIL_MODELS = [
    "google/gemini-3-flash-preview",
    "x-ai/grok-4-fast",
    "x-ai/grok-4.1-fast",
    "openai/gpt-5-nano",
]

CHAIRMAN_MODEL = "x-ai/grok-4-fast"
```

### Supported Model Families
- **OpenAI**: GPT-5.1, GPT-5, GPT-4.1
- **Google**: Gemini 3 Pro, Gemini 2.5 Pro/Flash
- **Anthropic**: Claude Sonnet 4.5, Claude 4, Claude Haiku 4.5
- **xAI**: Grok 4.1 Fast, Grok 4 Fast, Grok 4, Grok Code Fast 1
- **Meta**: Llama 4 Maverick, Llama 3.3 70B
- **DeepSeek**: DeepSeek V3, DeepSeek R1
- **Mistral**: Mistral Large

## 💡 Use Cases

### Research & Analysis
- Get multiple expert perspectives on complex topics
- Fact-check claims across different knowledge bases
- Identify consensus and disagreement among models

### Content Creation
- Generate well-researched, fact-validated content
- Get diverse viewpoints for balanced writing
- Catch errors before publication

### Decision Support
- Evaluate options from multiple analytical angles
- Identify potential risks and overlooked factors
- Synthesize comprehensive recommendations

### Education
- Understand topics from different explanatory approaches
- See how different models reason through problems
- Learn from fact-checking process

### API Integration
- Add fact-checked synthesis to existing applications
- Batch process questions with validation
- Build custom workflows on top of council logic

## 📈 Future Enhancements

### Short-Term
- Web search integration for real-time fact verification
- Custom fact-checking criteria per domain
- Export to PDF format
- Model performance analytics dashboard

### Medium-Term
- Multi-turn conversation support with reasoning continuity
- Customizable council composition per query type
- Integration with external knowledge bases
- Enhanced error pattern analysis

### Long-Term
- Specialized councils for different domains (medical, legal, technical)
- Community-contributed model evaluation datasets
- Automated model selection based on query characteristics
- Federation with other council instances

## 🤝 Contributing

When extending the system:

1. **Maintain format compatibility** - Agents rely on structured output parsing
2. **Preserve anonymization** - Critical for unbiased fact-checking
3. **Test graceful degradation** - System should handle partial failures
4. **Update documentation** - Keep technical docs synchronized

## 📚 Related Documentation

- **[README.md](README.md)** - Setup and quickstart guide
- **[AGENTS.md](AGENTS.md)** - Agent architecture overview
- **[CLAUDE.md](CLAUDE.md)** - Technical implementation details
- **[SYNTHESIZE_API.md](SYNTHESIZE_API.md)** - External API integration guide
- **[API_SECURITY.md](API_SECURITY.md)** - Security best practices

## 🏷️ Project Metadata

**Repository**: [mmruesch12/llm-council-fact-checker](https://github.com/mmruesch12/llm-council-fact-checker)

**Original Project**: [karpathy/llm-council](https://github.com/karpathy/llm-council)

**License**: MIT (inherited from original project)

**Status**: Active Development

**Version**: Fork with extended fact-checking capabilities

---

*This documentation provides a high-level technical overview of the LLM Council Fact-Checker system. For detailed implementation notes, see the technical documentation files in the repository.*
