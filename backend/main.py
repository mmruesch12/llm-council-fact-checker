"""FastAPI backend for LLM Council."""

import os
import re
from urllib.parse import quote
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid
import json
import asyncio

from . import storage
from . import database
from .config import (
    AVAILABLE_MODELS, COUNCIL_MODELS, CHAIRMAN_MODEL, 
    ERROR_CLASSIFICATION_ENABLED,
    RATE_LIMIT_GENERAL, RATE_LIMIT_EXPENSIVE
)
from .council import (
    run_full_council,
    generate_conversation_title,
    stage1_collect_responses,
    stage1_collect_responses_streaming,
    stage2_fact_check,
    stage2_fact_check_streaming,
    stage3_collect_rankings,
    stage3_collect_rankings_streaming,
    stage4_synthesize_final,
    stage4_synthesize_final_streaming,
    calculate_aggregate_rankings,
    calculate_aggregate_fact_checks,
    classify_errors
)
from . import error_catalog
from .auth import router as auth_router, require_auth, is_auth_enabled, get_current_user
from .export import export_conversation
from .rate_limiter import RateLimiter
from .security_headers import SecurityHeadersMiddleware
from .api_key_auth import optional_api_key, is_api_key_auth_enabled

app = FastAPI(title="LLM Council API")

# CORS configuration for local development and production
# In production on Render, set FRONTEND_URL environment variable
cors_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
]
# Add production frontend URL if configured
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url:
    cors_origins.append(frontend_url)

# Add any additional allowed origins (comma-separated)
additional_origins = os.getenv("ADDITIONAL_CORS_ORIGINS", "")
if additional_origins:
    for origin in additional_origins.split(","):
        origin = origin.strip()
        # Validate that origin is a properly formatted URL
        if origin and (origin.startswith("http://") or origin.startswith("https://")):
            cors_origins.append(origin)
        elif origin:
            print(f"Warning: Skipping invalid CORS origin (must start with http:// or https://): {origin}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    # Allow any Render.com subdomain for flexibility via regex
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add rate limiting middleware
# Configurable via environment variables: RATE_LIMIT_GENERAL and RATE_LIMIT_EXPENSIVE
app.add_middleware(
    RateLimiter, 
    requests_per_minute=RATE_LIMIT_GENERAL, 
    expensive_requests_per_minute=RATE_LIMIT_EXPENSIVE
)

# Include auth router
app.include_router(auth_router)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str = Field(..., max_length=50000)
    council_models: List[str] = None
    chairman_model: str = None
    fact_checking_enabled: bool = True


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    updated_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    updated_at: str
    title: str
    messages: List[Dict[str, Any]]


class SynthesizeRequest(BaseModel):
    """Request to synthesize a final answer from provided or generated responses."""
    question: str = Field(..., max_length=50000)
    responses: Optional[List[Dict[str, str]]] = None  # Optional: [{"model": "...", "content": "..."}]
    council_models: Optional[List[str]] = None  # Used only if responses not provided
    chairman_model: Optional[str] = None
    fact_checking_enabled: bool = False  # Default to false for simple synthesis
    include_metadata: bool = False  # Whether to return full metadata


class SynthesizeResponse(BaseModel):
    """Response containing the synthesized answer."""
    answer: str
    chairman_model: str
    metadata: Optional[Dict[str, Any]] = None  # Optional metadata if include_metadata=True


async def optional_auth(request: Request) -> dict:
    """Optional authentication - only enforced if auth is enabled."""
    if is_auth_enabled():
        return await require_auth(request)
    return {"login": "anonymous", "auth_disabled": True}


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


@app.get("/api/models")
async def get_models(user: dict = Depends(optional_auth)):
    """Get available models and default configuration."""
    return {
        "available_models": AVAILABLE_MODELS,
        "default_council": COUNCIL_MODELS,
        "default_chairman": CHAIRMAN_MODEL
    }


@app.post("/api/synthesize", response_model=SynthesizeResponse)
async def synthesize_answer(
    request: SynthesizeRequest, 
    user: dict = Depends(optional_auth),
    api_key: str = Depends(optional_api_key)
):
    """
    Synthesize a final answer from the chairman model.
    
    **Authentication:** Requires either:
    - Valid session authentication (GitHub OAuth), OR
    - Valid API key in X-API-Key header
    
    This endpoint allows external apps to get a synthesized answer either:
    1. From pre-provided responses (fast path - just runs stage 4)
    2. By running the full council process (stages 1-4)
    
    Args:
        request.question: The user's question
        request.responses: Optional list of pre-generated responses [{"model": "...", "content": "..."}]
        request.council_models: Council models to use (if responses not provided)
        request.chairman_model: Chairman model for synthesis
        request.fact_checking_enabled: Whether to run fact-checking (default: False for simplicity)
        request.include_metadata: Whether to return full metadata (default: False)
    
    Returns:
        SynthesizeResponse with the chairman's synthesized answer
    """
    # Verify authentication - must have either valid session or API key, depending on what is enabled
    auth_required = is_auth_enabled() or is_api_key_auth_enabled()
    has_session = user.get("login") != "anonymous"
    has_api_key = bool(api_key)

    if auth_required and not (has_session or has_api_key):
        # Tailor error message based on which auth mechanisms are enabled
        if is_auth_enabled() and is_api_key_auth_enabled():
            message = (
                "This endpoint requires either session authentication or an API key. "
                "Provide a valid API key in the X-API-Key header or authenticate via GitHub OAuth."
            )
        elif is_api_key_auth_enabled():
            message = (
                "This endpoint requires an API key. "
                "Provide a valid API key in the X-API-Key header."
            )
        else:  # Only session auth is enabled
            message = (
                "This endpoint requires session authentication. "
                "Authenticate via GitHub OAuth to access this endpoint."
            )

        raise HTTPException(
            status_code=401,
            detail={
                "error": "Authentication required",
                "message": message
            }
        )
    
    chairman = request.chairman_model if request.chairman_model else CHAIRMAN_MODEL
    
    # If responses are provided, use them directly (fast path)
    if request.responses:
        # Format responses for stage 4
        stage1_results = []
        for idx, resp in enumerate(request.responses):
            stage1_results.append({
                "model": resp.get("model", f"unknown-{idx}"),
                "instance": idx,
                "response": resp.get("content", ""),
                "response_time_ms": None
            })
        
        # Create label mapping for de-anonymization
        labels = [chr(65 + i) for i in range(len(stage1_results))]
        label_to_model = {
            f"Response {label}": {
                "model": result['model'],
                "instance": result.get('instance', idx)
            }
            for idx, (label, result) in enumerate(zip(labels, stage1_results))
        }
        
        # Skip fact-checking and rankings - go straight to synthesis
        fact_check_results = []
        stage3_results = []
        
        # Run stage 4 synthesis
        stage4_result = await stage4_synthesize_final(
            request.question,
            stage1_results,
            fact_check_results,
            stage3_results,
            label_to_model,
            chairman
        )
        
        response_data = {
            "answer": stage4_result.get("response", ""),
            "chairman_model": chairman
        }
        
        if request.include_metadata:
            response_data["metadata"] = {
                "responses_provided": len(request.responses),
                "fact_checking_enabled": False,
                "full_council_run": False
            }
        
        return response_data
    
    # No responses provided - run full council process
    else:
        stage1_results, fact_check_results, stage3_results, stage4_result, metadata = await run_full_council(
            request.question,
            request.council_models,
            chairman,
            request.fact_checking_enabled
        )
        
        response_data = {
            "answer": stage4_result.get("response", ""),
            "chairman_model": chairman
        }
        
        if request.include_metadata:
            response_data["metadata"] = {
                "responses_count": len(stage1_results),
                "fact_checking_enabled": request.fact_checking_enabled,
                "full_council_run": True,
                "council_models": request.council_models or COUNCIL_MODELS,
                "aggregate_rankings": metadata.get("aggregate_rankings", []),
                "aggregate_fact_checks": metadata.get("aggregate_fact_checks", [])
            }
        
        return response_data


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations_endpoint(user: dict = Depends(optional_auth)):
    """List all conversations for the current user (metadata only)."""
    user_id = user.get("login", "anonymous")
    return storage.list_conversations(user_id)


@app.get("/api/conversations/search", response_model=List[ConversationMetadata])
async def search_conversations_endpoint(q: str = "", user: dict = Depends(optional_auth)):
    """
    Search conversations for the current user by title or message content.
    
    Args:
        q: Search query string
    """
    user_id = user.get("login", "anonymous")
    return storage.search_conversations(user_id, q)


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest, user: dict = Depends(optional_auth)):
    """Create a new conversation for the current user."""
    conversation_id = str(uuid.uuid4())
    user_id = user.get("login", "anonymous")
    conversation = storage.create_conversation(conversation_id, user_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str, user: dict = Depends(optional_auth)):
    """Get a specific conversation with all its messages (must belong to current user)."""
    user_id = user.get("login", "anonymous")
    conversation = storage.get_conversation(conversation_id, user_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, user: dict = Depends(optional_auth)):
    """Delete a conversation (must belong to current user)."""
    user_id = user.get("login", "anonymous")
    deleted = storage.delete_conversation(conversation_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "ok", "message": "Conversation deleted"}


@app.get("/api/conversations/{conversation_id}/export")
async def export_conversation_endpoint(
    conversation_id: str, 
    mode: str = "all",
    current_user: dict = Depends(require_auth)
):
    """
    Export a conversation to Markdown format.
    
    Args:
        conversation_id: The conversation to export
        mode: Export mode - "all" (default), "final_only", or "rankings_and_final"
    """
    # Validate mode
    valid_modes = ["all", "final_only", "rankings_and_final"]
    if mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"Invalid export mode. Must be one of: {', '.join(valid_modes)}")
    
    user_id = current_user.get("login", "anonymous")
    conversation = storage.get_conversation(conversation_id, user_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Generate markdown with the specified mode
    markdown_content = export_conversation(conversation, mode)
    
    # Create a safe filename from the conversation title
    title = conversation.get('title', 'conversation')
    # Replace special characters with hyphens, then normalize multiple hyphens/spaces
    safe_title = re.sub(r'[^a-zA-Z0-9\s\-_]', '-', title)
    safe_title = re.sub(r'[\s\-]+', '-', safe_title.strip())
    # Ensure filename is not empty and not too long
    if not safe_title or safe_title == '-':
        safe_title = 'conversation'
    safe_title = safe_title[:50]  # Limit title part to 50 chars to leave room for mode and timestamp
    safe_title = safe_title.rstrip('-')  # Remove trailing hyphens after truncation
    
    # Add export mode to filename for clarity
    mode_label = mode.replace('_', '-')  # e.g., "final_only" becomes "final-only"
    
    # Add timestamp in YYYYMMDD-HHMMSS format for uniqueness
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    
    # Final filename format: title_mode_timestamp.md
    # Example: "What-is-Python_final-only_20260120-163000.md"
    filename = f"{safe_title}_{mode_label}_{timestamp}.md"
    
    # Return as downloadable file with RFC 6266 compliant headers
    # Include both ASCII filename and UTF-8 encoded filename* for better compatibility
    # Escape double quotes in filename to prevent header injection
    safe_filename_header = filename.replace('"', '\\"')
    encoded_filename = quote(filename, safe='')
    return Response(
        content=markdown_content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename_header}"; filename*=UTF-8\'\'{encoded_filename}'
        }
    )


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest, user: dict = Depends(optional_auth)):
    """
    Send a message and run the 4-stage council process.
    Returns the complete response with all stages.
    """
    user_id = user.get("login", "anonymous")
    
    # Check if conversation exists and belongs to user
    conversation = storage.get_conversation(conversation_id, user_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Add user message
    storage.add_user_message(conversation_id, request.content, user_id)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title, user_id)

    # Run the 4-stage council process
    stage1_results, fact_check_results, stage3_results, stage4_result, metadata = await run_full_council(
        request.content,
        request.council_models,
        request.chairman_model,
        request.fact_checking_enabled
    )

    # Classify and catalog any errors found during fact-checking (if enabled)
    if ERROR_CLASSIFICATION_ENABLED and request.fact_checking_enabled:
        classified_errors = await classify_errors(
            request.content,
            fact_check_results,
            metadata.get("label_to_model", {}),
            request.chairman_model
        )
        if classified_errors:
            for error in classified_errors:
                error["conversation_id"] = conversation_id
            error_catalog.add_errors(classified_errors)

    # Add assistant message with all stages
    storage.add_assistant_message(
        conversation_id,
        stage1_results,
        fact_check_results,
        stage3_results,
        stage4_result,
        user_id
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "fact_check": fact_check_results,
        "stage3": stage3_results,
        "stage4": stage4_result,
        "metadata": metadata
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest, user: dict = Depends(optional_auth)):
    """
    Send a message and stream the 4-stage council process.
    Returns Server-Sent Events as each stage completes.
    Supports per-model token streaming via chunk events.
    """
    user_id = user.get("login", "anonymous")
    
    # Check if conversation exists and belongs to user
    conversation = storage.get_conversation(conversation_id, user_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    async def event_generator():
        # Queue to collect chunks from parallel model queries
        chunk_queue = asyncio.Queue()

        # Track the current stage for chunk events
        current_stage = {"stage": None}

        async def on_chunk(model: str, instance: int, text: str):
            """Callback for streaming chunks from individual models."""
            await chunk_queue.put({
                "type": f"{current_stage['stage']}_chunk",
                "model": model,
                "instance": instance,
                "text": text
            })

        async def stream_chunks_until_done(done_event: asyncio.Event):
            """Yield chunks from queue until stage is done."""
            while not done_event.is_set() or not chunk_queue.empty():
                try:
                    chunk = await asyncio.wait_for(chunk_queue.get(), timeout=0.1)
                    yield f"data: {json.dumps(chunk)}\n\n"
                except asyncio.TimeoutError:
                    continue

        try:
            # Add user message
            storage.add_user_message(conversation_id, request.content, user_id)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            # Get models list for streaming init
            models = request.council_models if request.council_models else COUNCIL_MODELS

            # Stage 1: Collect responses with streaming
            current_stage["stage"] = "stage1"
            yield f"data: {json.dumps({'type': 'stage1_start', 'models': models})}\n\n"

            # Run stage 1 with streaming chunks
            stage1_done = asyncio.Event()

            async def run_stage1():
                result = await stage1_collect_responses_streaming(
                    request.content, on_chunk, request.council_models
                )
                stage1_done.set()
                return result

            stage1_task = asyncio.create_task(run_stage1())

            # Stream chunks while stage 1 runs
            async for chunk_event in stream_chunks_until_done(stage1_done):
                yield chunk_event

            stage1_results = await stage1_task
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            # Stage 2: Fact-check with streaming (optional)
            if request.fact_checking_enabled:
                current_stage["stage"] = "fact_check"
                yield f"data: {json.dumps({'type': 'fact_check_start', 'models': models})}\n\n"

                fact_check_done = asyncio.Event()

                async def run_fact_check():
                    result = await stage2_fact_check_streaming(
                        request.content, stage1_results, on_chunk, request.council_models
                    )
                    fact_check_done.set()
                    return result

                fact_check_task = asyncio.create_task(run_fact_check())

                # Stream chunks while fact-check runs
                async for chunk_event in stream_chunks_until_done(fact_check_done):
                    yield chunk_event

                fact_check_results, label_to_model = await fact_check_task
                aggregate_fact_checks = calculate_aggregate_fact_checks(fact_check_results, label_to_model)
                yield f"data: {json.dumps({'type': 'fact_check_complete', 'data': fact_check_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_fact_checks': aggregate_fact_checks}})}\n\n"
            else:
                # Skip fact-checking stage
                fact_check_results = []
                # Create simple label mapping without fact-checking
                labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...
                label_to_model = {
                    f"Response {label}": {
                        "model": result['model'],
                        "instance": result.get('instance', idx)
                    }
                    for idx, (label, result) in enumerate(zip(labels, stage1_results))
                }
                aggregate_fact_checks = []

            # Stage 3: Collect rankings with streaming
            current_stage["stage"] = "stage3"
            yield f"data: {json.dumps({'type': 'stage3_start', 'models': models})}\n\n"

            stage3_done = asyncio.Event()

            async def run_stage3():
                result = await stage3_collect_rankings_streaming(
                    request.content, stage1_results, fact_check_results,
                    label_to_model, on_chunk, request.council_models
                )
                stage3_done.set()
                return result

            stage3_task = asyncio.create_task(run_stage3())

            # Stream chunks while stage 3 runs
            async for chunk_event in stream_chunks_until_done(stage3_done):
                yield chunk_event

            stage3_results = await stage3_task
            aggregate_rankings = calculate_aggregate_rankings(stage3_results, label_to_model)
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_results, 'metadata': {'aggregate_rankings': aggregate_rankings}})}\n\n"

            # Stage 4: Synthesize final answer with streaming
            current_stage["stage"] = "stage4"
            chairman = request.chairman_model if request.chairman_model else CHAIRMAN_MODEL
            yield f"data: {json.dumps({'type': 'stage4_start', 'models': [chairman]})}\n\n"

            stage4_done = asyncio.Event()

            async def run_stage4():
                result = await stage4_synthesize_final_streaming(
                    request.content, stage1_results, fact_check_results,
                    stage3_results, label_to_model, on_chunk, request.chairman_model
                )
                stage4_done.set()
                return result

            stage4_task = asyncio.create_task(run_stage4())

            # Stream chunks while stage 4 runs
            async for chunk_event in stream_chunks_until_done(stage4_done):
                yield chunk_event

            stage4_result = await stage4_task
            yield f"data: {json.dumps({'type': 'stage4_complete', 'data': stage4_result})}\n\n"

            # Classify and catalog any errors found during fact-checking (if enabled)
            if ERROR_CLASSIFICATION_ENABLED and request.fact_checking_enabled:
                yield f"data: {json.dumps({'type': 'cataloging_start'})}\n\n"
                classified_errors = await classify_errors(
                    request.content,
                    fact_check_results,
                    label_to_model,
                    request.chairman_model
                )
                errors_cataloged = 0
                if classified_errors:
                    for error in classified_errors:
                        error["conversation_id"] = conversation_id
                    error_catalog.add_errors(classified_errors)
                    errors_cataloged = len(classified_errors)
                yield f"data: {json.dumps({'type': 'cataloging_complete', 'data': {'errors_cataloged': errors_cataloged}})}\n\n"

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title, user_id)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete assistant message
            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                fact_check_results,
                stage3_results,
                stage4_result,
                user_id
            )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            import traceback
            traceback.print_exc()
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/api/errors")
async def get_errors(
    user: dict = Depends(optional_auth),
    api_key: str = Depends(optional_api_key)
):
    """
    Get all cataloged errors with summary statistics.
    
    **Authentication:** Requires either valid session or API key if auth is enabled.
    """
    # Verify authentication if enabled
    auth_required = is_auth_enabled() or is_api_key_auth_enabled()
    has_session = user.get("login") != "anonymous"
    has_api_key = bool(api_key)

    if auth_required and not (has_session or has_api_key):
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    
    return {
        "errors": error_catalog.get_all_errors(),
        "summary": error_catalog.get_error_summary()
    }


@app.delete("/api/errors")
async def clear_errors(
    user: dict = Depends(require_auth)
):
    """
    Clear all cataloged errors.
    
    **Authentication:** Requires valid session authentication (cannot use API key for destructive operations).
    """
    error_catalog.save_catalog({"errors": []})
    return {"status": "ok", "message": "Error catalog cleared"}


# ============================================================================
# Model Configuration Endpoints
# ============================================================================

class CreateModelConfigRequest(BaseModel):
    """Request to create a new model configuration."""
    name: str = Field(..., min_length=1, max_length=100)
    council_models: List[str] = Field(..., min_length=1, max_length=4)
    chairman_model: str
    is_default: bool = False


class UpdateModelConfigRequest(BaseModel):
    """Request to update a model configuration."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    council_models: Optional[List[str]] = Field(None, min_length=1, max_length=4)
    chairman_model: Optional[str] = None
    is_default: Optional[bool] = None


class ModelConfigResponse(BaseModel):
    """Response containing a model configuration."""
    id: str
    name: str
    council_models: List[str]
    chairman_model: str
    is_default: bool
    created_at: str


@app.get("/api/model-configs", response_model=List[ModelConfigResponse])
async def list_model_configs(
    user: dict = Depends(optional_auth)
):
    """
    List all model configurations for the current user.
    
    **Authentication:** Requires valid session authentication.
    
    Returns:
        List of model configurations ordered by default status and creation date
    """
    user_id = user.get("login", "anonymous")
    if user_id == "anonymous":
        raise HTTPException(
            status_code=401,
            detail="Authentication required to manage model configurations"
        )
    
    configs = database.list_model_configurations(user_id)
    return configs


@app.post("/api/model-configs", response_model=ModelConfigResponse)
async def create_model_config(
    request: CreateModelConfigRequest,
    user: dict = Depends(optional_auth)
):
    """
    Create a new model configuration.
    
    **Authentication:** Requires valid session authentication.
    
    Args:
        request: Configuration details including name, models, and default status
    
    Returns:
        Created configuration
    """
    user_id = user.get("login", "anonymous")
    if user_id == "anonymous":
        raise HTTPException(
            status_code=401,
            detail="Authentication required to manage model configurations"
        )
    
    # Validate that all models exist in AVAILABLE_MODELS
    available_model_ids = {model["id"] for model in AVAILABLE_MODELS}
    invalid_council = [m for m in request.council_models if m not in available_model_ids]
    if invalid_council:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid council models: {', '.join(invalid_council)}"
        )
    if request.chairman_model not in available_model_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid chairman model: {request.chairman_model}"
        )
    
    config_id = str(uuid.uuid4())
    config = database.create_model_configuration(
        config_id=config_id,
        user_id=user_id,
        name=request.name,
        council_models=request.council_models,
        chairman_model=request.chairman_model,
        is_default=request.is_default
    )
    
    return config


@app.get("/api/model-configs/{config_id}", response_model=ModelConfigResponse)
async def get_model_config(
    config_id: str,
    user: dict = Depends(optional_auth)
):
    """
    Get a specific model configuration.
    
    **Authentication:** Requires valid session authentication.
    
    Args:
        config_id: Configuration identifier
    
    Returns:
        Configuration details
    """
    user_id = user.get("login", "anonymous")
    if user_id == "anonymous":
        raise HTTPException(
            status_code=401,
            detail="Authentication required to manage model configurations"
        )
    
    config = database.get_model_configuration(config_id, user_id)
    if not config:
        raise HTTPException(
            status_code=404,
            detail="Model configuration not found"
        )
    
    return config


@app.put("/api/model-configs/{config_id}", response_model=ModelConfigResponse)
async def update_model_config(
    config_id: str,
    request: UpdateModelConfigRequest,
    user: dict = Depends(optional_auth)
):
    """
    Update a model configuration.
    
    **Authentication:** Requires valid session authentication.
    
    Args:
        config_id: Configuration identifier
        request: Updated configuration details
    
    Returns:
        Updated configuration
    """
    user_id = user.get("login", "anonymous")
    if user_id == "anonymous":
        raise HTTPException(
            status_code=401,
            detail="Authentication required to manage model configurations"
        )
    
    # Validate models if provided
    if request.council_models or request.chairman_model:
        available_model_ids = {model["id"] for model in AVAILABLE_MODELS}
        
        if request.council_models:
            invalid_council = [m for m in request.council_models if m not in available_model_ids]
            if invalid_council:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid council models: {', '.join(invalid_council)}"
                )
        
        if request.chairman_model and request.chairman_model not in available_model_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid chairman model: {request.chairman_model}"
            )
    
    success = database.update_model_configuration(
        config_id=config_id,
        user_id=user_id,
        name=request.name,
        council_models=request.council_models,
        chairman_model=request.chairman_model,
        is_default=request.is_default
    )
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Model configuration not found"
        )
    
    # Return updated configuration
    config = database.get_model_configuration(config_id, user_id)
    return config


@app.delete("/api/model-configs/{config_id}")
async def delete_model_config(
    config_id: str,
    user: dict = Depends(optional_auth)
):
    """
    Delete a model configuration.
    
    **Authentication:** Requires valid session authentication.
    
    Args:
        config_id: Configuration identifier
    
    Returns:
        Success status
    """
    user_id = user.get("login", "anonymous")
    if user_id == "anonymous":
        raise HTTPException(
            status_code=401,
            detail="Authentication required to manage model configurations"
        )
    
    success = database.delete_model_configuration(config_id, user_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Model configuration not found"
        )
    
    return {"status": "ok", "message": "Configuration deleted"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
