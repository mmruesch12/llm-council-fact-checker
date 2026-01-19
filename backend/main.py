"""FastAPI backend for LLM Council."""

import os
import re
from urllib.parse import quote
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from typing import List, Dict, Any
import uuid
import json
import asyncio

from . import storage
from .config import AVAILABLE_MODELS, COUNCIL_MODELS, CHAIRMAN_MODEL, ERROR_CLASSIFICATION_ENABLED, FRONTEND_URL
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
from .export import export_conversation_to_markdown

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    # Allow any Render.com subdomain for flexibility via regex
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include auth router
app.include_router(auth_router)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str
    council_models: List[str] = None
    chairman_model: str = None
    fact_checking_enabled: bool = True


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]


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


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations(user: dict = Depends(optional_auth)):
    """List all conversations (metadata only)."""
    return storage.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest, user: dict = Depends(optional_auth)):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str, user: dict = Depends(optional_auth)):
    """Get a specific conversation with all its messages."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.get("/api/conversations/{conversation_id}/export")
async def export_conversation(conversation_id: str):
    """Export a conversation to Markdown format."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Generate markdown
    markdown_content = export_conversation_to_markdown(conversation)
    
    # Create a safe filename from the conversation title
    title = conversation.get('title', 'conversation')
    # Replace special characters with hyphens, then normalize multiple hyphens/spaces
    safe_title = re.sub(r'[^a-zA-Z0-9\s\-_]', '-', title)
    safe_title = re.sub(r'[\s\-]+', '-', safe_title.strip())
    # Ensure filename is not empty and not too long
    if not safe_title or safe_title == '-':
        safe_title = 'conversation'
    safe_title = safe_title[:100]  # Limit filename length
    safe_title = safe_title.rstrip('-')  # Remove trailing hyphens after truncation
    filename = f"{safe_title}.md"
    
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
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Add user message
    storage.add_user_message(conversation_id, request.content)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)

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
        stage4_result
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
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
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
            storage.add_user_message(conversation_id, request.content)

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
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete assistant message
            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                fact_check_results,
                stage3_results,
                stage4_result
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
async def get_errors(user: dict = Depends(optional_auth)):
    """Get all cataloged errors with summary statistics."""
    return {
        "errors": error_catalog.get_all_errors(),
        "summary": error_catalog.get_error_summary()
    }


@app.delete("/api/errors")
async def clear_errors(user: dict = Depends(optional_auth)):
    """Clear all cataloged errors."""
    error_catalog.save_catalog({"errors": []})
    return {"status": "ok", "message": "Error catalog cleared"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
