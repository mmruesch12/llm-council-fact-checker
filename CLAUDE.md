# CLAUDE.md - Technical Notes for LLM Council

This file contains technical details, architectural decisions, and important implementation notes for future development sessions.

## Project Overview

LLM Council is a **4-stage deliberation system** where multiple LLMs collaboratively answer user questions. The key innovations are:
1. **Anonymized peer review** - models can't play favorites
2. **Fact-checking stage** - models verify each other's claims before ranking
3. **Chairman validation** - final synthesis includes fact-check analysis and validation

## The 4-Stage Process

1. **Stage 1: Individual Responses** - All council models answer the user's question independently
2. **Stage 2: Fact-Checking** - Each model fact-checks all other responses (anonymized)
3. **Stage 3: Peer Rankings** - Models rank responses after seeing fact-check analyses
4. **Stage 4: Chairman Synthesis** - Chairman synthesizes final answer with fact-check validation

## Architecture

### Backend Structure (`backend/`)

**`config.py`**
- Contains `COUNCIL_MODELS` (list of OpenRouter model identifiers)
- Contains `CHAIRMAN_MODEL` (model that synthesizes final answer)
- Uses environment variable `OPENROUTER_API_KEY` from `.env`
- Backend runs on **port 8001** (NOT 8000 - user had another app on 8000)

**`openrouter.py`**
- `query_model()`: Single async model query
- `query_models_parallel()`: Parallel queries using `asyncio.gather()`
- Returns dict with 'content' and optional 'reasoning_details'
- Graceful degradation: returns None on failure, continues with successful responses

**`council.py`** - The Core Logic
- `stage1_collect_responses()`: Parallel queries to all council models
- `stage2_fact_check()`:
  - Anonymizes responses as "Response A, B, C, etc."
  - Creates `label_to_model` mapping for de-anonymization
  - Prompts models to fact-check each response with strict format requirements
  - Returns tuple: (fact_check_list, label_to_model_dict)
  - Each fact-check includes raw text and `parsed_summary` with ratings
- `stage3_collect_rankings()`:
  - Takes fact-check results as input context
  - Models rank responses informed by fact-check analyses
  - Returns rankings with `parsed_ranking` list
- `stage4_synthesize_final()`: Chairman synthesizes with:
  - Fact-check synthesis (what was confirmed accurate/inaccurate)
  - Fact-checker validation (reviewing the fact-checkers themselves)
  - Final comprehensive answer
- `parse_ranking_from_text()`: Extracts "FINAL RANKING:" section
- `parse_fact_check_from_text()`: Extracts "FACT CHECK SUMMARY:" section with ratings
- `calculate_aggregate_rankings()`: Computes average rank position across all peer evaluations
- `calculate_aggregate_fact_checks()`: Computes consensus accuracy ratings across all fact-checkers

**`storage.py`**
- Abstraction layer that supports both SQLite and JSON backends
- Backend selection controlled by `USE_SQLITE_DB` config flag (defaults to true)
- For SQLite: delegates to `database.py` functions
- For JSON: legacy file-based storage in `data/conversations/`
- Each conversation: `{id, created_at, messages[]}`
- Assistant messages contain: `{role, stage1, fact_check, stage3, stage4}`
- Note: metadata (label_to_model, aggregate_rankings, aggregate_fact_checks) is NOT persisted to storage, only returned via API

**`database.py`** (NEW)
- SQLite implementation for conversation and error storage
- Tables: conversations, messages, errors (see README for full schema)
- Context manager `get_db()` for proper connection handling
- All CRUD operations with proper indexes for performance
- Stores stage data as JSON text in message columns
- Supports concurrent access with ACID compliance

**`error_catalog.py`**
- Abstraction layer that supports both SQLite and JSON backends
- Backend selection controlled by `USE_SQLITE_DB` config flag
- For SQLite: delegates to `database.py` functions
- For JSON: legacy file-based storage in `data/error_catalog.json`

**`migrate_to_sqlite.py`** (NEW)
- Migration utility to convert JSON data to SQLite
- Backs up existing JSON files before migration
- Verifies migration success
- Can be run with: `python -m backend.migrate_to_sqlite`

**`main.py`**
- FastAPI app with CORS enabled for localhost:5173 and localhost:3000
- POST `/api/conversations/{id}/message` returns metadata in addition to stages
- Streaming endpoint sends events: `stage1_start/complete`, `fact_check_start/complete`, `stage3_start/complete`, `stage4_start/complete`
- Metadata includes: label_to_model mapping, aggregate_rankings, and aggregate_fact_checks

### Frontend Structure (`frontend/src/`)

**`App.jsx`**
- Main orchestration: manages conversations list and current conversation
- Handles message sending and metadata storage
- Streaming event handlers for all 4 stages
- Important: metadata is stored in the UI state for display but not persisted to backend JSON

**`components/ChatInterface.jsx`**
- Multiline textarea (3 rows, resizable)
- Enter to send, Shift+Enter for new line
- User messages wrapped in markdown-content class for padding
- Renders Stage1, FactCheck, Stage3, Stage4 components

**`components/Stage1.jsx`**
- Tab view of individual model responses
- ReactMarkdown rendering with markdown-content wrapper

**`components/FactCheck.jsx`** (NEW)
- **Aggregate Accuracy Ratings**: Shows consensus ratings across all fact-checkers
- Tab view showing raw fact-check analysis from each model
- De-anonymization happens CLIENT-SIDE for display
- Shows "Extracted Summary" with parsed ratings and most_reliable designation
- Color-coded rating badges: ACCURATE (green) to INACCURATE (red)

**`components/Stage3.jsx`**
- Tab view showing ranking evaluations from each model
- Informed by fact-check analyses
- Shows "Extracted Ranking" below each evaluation
- Aggregate rankings shown with average position and vote count

**`components/Stage4.jsx`**
- Final synthesized answer from chairman
- Includes Fact-Check Synthesis, Fact-Checker Validation, and Final Council Answer
- Green-tinted background (#f0fff0) to highlight conclusion

**Styling (`*.css`)**
- Light mode theme (not dark mode)
- Primary color: #4a90e2 (blue)
- Fact-check stage uses orange/amber theme (#ffa500, #ffd966)
- Global markdown styling in `index.css` with `.markdown-content` class
- 12px padding on all markdown content to prevent cluttered appearance

## Key Design Decisions

### Stage 2 Fact-Check Prompt Format
The fact-check prompt requires specific output:
```
1. For each response, identify:
   - Accurate Claims
   - Inaccurate Claims (with explanations)
   - Unverifiable Claims
   - Missing Important Information

2. End with "FACT CHECK SUMMARY:" section
3. Rate each response: ACCURATE / MOSTLY ACCURATE / MIXED / MOSTLY INACCURATE / INACCURATE
4. Designate "MOST RELIABLE: Response X"
```

### Stage 3 Ranking Prompt Format
The ranking prompt is informed by fact-checks:
```
1. Consider both quality and fact-check findings
2. Provide "FINAL RANKING:" header
3. Numbered list format: "1. Response C", "2. Response A", etc.
```

### Stage 4 Chairman Synthesis Format
The chairman must provide structured output:
```
## Fact-Check Synthesis
[Analysis of what was confirmed accurate/inaccurate across fact-checkers]

## Fact-Checker Validation
[Review of the fact-checkers themselves - any errors in their analyses]

## Final Council Answer
[Comprehensive, fact-checked answer]
```

### De-anonymization Strategy
- Models receive: "Response A", "Response B", etc.
- Backend creates mapping: `{"Response A": "openai/gpt-5.1", ...}`
- Frontend displays model names in **bold** for readability
- Users see explanation that original evaluation used anonymous labels
- This prevents bias while maintaining transparency

### Error Handling Philosophy
- Continue with successful responses if some models fail (graceful degradation)
- Never fail the entire request due to single model failure
- Log errors but don't expose to user unless all models fail

### UI/UX Transparency
- All raw outputs are inspectable via tabs
- Parsed fact-check summaries and rankings shown below raw text for validation
- Users can verify system's interpretation of model outputs
- This builds trust and allows debugging of edge cases

## Important Implementation Details

### Relative Imports
All backend modules use relative imports (e.g., `from .config import ...`) not absolute imports. This is critical for Python's module system to work correctly when running as `python -m backend.main`.

### Port Configuration
- Backend: 8001 (changed from 8000 to avoid conflict)
- Frontend: 5173 (Vite default)
- Update both `backend/main.py` and `frontend/src/api.js` if changing

### Markdown Rendering
All ReactMarkdown components must be wrapped in `<div className="markdown-content">` for proper spacing. This class is defined globally in `index.css`.

### Model Configuration
Models are hardcoded in `backend/config.py`. Chairman can be same or different from council members. The current default is Gemini as chairman per user preference.

### Database Backend
- SQLite is used by default (`USE_SQLITE_DB=true` in config)
- Database file: `llm_council.db` at project root
- For migration from JSON: `python -m backend.migrate_to_sqlite`
- Both backends share the same interface via `storage.py` and `error_catalog.py`

## Common Gotchas

1. **Module Import Errors**: Always run backend as `python -m backend.main` from project root, not from backend directory
2. **CORS Issues**: Frontend must match allowed origins in `main.py` CORS middleware
3. **Ranking Parse Failures**: If models don't follow format, fallback regex extracts any "Response X" patterns in order
4. **Fact-Check Parse Failures**: If models don't follow format, ratings dict may be empty
5. **Missing Metadata**: Metadata is ephemeral (not persisted), only available in API responses

## Future Enhancement Ideas

- Configurable council/chairman via UI instead of config file
- Model performance analytics over time
- Custom fact-checking criteria for different domains
- Support for reasoning models (o1, etc.) with special handling
- Web search integration for fact-checking
- Export to PDF format (currently supports Markdown)

## Testing Notes

Use `test_openrouter.py` to verify API connectivity and test different model identifiers before adding to council. The script tests both streaming and non-streaming modes.

Use `test_database.py` to verify SQLite database functionality. The script tests conversation and error catalog CRUD operations.

## Data Flow Summary

```
User Query
    ↓
Stage 1: Parallel queries → [individual responses]
    ↓
Stage 2: Anonymize → Parallel fact-check queries → [fact_checks + parsed_summaries]
    ↓
Aggregate Fact-Check Calculation → [sorted by accuracy score]
    ↓
Stage 3: Parallel ranking queries (with fact-check context) → [rankings + parsed_rankings]
    ↓
Aggregate Rankings Calculation → [sorted by avg position]
    ↓
Stage 4: Chairman synthesis with full context + fact-check validation
    ↓
Return: {stage1, fact_check, stage3, stage4, metadata}
    ↓
Storage: Save to SQLite (or JSON if USE_SQLITE_DB=false)
    ↓
Frontend: Display with tabs + validation UI for each stage
```

The entire flow is async/parallel where possible to minimize latency.
