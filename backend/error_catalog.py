"""Error catalog for tracking and classifying fact-checking errors."""

import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from .config import ERROR_CATALOG_FILE, ERROR_TYPES


def _ensure_catalog_exists() -> None:
    """Ensure the error catalog file and its directory exist."""
    os.makedirs(os.path.dirname(ERROR_CATALOG_FILE), exist_ok=True)
    if not os.path.exists(ERROR_CATALOG_FILE):
        with open(ERROR_CATALOG_FILE, 'w') as f:
            json.dump({"errors": []}, f)


def load_catalog() -> Dict[str, Any]:
    """Load the error catalog from disk."""
    _ensure_catalog_exists()
    with open(ERROR_CATALOG_FILE, 'r') as f:
        return json.load(f)


def save_catalog(catalog: Dict[str, Any]) -> None:
    """Save the error catalog to disk."""
    _ensure_catalog_exists()
    with open(ERROR_CATALOG_FILE, 'w') as f:
        json.dump(catalog, f, indent=2)


def add_errors(errors: List[Dict[str, Any]]) -> None:
    """
    Add classified errors to the catalog.

    Args:
        errors: List of error dicts with keys:
            - model: The model that made the error
            - error_type: One of ERROR_TYPES
            - claim: The inaccurate claim (abbreviated)
            - explanation: Brief explanation of why it's wrong
            - question_summary: Brief summary of the user's question
            - conversation_id: ID of the conversation
    """
    if not errors:
        return

    catalog = load_catalog()

    for error in errors:
        catalog["errors"].append({
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "conversation_id": error.get("conversation_id", "unknown"),
            "model": error.get("model", "unknown"),
            "error_type": error.get("error_type", "Other"),
            "claim": error.get("claim", ""),
            "explanation": error.get("explanation", ""),
            "question_summary": error.get("question_summary", "")
        })

    save_catalog(catalog)


def get_all_errors() -> List[Dict[str, Any]]:
    """Get all errors from the catalog."""
    catalog = load_catalog()
    return catalog.get("errors", [])


def get_errors_by_model(model: str) -> List[Dict[str, Any]]:
    """Get all errors for a specific model."""
    all_errors = get_all_errors()
    return [e for e in all_errors if e.get("model") == model]


def get_errors_by_type(error_type: str) -> List[Dict[str, Any]]:
    """Get all errors of a specific type."""
    all_errors = get_all_errors()
    return [e for e in all_errors if e.get("error_type") == error_type]


def get_error_summary() -> Dict[str, Any]:
    """
    Get a summary of errors by model and by type.

    Returns:
        Dict with 'by_model' and 'by_type' breakdowns
    """
    all_errors = get_all_errors()

    by_model: Dict[str, int] = {}
    by_type: Dict[str, int] = {}
    by_model_and_type: Dict[str, Dict[str, int]] = {}

    for error in all_errors:
        model = error.get("model", "unknown")
        error_type = error.get("error_type", "Other")

        by_model[model] = by_model.get(model, 0) + 1
        by_type[error_type] = by_type.get(error_type, 0) + 1

        if model not in by_model_and_type:
            by_model_and_type[model] = {}
        by_model_and_type[model][error_type] = by_model_and_type[model].get(error_type, 0) + 1

    return {
        "total_errors": len(all_errors),
        "by_model": by_model,
        "by_type": by_type,
        "by_model_and_type": by_model_and_type
    }


def parse_classification_response(response_text: str) -> List[Dict[str, Any]]:
    """
    Parse the chairman's error classification response.

    Expected format in response:
    ERROR CLASSIFICATIONS:
    ---
    MODEL: openai/gpt-4o
    ERROR_TYPE: Hallucinated Fact
    CLAIM: The claim that was wrong
    EXPLANATION: Why it was wrong
    ---
    MODEL: ...

    Args:
        response_text: The raw response from the chairman

    Returns:
        List of parsed error dicts
    """
    import re

    errors = []

    # Look for ERROR CLASSIFICATIONS section
    if "ERROR CLASSIFICATIONS:" not in response_text:
        return errors

    # Split by the section header
    parts = response_text.split("ERROR CLASSIFICATIONS:")
    if len(parts) < 2:
        return errors

    classification_section = parts[1]

    # Split by error separators (---)
    error_blocks = re.split(r'\n---+\n?', classification_section)

    for block in error_blocks:
        block = block.strip()
        if not block:
            continue

        error = {}

        # Extract MODEL
        model_match = re.search(r'MODEL:\s*(.+?)(?:\n|$)', block, re.IGNORECASE)
        if model_match:
            error["model"] = model_match.group(1).strip()

        # Extract ERROR_TYPE
        type_match = re.search(r'ERROR_TYPE:\s*(.+?)(?:\n|$)', block, re.IGNORECASE)
        if type_match:
            error_type = type_match.group(1).strip()
            # Validate against known types
            if error_type not in ERROR_TYPES:
                error_type = "Other"
            error["error_type"] = error_type

        # Extract CLAIM
        claim_match = re.search(r'CLAIM:\s*(.+?)(?:\n(?:ERROR_TYPE|EXPLANATION|MODEL):|$)', block, re.IGNORECASE | re.DOTALL)
        if claim_match:
            error["claim"] = claim_match.group(1).strip()

        # Extract EXPLANATION
        explanation_match = re.search(r'EXPLANATION:\s*(.+?)(?:\n(?:ERROR_TYPE|CLAIM|MODEL):|$)', block, re.IGNORECASE | re.DOTALL)
        if explanation_match:
            error["explanation"] = explanation_match.group(1).strip()

        # Only add if we have at least model and error_type
        if error.get("model") and error.get("error_type"):
            errors.append(error)

    return errors
