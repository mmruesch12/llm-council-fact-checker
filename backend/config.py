"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

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
    {"id": "openai/gpt-5.1", "name": "GPT-5.1", "provider": "OpenAI"},
    {"id": "openai/gpt-5", "name": "GPT-5", "provider": "OpenAI"},
    {"id": "openai/gpt-4.1", "name": "GPT-4.1", "provider": "OpenAI"},
    {"id": "google/gemini-3-pro-preview", "name": "Gemini 3 Pro", "provider": "Google"},
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

# Data directory for conversation storage
DATA_DIR = "data/conversations"

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
