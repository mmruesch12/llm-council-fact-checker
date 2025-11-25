"""3-stage LLM Council orchestration."""

import json
import asyncio
from typing import List, Dict, Any, Tuple, Callable, AsyncGenerator
from .openrouter import query_models_parallel, query_model, query_models_parallel_streaming, query_model_streaming
from .config import COUNCIL_MODELS, CHAIRMAN_MODEL, ERROR_TYPES


async def stage1_collect_responses(
    user_query: str,
    council_models: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council models.

    Args:
        user_query: The user's question
        council_models: Optional list of model IDs to use (defaults to COUNCIL_MODELS)

    Returns:
        List of dicts with 'model', 'instance', and 'response' keys.
        For duplicate models, 'instance' distinguishes between them.
    """
    models = council_models if council_models else COUNCIL_MODELS
    messages = [{"role": "user", "content": user_query}]

    # Query all models in parallel (handles duplicates)
    responses = await query_models_parallel(models, messages)

    # Format results - responses is now a list, not a dict
    stage1_results = []
    for item in responses:
        response = item.get('response')
        if response is not None:  # Only include successful responses
            stage1_results.append({
                "model": item['model'],
                "instance": item['instance'],
                "response": response.get('content', ''),
                "response_time_ms": response.get('response_time_ms')
            })

    return stage1_results


async def stage2_fact_check(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    council_models: List[str] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """
    Stage 2: Each model fact-checks the other models' anonymized responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1
        council_models: Optional list of model IDs to use (defaults to COUNCIL_MODELS)

    Returns:
        Tuple of (fact_check list, label_to_model mapping).
        label_to_model maps "Response X" to {"model": model_id, "instance": instance_idx}
    """
    models = council_models if council_models else COUNCIL_MODELS
    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...

    # Create mapping from label to model info (includes instance for duplicates)
    label_to_model = {
        f"Response {label}": {
            "model": result['model'],
            "instance": result.get('instance', idx)
        }
        for idx, (label, result) in enumerate(zip(labels, stage1_results))
    }

    # Build the fact-checking prompt
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    fact_check_prompt = f"""You are a fact-checker evaluating different AI responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task is to fact-check each response thoroughly:

1. For EACH response, identify:
   - **Accurate Claims**: List specific claims that are factually correct
   - **Inaccurate Claims**: List specific claims that are factually incorrect or misleading, and explain why
   - **Unverifiable Claims**: List claims that cannot be easily verified or are speculative
   - **Missing Important Information**: Note any crucial information the response failed to include

2. At the very end of your analysis, provide a summary section.

IMPORTANT: Your summary MUST be formatted EXACTLY as follows:
- Start with the line "FACT CHECK SUMMARY:" (all caps, with colon)
- For each response, on a new line write: "Response X: [ACCURATE/MOSTLY ACCURATE/MIXED/MOSTLY INACCURATE/INACCURATE]"
- After rating all responses, add a line: "MOST RELIABLE: Response X" (the single most factually reliable response)

Example of the correct format for your summary:

FACT CHECK SUMMARY:
Response A: MOSTLY ACCURATE
Response B: MIXED
Response C: ACCURATE
MOST RELIABLE: Response C

Now provide your detailed fact-check analysis:"""

    messages = [{"role": "user", "content": fact_check_prompt}]

    # Get fact-checks from all council models in parallel
    responses = await query_models_parallel(models, messages)

    # Format results - responses is now a list
    fact_check_results = []
    for item in responses:
        response = item.get('response')
        if response is not None:
            full_text = response.get('content', '')
            parsed = parse_fact_check_from_text(full_text)
            fact_check_results.append({
                "model": item['model'],
                "instance": item['instance'],
                "fact_check": full_text,
                "parsed_summary": parsed,
                "response_time_ms": response.get('response_time_ms')
            })

    return fact_check_results, label_to_model


def parse_fact_check_from_text(fact_check_text: str) -> Dict[str, Any]:
    """
    Parse the FACT CHECK SUMMARY section from the model's response.

    Args:
        fact_check_text: The full text response from the model

    Returns:
        Dict with ratings per response and most_reliable
    """
    import re

    result = {
        "ratings": {},
        "most_reliable": None
    }

    # Look for "FACT CHECK SUMMARY:" section
    if "FACT CHECK SUMMARY:" in fact_check_text:
        # Extract everything after "FACT CHECK SUMMARY:"
        parts = fact_check_text.split("FACT CHECK SUMMARY:")
        if len(parts) >= 2:
            summary_section = parts[1]

            # Extract ratings (e.g., "Response A: MOSTLY ACCURATE")
            rating_matches = re.findall(
                r'Response ([A-Z]):\s*(ACCURATE|MOSTLY ACCURATE|MIXED|MOSTLY INACCURATE|INACCURATE)',
                summary_section,
                re.IGNORECASE
            )
            for label, rating in rating_matches:
                result["ratings"][f"Response {label}"] = rating.upper()

            # Extract most reliable
            most_reliable_match = re.search(
                r'MOST RELIABLE:\s*Response ([A-Z])',
                summary_section,
                re.IGNORECASE
            )
            if most_reliable_match:
                result["most_reliable"] = f"Response {most_reliable_match.group(1)}"

    return result


async def stage3_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    fact_check_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str],
    council_models: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Stage 3: Each model ranks the anonymized responses (after seeing fact-checks).

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1
        fact_check_results: Results from Stage 2 (fact-checking)
        label_to_model: Mapping from labels to model names
        council_models: Optional list of model IDs to use (defaults to COUNCIL_MODELS)

    Returns:
        List of rankings from each model
    """
    models = council_models if council_models else COUNCIL_MODELS
    # Get labels from label_to_model
    labels = [label.replace("Response ", "") for label in label_to_model.keys()]
    labels.sort()

    # Build the ranking prompt with fact-check context
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    # Summarize fact-check findings
    fact_check_summary = "\n\n".join([
        f"Fact-checker {i+1}:\n{result['fact_check']}"
        for i, result in enumerate(fact_check_results)
    ])

    ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

---

Here are the fact-check analyses from peer reviewers:

{fact_check_summary}

---

Your task:
1. Consider both the quality of each response AND the fact-check findings.
2. Evaluate each response individually, taking into account:
   - Factual accuracy (as revealed by the fact-checks)
   - Completeness and helpfulness
   - Clarity and reasoning
3. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format:

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

    messages = [{"role": "user", "content": ranking_prompt}]

    # Get rankings from all council models in parallel
    responses = await query_models_parallel(models, messages)

    # Format results - responses is now a list
    stage3_results = []
    for item in responses:
        response = item.get('response')
        if response is not None:
            full_text = response.get('content', '')
            parsed = parse_ranking_from_text(full_text)
            stage3_results.append({
                "model": item['model'],
                "instance": item['instance'],
                "ranking": full_text,
                "parsed_ranking": parsed,
                "response_time_ms": response.get('response_time_ms')
            })

    return stage3_results


async def stage4_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    fact_check_results: List[Dict[str, Any]],
    stage3_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str],
    chairman_model: str = None
) -> Dict[str, Any]:
    """
    Stage 4: Chairman synthesizes final response with fact-check validation.

    Args:
        user_query: The original user query
        stage1_results: Individual model responses from Stage 1
        fact_check_results: Fact-checks from Stage 2
        stage3_results: Rankings from Stage 3
        label_to_model: Mapping from labels to model names
        chairman_model: Optional chairman model ID (defaults to CHAIRMAN_MODEL)

    Returns:
        Dict with 'model', 'response', and 'fact_check_synthesis' keys
    """
    chairman = chairman_model if chairman_model else CHAIRMAN_MODEL
    # Build comprehensive context for chairman
    stage1_text = "\n\n".join([
        f"Model: {result['model']}\nResponse: {result['response']}"
        for result in stage1_results
    ])

    fact_check_text = "\n\n".join([
        f"Fact-checker ({result['model']}):\n{result['fact_check']}"
        for result in fact_check_results
    ])

    stage3_text = "\n\n".join([
        f"Model: {result['model']}\nRanking: {result['ranking']}"
        for result in stage3_results
    ])

    chairman_prompt = f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question. Then each model fact-checked each other's responses. Finally, each model ranked the responses taking the fact-checks into account.

Original Question: {user_query}

=== STAGE 1 - Individual Responses ===
{stage1_text}

=== STAGE 2 - Fact-Check Analyses ===
{fact_check_text}

=== STAGE 3 - Peer Rankings (Informed by Fact-Checks) ===
{stage3_text}

---

Your task as Chairman is comprehensive. You must:

1. **FACT-CHECK SYNTHESIS**: First, analyze all the fact-check reports. Identify:
   - Claims that multiple fact-checkers agreed were ACCURATE
   - Claims that multiple fact-checkers agreed were INACCURATE (these are confirmed errors)
   - Claims where fact-checkers DISAGREED (these need your judgment)
   - Any factual errors that were missed by some fact-checkers

2. **FACT-CHECK VALIDATION**: Review the fact-checkers themselves. Did any fact-checker make errors in their fact-checking? Note any corrections needed.

3. **FINAL ANSWER**: Synthesize all of this into a single, comprehensive, FACTUALLY ACCURATE answer to the user's question. Your answer should:
   - Incorporate the best insights from all responses
   - EXCLUDE or CORRECT any claims that were identified as inaccurate
   - Note any areas of genuine uncertainty where fact-checkers disagreed
   - Be clear about what is well-established fact vs. what is opinion or speculation

Structure your response as follows:

## Fact-Check Synthesis
[Your analysis of the fact-checking results - what was confirmed accurate, what was confirmed inaccurate, and any disagreements]

## Fact-Checker Validation
[Any corrections to the fact-checkers themselves, or confirmation that their analyses were sound]

## Final Council Answer
[Your comprehensive, fact-checked answer to the user's question]

Now provide your Chairman synthesis:"""

    messages = [{"role": "user", "content": chairman_prompt}]

    # Query the chairman model
    response = await query_model(chairman, messages)

    if response is None:
        # Fallback if chairman fails
        return {
            "model": chairman,
            "response": "Error: Unable to generate final synthesis.",
            "response_time_ms": None
        }

    return {
        "model": chairman,
        "response": response.get('content', ''),
        "response_time_ms": response.get('response_time_ms')
    }


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order
    """
    import re

    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        # Extract everything after "FINAL RANKING:"
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            # Try to extract numbered list format (e.g., "1. Response A")
            # This pattern looks for: number, period, optional space, "Response X"
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                # Extract just the "Response X" part
                return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]

            # Fallback: Extract all "Response X" patterns in order
            matches = re.findall(r'Response [A-Z]', ranking_section)
            return matches

    # Fallback: try to find any "Response X" patterns in order
    matches = re.findall(r'Response [A-Z]', ranking_text)
    return matches


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models.

    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to {"model": model_id, "instance": idx}

    Returns:
        List of dicts with model info and average rank, sorted best to worst.
        For duplicate models, each instance is tracked separately.
    """
    from collections import defaultdict

    # Track positions for each model instance (keyed by "model:instance")
    model_positions = defaultdict(list)

    for ranking in stage2_results:
        ranking_text = ranking['ranking']

        # Parse the ranking from the structured format
        parsed_ranking = parse_ranking_from_text(ranking_text)

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_info = label_to_model[label]
                # Create unique key for this model instance
                instance_key = f"{model_info['model']}:{model_info['instance']}"
                model_positions[instance_key].append(position)

    # Calculate average position for each model instance
    aggregate = []
    for instance_key, positions in model_positions.items():
        if positions:
            model_id, instance = instance_key.rsplit(':', 1)
            avg_rank = sum(positions) / len(positions)
            aggregate.append({
                "model": model_id,
                "instance": int(instance),
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions)
            })

    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x['average_rank'])

    return aggregate


async def generate_conversation_title(user_query: str) -> str:
    """
    Generate a short title for a conversation based on the first user message.

    Args:
        user_query: The first user message

    Returns:
        A short title (3-5 words)
    """
    title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

    messages = [{"role": "user", "content": title_prompt}]

    # Use gemini-2.5-flash for title generation (fast and cheap)
    response = await query_model("google/gemini-2.5-flash", messages, timeout=30.0)

    if response is None:
        # Fallback to a generic title
        return "New Conversation"

    title = response.get('content', 'New Conversation').strip()

    # Clean up the title - remove quotes, limit length
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title


def calculate_aggregate_fact_checks(
    fact_check_results: List[Dict[str, Any]],
    label_to_model: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate fact-check ratings across all fact-checkers.

    Args:
        fact_check_results: Fact-checks from each model
        label_to_model: Mapping from anonymous labels to {"model": model_id, "instance": idx}

    Returns:
        List of dicts with model info, consensus rating, and vote breakdown.
        For duplicate models, each instance is tracked separately.
    """
    from collections import defaultdict

    # Rating scores for averaging (higher is better)
    rating_scores = {
        "ACCURATE": 5,
        "MOSTLY ACCURATE": 4,
        "MIXED": 3,
        "MOSTLY INACCURATE": 2,
        "INACCURATE": 1
    }

    # Track ratings and most_reliable votes for each model instance (keyed by "model:instance")
    model_ratings = defaultdict(list)
    most_reliable_votes = defaultdict(int)

    for fact_check in fact_check_results:
        parsed = fact_check.get('parsed_summary', {})
        ratings = parsed.get('ratings', {})
        most_reliable = parsed.get('most_reliable')

        # Collect ratings for each response
        for label, rating in ratings.items():
            if label in label_to_model:
                model_info = label_to_model[label]
                instance_key = f"{model_info['model']}:{model_info['instance']}"
                model_ratings[instance_key].append(rating)

        # Count most_reliable votes
        if most_reliable and most_reliable in label_to_model:
            model_info = label_to_model[most_reliable]
            instance_key = f"{model_info['model']}:{model_info['instance']}"
            most_reliable_votes[instance_key] += 1

    # Calculate aggregate for each model instance
    aggregate = []
    for instance_key, ratings in model_ratings.items():
        if ratings:
            model_id, instance = instance_key.rsplit(':', 1)
            # Calculate average score
            scores = [rating_scores.get(r, 3) for r in ratings]
            avg_score = sum(scores) / len(scores)

            # Map back to rating label
            if avg_score >= 4.5:
                consensus = "ACCURATE"
            elif avg_score >= 3.5:
                consensus = "MOSTLY ACCURATE"
            elif avg_score >= 2.5:
                consensus = "MIXED"
            elif avg_score >= 1.5:
                consensus = "MOSTLY INACCURATE"
            else:
                consensus = "INACCURATE"

            aggregate.append({
                "model": model_id,
                "instance": int(instance),
                "consensus_rating": consensus,
                "average_score": round(avg_score, 2),
                "ratings_count": len(ratings),
                "most_reliable_votes": most_reliable_votes.get(instance_key, 0),
                "rating_breakdown": ratings
            })

    # Sort by average score (higher is better)
    aggregate.sort(key=lambda x: x['average_score'], reverse=True)

    return aggregate


async def classify_errors(
    user_query: str,
    fact_check_results: List[Dict[str, Any]],
    label_to_model: Dict[str, Dict[str, Any]],
    chairman_model: str = None
) -> List[Dict[str, Any]]:
    """
    Have the chairman classify inaccuracies found during fact-checking.

    Args:
        user_query: The original user query
        fact_check_results: Results from Stage 2 (fact-checking)
        label_to_model: Mapping from labels to {"model": model_id, "instance": idx}
        chairman_model: Optional chairman model ID (defaults to CHAIRMAN_MODEL)

    Returns:
        List of classified errors ready for cataloging
    """
    from .error_catalog import parse_classification_response

    chairman = chairman_model if chairman_model else CHAIRMAN_MODEL

    # Build fact-check context
    fact_check_text = "\n\n".join([
        f"Fact-checker ({result['model']}):\n{result['fact_check']}"
        for result in fact_check_results
    ])

    # Build the error types list for the prompt
    error_types_list = "\n".join([f"- {et}" for et in ERROR_TYPES])

    # Create a simplified label_to_model mapping with just model IDs (no instances)
    # This ensures errors are cataloged against the model itself, not specific instances
    simple_label_to_model = {
        label: info['model'] if isinstance(info, dict) else info
        for label, info in label_to_model.items()
    }

    classification_prompt = f"""You are classifying factual errors found during a fact-checking process.

The original question was about: {user_query}

Here are the fact-check analyses from multiple reviewers:

{fact_check_text}

---

The anonymous response labels map to these models:
{json.dumps(simple_label_to_model, indent=2)}

---

Your task:
1. Review all the fact-check analyses above
2. Identify ALL claims that were flagged as INACCURATE by fact-checkers
3. For EACH inaccurate claim, classify it into ONE of these error types:

{error_types_list}

IMPORTANT FORMATTING REQUIREMENTS:
- Summarize the question context in 10 words or fewer
- Keep each claim description to 1-2 sentences maximum
- Keep explanations brief (1-2 sentences)

If NO inaccuracies were found, respond with:
NO ERRORS FOUND

Otherwise, format your response EXACTLY as follows:

QUESTION SUMMARY: [Brief 10-word-or-fewer summary of the question]

ERROR CLASSIFICATIONS:
---
MODEL: [full model identifier, e.g., openai/gpt-4o]
ERROR_TYPE: [one of the error types listed above]
CLAIM: [the inaccurate claim, 1-2 sentences max]
EXPLANATION: [brief explanation of why it's wrong, 1-2 sentences max]
---
MODEL: [next model if applicable]
ERROR_TYPE: ...
CLAIM: ...
EXPLANATION: ...
---

Include one block for EACH inaccurate claim identified. Multiple errors from the same model should each have their own block.

Now classify the errors:"""

    messages = [{"role": "user", "content": classification_prompt}]

    response = await query_model(chairman, messages)

    if response is None or "NO ERRORS FOUND" in response.get('content', ''):
        return []

    response_text = response.get('content', '')

    # Extract question summary
    question_summary = ""
    import re
    summary_match = re.search(r'QUESTION SUMMARY:\s*(.+?)(?:\n|$)', response_text)
    if summary_match:
        question_summary = summary_match.group(1).strip()
    else:
        # Fallback: truncate the original query
        question_summary = user_query[:50] + "..." if len(user_query) > 50 else user_query

    # Parse the classification response
    errors = parse_classification_response(response_text)

    # Add question summary to each error
    for error in errors:
        error["question_summary"] = question_summary

    return errors


async def stage1_collect_responses_streaming(
    user_query: str,
    on_chunk: Callable[[str, int, str], None],
    council_models: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Stage 1 with streaming: Collect individual responses from all council models.
    Streams tokens via on_chunk callback as they arrive.

    Args:
        user_query: The user's question
        on_chunk: Async callback (model, instance, chunk_text) -> None
        council_models: Optional list of model IDs to use

    Returns:
        List of dicts with 'model', 'instance', and 'response' keys.
    """
    models = council_models if council_models else COUNCIL_MODELS
    messages = [{"role": "user", "content": user_query}]

    # Query all models in parallel with streaming
    responses = await query_models_parallel_streaming(models, messages, on_chunk)

    # Format results
    stage1_results = []
    for item in responses:
        response = item.get('response')
        if response is not None:
            stage1_results.append({
                "model": item['model'],
                "instance": item['instance'],
                "response": response.get('content', ''),
                "response_time_ms": response.get('response_time_ms')
            })

    return stage1_results


async def stage2_fact_check_streaming(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    on_chunk: Callable[[str, int, str], None],
    council_models: List[str] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """
    Stage 2 with streaming: Each model fact-checks the other models' responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1
        on_chunk: Async callback (model, instance, chunk_text) -> None
        council_models: Optional list of model IDs to use

    Returns:
        Tuple of (fact_check list, label_to_model mapping).
    """
    models = council_models if council_models else COUNCIL_MODELS
    labels = [chr(65 + i) for i in range(len(stage1_results))]

    label_to_model = {
        f"Response {label}": {
            "model": result['model'],
            "instance": result.get('instance', idx)
        }
        for idx, (label, result) in enumerate(zip(labels, stage1_results))
    }

    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    fact_check_prompt = f"""You are a fact-checker evaluating different AI responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task is to fact-check each response thoroughly:

1. For EACH response, identify:
   - **Accurate Claims**: List specific claims that are factually correct
   - **Inaccurate Claims**: List specific claims that are factually incorrect or misleading, and explain why
   - **Unverifiable Claims**: List claims that cannot be easily verified or are speculative
   - **Missing Important Information**: Note any crucial information the response failed to include

2. At the very end of your analysis, provide a summary section.

IMPORTANT: Your summary MUST be formatted EXACTLY as follows:
- Start with the line "FACT CHECK SUMMARY:" (all caps, with colon)
- For each response, on a new line write: "Response X: [ACCURATE/MOSTLY ACCURATE/MIXED/MOSTLY INACCURATE/INACCURATE]"
- After rating all responses, add a line: "MOST RELIABLE: Response X" (the single most factually reliable response)

Example of the correct format for your summary:

FACT CHECK SUMMARY:
Response A: MOSTLY ACCURATE
Response B: MIXED
Response C: ACCURATE
MOST RELIABLE: Response C

Now provide your detailed fact-check analysis:"""

    messages = [{"role": "user", "content": fact_check_prompt}]

    # Get fact-checks with streaming
    responses = await query_models_parallel_streaming(models, messages, on_chunk)

    fact_check_results = []
    for item in responses:
        response = item.get('response')
        if response is not None:
            full_text = response.get('content', '')
            parsed = parse_fact_check_from_text(full_text)
            fact_check_results.append({
                "model": item['model'],
                "instance": item['instance'],
                "fact_check": full_text,
                "parsed_summary": parsed,
                "response_time_ms": response.get('response_time_ms')
            })

    return fact_check_results, label_to_model


async def stage3_collect_rankings_streaming(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    fact_check_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str],
    on_chunk: Callable[[str, int, str], None],
    council_models: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Stage 3 with streaming: Each model ranks the anonymized responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1
        fact_check_results: Results from Stage 2
        label_to_model: Mapping from labels to model names
        on_chunk: Async callback (model, instance, chunk_text) -> None
        council_models: Optional list of model IDs to use

    Returns:
        List of rankings from each model
    """
    models = council_models if council_models else COUNCIL_MODELS
    labels = [label.replace("Response ", "") for label in label_to_model.keys()]
    labels.sort()

    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    fact_check_summary = "\n\n".join([
        f"Fact-checker {i+1}:\n{result['fact_check']}"
        for i, result in enumerate(fact_check_results)
    ])

    ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

---

Here are the fact-check analyses from peer reviewers:

{fact_check_summary}

---

Your task:
1. Consider both the quality of each response AND the fact-check findings.
2. Evaluate each response individually, taking into account:
   - Factual accuracy (as revealed by the fact-checks)
   - Completeness and helpfulness
   - Clarity and reasoning
3. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format:

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

    messages = [{"role": "user", "content": ranking_prompt}]

    # Get rankings with streaming
    responses = await query_models_parallel_streaming(models, messages, on_chunk)

    stage3_results = []
    for item in responses:
        response = item.get('response')
        if response is not None:
            full_text = response.get('content', '')
            parsed = parse_ranking_from_text(full_text)
            stage3_results.append({
                "model": item['model'],
                "instance": item['instance'],
                "ranking": full_text,
                "parsed_ranking": parsed,
                "response_time_ms": response.get('response_time_ms')
            })

    return stage3_results


async def stage4_synthesize_final_streaming(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    fact_check_results: List[Dict[str, Any]],
    stage3_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str],
    on_chunk: Callable[[str, int, str], None],
    chairman_model: str = None
) -> Dict[str, Any]:
    """
    Stage 4 with streaming: Chairman synthesizes final response with fact-check validation.

    Args:
        user_query: The original user query
        stage1_results: Individual model responses from Stage 1
        fact_check_results: Fact-checks from Stage 2
        stage3_results: Rankings from Stage 3
        label_to_model: Mapping from labels to model names
        on_chunk: Async callback (model, instance, chunk_text) -> None
        chairman_model: Optional chairman model ID (defaults to CHAIRMAN_MODEL)

    Returns:
        Dict with 'model', 'response', and 'response_time_ms' keys
    """
    chairman = chairman_model if chairman_model else CHAIRMAN_MODEL

    # Build comprehensive context for chairman
    stage1_text = "\n\n".join([
        f"Model: {result['model']}\nResponse: {result['response']}"
        for result in stage1_results
    ])

    fact_check_text = "\n\n".join([
        f"Fact-checker ({result['model']}):\n{result['fact_check']}"
        for result in fact_check_results
    ])

    stage3_text = "\n\n".join([
        f"Model: {result['model']}\nRanking: {result['ranking']}"
        for result in stage3_results
    ])

    chairman_prompt = f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question. Then each model fact-checked each other's responses. Finally, each model ranked the responses taking the fact-checks into account.

Original Question: {user_query}

=== STAGE 1 - Individual Responses ===
{stage1_text}

=== STAGE 2 - Fact-Check Analyses ===
{fact_check_text}

=== STAGE 3 - Peer Rankings (Informed by Fact-Checks) ===
{stage3_text}

---

Your task as Chairman is comprehensive. You must:

1. **FACT-CHECK SYNTHESIS**: First, analyze all the fact-check reports. Identify:
   - Claims that multiple fact-checkers agreed were ACCURATE
   - Claims that multiple fact-checkers agreed were INACCURATE (these are confirmed errors)
   - Claims where fact-checkers DISAGREED (these need your judgment)
   - Any factual errors that were missed by some fact-checkers

2. **FACT-CHECK VALIDATION**: Review the fact-checkers themselves. Did any fact-checker make errors in their fact-checking? Note any corrections needed.

3. **FINAL ANSWER**: Synthesize all of this into a single, comprehensive, FACTUALLY ACCURATE answer to the user's question. Your answer should:
   - Incorporate the best insights from all responses
   - EXCLUDE or CORRECT any claims that were identified as inaccurate
   - Note any areas of genuine uncertainty where fact-checkers disagreed
   - Be clear about what is well-established fact vs. what is opinion or speculation

Structure your response as follows:

## Fact-Check Synthesis
[Your analysis of the fact-checking results - what was confirmed accurate, what was confirmed inaccurate, and any disagreements]

## Fact-Checker Validation
[Any corrections to the fact-checkers themselves, or confirmation that their analyses were sound]

## Final Council Answer
[Your comprehensive, fact-checked answer to the user's question]

Now provide your Chairman synthesis:"""

    messages = [{"role": "user", "content": chairman_prompt}]

    # Query the chairman model with streaming (instance 0 since single model)
    response = await query_model_streaming(chairman, messages, 0, on_chunk)

    if response is None:
        return {
            "model": chairman,
            "response": "Error: Unable to generate final synthesis.",
            "response_time_ms": None
        }

    return {
        "model": chairman,
        "response": response.get('content', ''),
        "response_time_ms": response.get('response_time_ms')
    }


async def run_full_council(
    user_query: str,
    council_models: List[str] = None,
    chairman_model: str = None
) -> Tuple[List, List, List, Dict, Dict]:
    """
    Run the complete 4-stage council process.

    Args:
        user_query: The user's question
        council_models: Optional list of model IDs for the council (defaults to COUNCIL_MODELS)
        chairman_model: Optional chairman model ID (defaults to CHAIRMAN_MODEL)

    Returns:
        Tuple of (stage1_results, fact_check_results, stage3_results, stage4_result, metadata)
    """
    # Stage 1: Collect individual responses
    stage1_results = await stage1_collect_responses(user_query, council_models)

    # If no models responded successfully, return error
    if not stage1_results:
        return [], [], [], {
            "model": "error",
            "response": "All models failed to respond. Please try again."
        }, {}

    # Stage 2: Fact-check each other's responses
    fact_check_results, label_to_model = await stage2_fact_check(user_query, stage1_results, council_models)

    # Calculate aggregate fact-check ratings
    aggregate_fact_checks = calculate_aggregate_fact_checks(fact_check_results, label_to_model)

    # Stage 3: Collect rankings (informed by fact-checks)
    stage3_results = await stage3_collect_rankings(
        user_query, stage1_results, fact_check_results, label_to_model, council_models
    )

    # Calculate aggregate rankings
    aggregate_rankings = calculate_aggregate_rankings(stage3_results, label_to_model)

    # Stage 4: Synthesize final answer with fact-check validation
    stage4_result = await stage4_synthesize_final(
        user_query,
        stage1_results,
        fact_check_results,
        stage3_results,
        label_to_model,
        chairman_model
    )

    # Prepare metadata
    metadata = {
        "label_to_model": label_to_model,
        "aggregate_fact_checks": aggregate_fact_checks,
        "aggregate_rankings": aggregate_rankings
    }

    return stage1_results, fact_check_results, stage3_results, stage4_result, metadata
