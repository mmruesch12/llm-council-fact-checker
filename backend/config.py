"""Configuration for the LLM Council."""

import os
import secrets
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# GitHub OAuth Configuration
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

# Secret key for session signing
# Generate a random key if not provided (note: sessions won't persist across restarts)
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY") or secrets.token_hex(32)

# Whether to use secure cookies (should be True in production with HTTPS)
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"

# Allowed GitHub usernames (comma-separated list in env var)
# If empty or not set, authentication is disabled
ALLOWED_GITHUB_USERS = [
    u.strip() for u in os.getenv("ALLOWED_GITHUB_USERS", "").split(",") if u.strip()
]

# Frontend URL for OAuth callback redirect
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# OAuth callback URL (explicitly set for production, auto-detected in development)
# Should be set to backend URL, e.g., https://llm-council-api-9zfj.onrender.com/auth/callback
OAUTH_CALLBACK_URL = os.getenv("OAUTH_CALLBACK_URL")

# API Key Authentication Configuration
# API keys for external API access (comma-separated list)
# Format: sk-council-<64 hex characters>
# If not set, API key authentication is optional but recommended for /api/synthesize
API_KEYS = os.getenv("API_KEYS", "")

# Rate Limiting Configuration
# Maximum requests per minute for general endpoints
RATE_LIMIT_GENERAL = int(os.getenv("RATE_LIMIT_GENERAL", "60"))

# Maximum requests per minute for expensive endpoints (LLM API calls)
RATE_LIMIT_EXPENSIVE = int(os.getenv("RATE_LIMIT_EXPENSIVE", "10"))

# Council members - list of OpenRouter model identifiers
COUNCIL_MODELS = [
    "openai/gpt-5.1",
    "google/gemini-3-pro-preview",
    "anthropic/claude-sonnet-4.5",
    "x-ai/grok-4.1-fast",
]

# Chairman model - synthesizes final response
CHAIRMAN_MODEL = "x-ai/grok-4.1-fast"

# All available models for selection (council models are a subset of these)
AVAILABLE_MODELS = [
    {"id": "openai/gpt-5.2", "name": "GPT-5.2", "provider": "OpenAI"},
    {"id": "openai/gpt-5.1", "name": "GPT-5.1", "provider": "OpenAI"},
    {"id": "openai/gpt-5", "name": "GPT-5", "provider": "OpenAI"},
    {"id": "openai/gpt-5-mini", "name": "GPT-5 Mini", "provider": "OpenAI"},
    {"id": "openai/gpt-5-nano", "name": "GPT-5 Nano", "provider": "OpenAI"},
    {"id": "openai/gpt-4.1", "name": "GPT-4.1", "provider": "OpenAI"},
    {"id": "google/gemini-3-pro-preview", "name": "Gemini 3 Pro", "provider": "Google"},
    {"id": "google/gemini-3-flash-preview", "name": "Gemini 3 Flash", "provider": "Google"},
    {"id": "google/gemini-2.5-pro", "name": "Gemini 2.5 Pro", "provider": "Google"},
    {"id": "google/gemini-2.5-flash", "name": "Gemini 2.5 Flash", "provider": "Google"},
    {"id": "anthropic/claude-sonnet-4.5", "name": "Claude Sonnet 4.5", "provider": "Anthropic"},
    {"id": "anthropic/claude-sonnet-4", "name": "Claude Sonnet 4", "provider": "Anthropic"},
    {"id": "anthropic/claude-haiku-4.5", "name": "Claude Haiku 4.5", "provider": "Anthropic"},
    {"id": "x-ai/grok-4.1-fast", "name": "Grok 4.1 Fast", "provider": "xAI"},
    {"id": "x-ai/grok-4-fast", "name": "Grok 4 Fast", "provider": "xAI"},
    {"id": "x-ai/grok-4", "name": "Grok 4", "provider": "xAI"},
    {"id": "x-ai/grok-code-fast-1", "name": "Grok Code Fast 1", "provider": "xAI"},
    {"id": "meta-llama/llama-4-maverick", "name": "Llama 4 Maverick", "provider": "Meta"},
    {"id": "meta-llama/llama-3.3-70b-instruct", "name": "Llama 3.3 70B", "provider": "Meta"},
    {"id": "deepseek/deepseek-chat-v3-0324", "name": "DeepSeek V3", "provider": "DeepSeek"},
    {"id": "deepseek/deepseek-r1", "name": "DeepSeek R1", "provider": "DeepSeek"},
    {"id": "mistralai/mistral-large-2411", "name": "Mistral Large", "provider": "Mistral"},
]

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Data directory for conversation storage (legacy JSON - kept for migration)
DATA_DIR = "data/conversations"

# SQLite database path
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/llm_council.db")

# Error catalog file path
ERROR_CATALOG_FILE = "data/error_catalog.json"

# Feature flag for error classification
ERROR_CLASSIFICATION_ENABLED = os.getenv("ERROR_CLASSIFICATION_ENABLED", "true").lower() == "true"

# Predefined error taxonomy for fact-checking classification
ERROR_TYPES = [
    "Hallucinated Fact",        # Made-up information with no basis
    "Outdated Information",     # Was true but no longer accurate
    "Numerical/Statistical Error",  # Wrong numbers, percentages, dates
    "Misattribution",           # Attributed to wrong source/person
    "Overgeneralization",       # Stated as universal when only partially true
    "Conflation",               # Mixed up two distinct concepts/events
    "Omission of Critical Context",  # Technically true but misleading
    "Logical Fallacy",          # Faulty reasoning leading to wrong conclusion
    "Other",                    # Doesn't fit above categories
]
