# LLM Council (Fact-Checker Fork)

![llmcouncil](header.jpg)

> **Fork Notice:** This project is a fork of [Andrej Karpathy's LLM Council](https://github.com/karpathy/llm-council). The original project implemented a 3-stage council process. This fork extends it with an additional **fact-checking stage** and an **error cataloging system** to track LLM accuracy over time.

The idea of this repo is that instead of asking a question to your favorite LLM provider (e.g. OpenAI GPT 5.1, Google Gemini 3.0 Pro, Anthropic Claude Sonnet 4.5, xAI Grok 4, eg.c), you can group them into your "LLM Council". This repo is a simple, local web app that essentially looks like ChatGPT except it uses OpenRouter to send your query to multiple LLMs, it then asks them to fact-check and rank each other's work, and finally a Chairman LLM produces the final response.

## How It Works

When you submit a query, the council goes through 4 stages:

1. **Stage 1: First Opinions** — The user query is sent to all council LLMs in parallel. Responses stream in real-time and are displayed in a grid view (or tab view), allowing you to watch each model think simultaneously.

2. **Stage 2: Fact-Checking** — Each council LLM receives all other models' anonymized responses and performs a detailed fact-check. They identify accurate claims, inaccurate claims, unverifiable claims, and missing information. Each fact-checker provides a reliability rating (ACCURATE → INACCURATE) and votes for the most reliable response.

3. **Stage 3: Peer Rankings** — Armed with the fact-check results, each LLM ranks all responses considering factual accuracy, completeness, and clarity. An aggregate ranking is calculated across all models.

4. **Stage 4: Chairman Synthesis** — The designated Chairman LLM synthesizes everything: the original responses, fact-check analyses, and peer rankings into a single, comprehensive, fact-validated final answer.

### Error Cataloging

As a bonus feature, the app automatically catalogs factual errors discovered during the fact-checking process. Errors are classified into types:

- Hallucinated Fact
- Outdated Information
- Numerical/Statistical Error
- Misattribution
- Overgeneralization
- Conflation
- Omission of Critical Context
- Logical Fallacy

You can view the error catalog from the sidebar to track which models make which types of errors over time.

## Vibe Code Alert

From the [original project](https://github.com/karpathy/llm-council) by Andrej Karpathy:

> This project was 99% vibe coded as a fun Saturday hack because I wanted to explore and evaluate a number of LLMs side by side in the process of [reading books together with LLMs](https://x.com/karpathy/status/1990577951671509438). It's nice and useful to see multiple responses side by side, and also the cross-opinions of all LLMs on each other's outputs. I'm not going to support it in any way, it's provided here as is for other people's inspiration and I don't intend to improve it. Code is ephemeral now and libraries are over, ask your LLM to change it in whatever way you like.

### What This Fork Adds

- **Stage 2: Fact-Checking** — A dedicated fact-checking stage where each LLM evaluates the accuracy of other models' responses
- **Error Cataloging** — Automatic classification and tracking of factual errors by type and model
- **Real-Time Streaming Grid** — Watch all models generate responses simultaneously in a grid layout
- **Dynamic Model Selection** — Choose council members and chairman from the UI sidebar

## Setup

### 1. Install Dependencies

The project uses [uv](https://docs.astral.sh/uv/) for Python project management.

**Backend:**
```bash
uv sync
```

**Frontend:**
```bash
cd frontend
npm install
cd ..
```

### 2. Configure API Key

Create a `.env` file in the project root:

```bash
OPENROUTER_API_KEY=sk-or-v1-...
```

Get your API key at [openrouter.ai](https://openrouter.ai/). Make sure to purchase the credits you need, or sign up for automatic top up.

### 3. Configure Models (Optional)

Edit `backend/config.py` to customize the council:

```python
# Council members who provide responses, fact-check, and rank
COUNCIL_MODELS = [
    "openai/gpt-5.1",
    "google/gemini-3-pro-preview",
    "anthropic/claude-sonnet-4.5",
    "x-ai/grok-4.1-fast:free",
]

# Chairman who synthesizes the final answer
CHAIRMAN_MODEL = "x-ai/grok-4.1-fast:free"
```

**Available models include:**
- OpenAI: GPT-5.1, GPT-5, GPT-4.1
- Google: Gemini 3 Pro, Gemini 2.5 Pro, Gemini 2.5 Flash
- Anthropic: Claude Sonnet 4.5, Claude Sonnet 4, Claude Haiku 4.5
- xAI: Grok 4.1 Fast (Free), Grok 4 Fast, Grok 4, Grok Code Fast 1
- Meta: Llama 4 Maverick, Llama 3.3 70B
- DeepSeek: DeepSeek V3, DeepSeek R1
- Mistral: Mistral Large

You can also select models dynamically from the UI sidebar.

### 4. Environment Variables (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | (required) | Your OpenRouter API key |
| `ERROR_CLASSIFICATION_ENABLED` | `true` | Enable/disable automatic error cataloging |

## Running the Application

**Option 1: Use the start script**
```bash
./start.sh
```

**Option 2: Run manually**

Terminal 1 (Backend):
```bash
uv run python -m backend.main
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

Then open http://localhost:5173 in your browser.

## Features

### Real-Time Streaming
Watch all council models generate their responses simultaneously in a grid view. Token-by-token streaming powered by Server-Sent Events.

### Model Selection
Use the sidebar to customize which models participate in the council and which model serves as chairman. Changes apply to your next query.

### Response Times
Each model response displays its generation time in milliseconds, helping you compare model latencies.

### Conversation History
All conversations are automatically saved and can be resumed later. Titles are auto-generated based on your first message.

### Error Catalog
Track factual errors across sessions. View error breakdowns by model and by error type to understand each model's strengths and weaknesses.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/api/models` | Get available models and defaults |
| `GET` | `/api/conversations` | List all conversations |
| `POST` | `/api/conversations` | Create new conversation |
| `GET` | `/api/conversations/{id}` | Get conversation with messages |
| `POST` | `/api/conversations/{id}/message` | Send message (non-streaming) |
| `POST` | `/api/conversations/{id}/message/stream` | Send message with SSE streaming |
| `GET` | `/api/errors` | Get error catalog with summary |
| `DELETE` | `/api/errors` | Clear error catalog |

## Tech Stack

- **Backend:** FastAPI (Python 3.10+), async httpx, Pydantic, OpenRouter API
- **Frontend:** React 19 + Vite 7, react-markdown for rendering
- **Storage:** JSON files in `data/conversations/` and `data/error_catalog.json`
- **Package Management:** uv for Python, npm for JavaScript
- **Deployment:** Render.com (see Deployment section below)

## Deployment to Render

This repository includes a `render.yaml` blueprint for easy deployment to [Render.com](https://render.com).

### Quick Deploy

1. **Fork this repository** to your own GitHub account

2. **Create a new Blueprint** on Render:
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New" → "Blueprint"
   - Connect your GitHub repository
   - Render will automatically detect `render.yaml`

3. **Set the OPENROUTER_API_KEY secret**:
   - After the blueprint is created, go to the `llm-council-api` service
   - Navigate to "Environment" tab
   - Add your `OPENROUTER_API_KEY` value (marked as `sync: false` for security)

4. **Deploy** - Render will automatically build and deploy both services

### Services Created

The blueprint creates two services:

| Service | Type | URL |
|---------|------|-----|
| `llm-council-api` | Web Service (Python) | `https://llm-council-api.onrender.com` |
| `llm-council-frontend` | Static Site | `https://llm-council-frontend.onrender.com` |

### Environment Variables

#### Backend (`llm-council-api`)
| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | Your OpenRouter API key (set manually in Render dashboard) |
| `PYTHON_VERSION` | No | Python version (defaults to 3.11) |
| `ERROR_CLASSIFICATION_ENABLED` | No | Enable error cataloging (defaults to true) |
| `FRONTEND_URL` | No | Frontend URL for CORS (auto-configured in blueprint) |

#### Frontend (`llm-council-frontend`)
| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_URL` | Yes | Backend API URL (auto-configured in blueprint) |

### Custom Domain

To use a custom domain:
1. Add your domain in the Render dashboard for each service
2. Update the `FRONTEND_URL` environment variable on the backend
3. Update the `VITE_API_URL` environment variable on the frontend (requires rebuild)

## Project Structure

```
llm-council-fact-checker/
├── backend/
│   ├── main.py          # FastAPI app and routes
│   ├── council.py       # 4-stage orchestration logic
│   ├── openrouter.py    # OpenRouter API client
│   ├── storage.py       # Conversation persistence
│   ├── error_catalog.py # Error tracking
│   └── config.py        # Models and settings
├── frontend/
│   └── src/
│       ├── App.jsx              # Main app with streaming state
│       ├── api.js               # Backend API client
│       └── components/
│           ├── ChatInterface.jsx   # Main chat view
│           ├── Sidebar.jsx         # Navigation + model selector
│           ├── StreamingGrid.jsx   # Real-time grid view
│           ├── Stage1-4.jsx        # Stage result displays
│           ├── FactCheck.jsx       # Fact-check visualization
│           └── ErrorCatalog.jsx    # Error tracking view
├── data/
│   └── conversations/   # Saved conversation JSON files
├── render.yaml          # Render.com deployment blueprint
├── requirements.txt     # Python dependencies for deployment
├── start.sh             # Launch both servers locally
└── pyproject.toml       # Python project configuration
```

## Credits

This project is based on [LLM Council](https://github.com/karpathy/llm-council) by [Andrej Karpathy](https://github.com/karpathy). The original 3-stage council concept and core architecture are his work. This fork adds fact-checking capabilities and error tracking features.
