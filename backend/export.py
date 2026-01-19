"""Export conversations to various formats."""

from typing import Dict, Any, Literal
from datetime import datetime, timezone

ExportMode = Literal["all", "final_only", "rankings_and_final"]


def _get_header(conversation: Dict[str, Any]) -> str:
    """Generate common header for exports."""
    lines = []
    lines.append(f"# {conversation.get('title', 'LLM Council Conversation')}")
    lines.append("")
    lines.append(f"**Created:** {conversation.get('created_at', 'Unknown')}")
    lines.append(f"**Conversation ID:** {conversation.get('id', 'Unknown')}")
    lines.append("")
    lines.append("---")
    lines.append("")
    return '\n'.join(lines)


def _get_footer() -> str:
    """Generate common footer for exports."""
    lines = []
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*Exported from LLM Council on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC*")
    lines.append("")
    return '\n'.join(lines)


def export_final_answer_only(conversation: Dict[str, Any]) -> str:
    """
    Export only the final chairman answers from the conversation.
    
    Args:
        conversation: Full conversation dict with messages
        
    Returns:
        Markdown-formatted string with only final answers
    """
    lines = []
    
    # Header
    lines.append(_get_header(conversation))
    
    # Process each message
    query_counter = 0
    for message in conversation.get('messages', []):
        if message['role'] == 'user':
            query_counter += 1
            lines.append(f"## Query {query_counter}")
            lines.append("")
            lines.append(f"**User:** {message['content']}")
            lines.append("")
            
        elif message['role'] == 'assistant':
            # Only Stage 4: Chairman Synthesis
            stage4 = message.get('stage4', {})
            if stage4:
                lines.append("### Final Council Answer")
                lines.append("")
                model_name = stage4.get('model', 'Unknown Model')
                content = stage4.get('content', '')
                response_time = stage4.get('response_time_ms')
                
                lines.append(f"**Chairman: {model_name}**")
                if response_time and isinstance(response_time, (int, float)):
                    lines.append(f"*Response Time: {response_time:.0f}ms*")
                lines.append("")
                lines.append(content)
                lines.append("")
                lines.append("---")
                lines.append("")
    
    # Footer
    lines.append(_get_footer())
    
    return '\n'.join(lines)


def export_rankings_and_final(conversation: Dict[str, Any]) -> str:
    """
    Export rankings and final answer from the conversation.
    
    Args:
        conversation: Full conversation dict with messages
        
    Returns:
        Markdown-formatted string with rankings and final answer
    """
    lines = []
    
    # Header
    lines.append(_get_header(conversation))
    
    # Process each message
    query_counter = 0
    for message in conversation.get('messages', []):
        if message['role'] == 'user':
            query_counter += 1
            lines.append(f"## Query {query_counter}")
            lines.append("")
            lines.append(f"**User:** {message['content']}")
            lines.append("")
            
        elif message['role'] == 'assistant':
            lines.append("### Council Response")
            lines.append("")
            
            # Stage 3: Peer Rankings
            stage3 = message.get('stage3', [])
            if stage3:
                lines.append("#### Peer Rankings")
                lines.append("")
                for ranking in stage3:
                    model_name = ranking.get('model', 'Unknown Model')
                    content = ranking.get('content', '')
                    
                    lines.append(f"**Ranker: {model_name}**")
                    lines.append("")
                    
                    # Include parsed ranking if available
                    parsed = ranking.get('parsed_ranking', [])
                    if parsed:
                        lines.append("*Ranking:*")
                        for i, response_label in enumerate(parsed, 1):
                            lines.append(f"{i}. {response_label}")
                        lines.append("")
                    
                    lines.append(content)
                    lines.append("")
                    lines.append("---")
                    lines.append("")
            
            # Stage 4: Chairman Synthesis
            stage4 = message.get('stage4', {})
            if stage4:
                lines.append("#### Final Council Answer")
                lines.append("")
                model_name = stage4.get('model', 'Unknown Model')
                content = stage4.get('content', '')
                response_time = stage4.get('response_time_ms')
                
                lines.append(f"**Chairman: {model_name}**")
                if response_time and isinstance(response_time, (int, float)):
                    lines.append(f"*Response Time: {response_time:.0f}ms*")
                lines.append("")
                lines.append(content)
                lines.append("")
            
            lines.append("---")
            lines.append("")
    
    # Footer
    lines.append(_get_footer())
    
    return '\n'.join(lines)


def export_conversation_to_markdown(conversation: Dict[str, Any]) -> str:
    """
    Export a conversation to Markdown format with all stages (full export).
    
    Args:
        conversation: Full conversation dict with messages
        
    Returns:
        Markdown-formatted string
    """
    lines = []
    
    # Header
    lines.append(_get_header(conversation))
    
    # Process each message
    query_counter = 0
    for _, message in enumerate(conversation.get('messages', [])):
        if message['role'] == 'user':
            # User message
            query_counter += 1
            lines.append(f"## Query {query_counter}")
            lines.append("")
            lines.append(f"**User:** {message['content']}")
            lines.append("")
            
        elif message['role'] == 'assistant':
            # Assistant message with all 4 stages
            lines.append("### Council Response")
            lines.append("")
            
            # Stage 1: Individual Responses
            stage1 = message.get('stage1', [])
            if stage1:
                lines.append("#### Stage 1: Individual Model Responses")
                lines.append("")
                for response in stage1:
                    model_name = response.get('model', 'Unknown Model')
                    content = response.get('content', '')
                    response_time = response.get('response_time_ms')
                    
                    lines.append(f"**{model_name}**")
                    if response_time and isinstance(response_time, (int, float)):
                        lines.append(f"*Response Time: {response_time:.0f}ms*")
                    lines.append("")
                    lines.append(content)
                    lines.append("")
                    lines.append("---")
                    lines.append("")
            
            # Stage 2: Fact-Checking
            fact_check = message.get('fact_check', [])
            if fact_check:
                lines.append("#### Stage 2: Fact-Checking Analysis")
                lines.append("")
                for fc in fact_check:
                    model_name = fc.get('model', 'Unknown Model')
                    content = fc.get('content', '')
                    
                    lines.append(f"**Fact-Checker: {model_name}**")
                    lines.append("")
                    
                    # Include parsed summary if available
                    parsed = fc.get('parsed_summary', {})
                    if parsed.get('ratings'):
                        lines.append("*Ratings:*")
                        for response_label, rating in parsed['ratings'].items():
                            lines.append(f"- {response_label}: {rating}")
                        if parsed.get('most_reliable'):
                            lines.append(f"- Most Reliable: {parsed['most_reliable']}")
                        lines.append("")
                    
                    lines.append(content)
                    lines.append("")
                    lines.append("---")
                    lines.append("")
            
            # Stage 3: Peer Rankings
            stage3 = message.get('stage3', [])
            if stage3:
                lines.append("#### Stage 3: Peer Rankings")
                lines.append("")
                for ranking in stage3:
                    model_name = ranking.get('model', 'Unknown Model')
                    content = ranking.get('content', '')
                    
                    lines.append(f"**Ranker: {model_name}**")
                    lines.append("")
                    
                    # Include parsed ranking if available
                    parsed = ranking.get('parsed_ranking', [])
                    if parsed:
                        lines.append("*Ranking:*")
                        for i, response_label in enumerate(parsed, 1):
                            lines.append(f"{i}. {response_label}")
                        lines.append("")
                    
                    lines.append(content)
                    lines.append("")
                    lines.append("---")
                    lines.append("")
            
            # Stage 4: Chairman Synthesis
            stage4 = message.get('stage4', {})
            if stage4:
                lines.append("#### Stage 4: Final Council Answer")
                lines.append("")
                model_name = stage4.get('model', 'Unknown Model')
                content = stage4.get('content', '')
                response_time = stage4.get('response_time_ms')
                
                lines.append(f"**Chairman: {model_name}**")
                if response_time and isinstance(response_time, (int, float)):
                    lines.append(f"*Response Time: {response_time:.0f}ms*")
                lines.append("")
                lines.append(content)
                lines.append("")
            
            lines.append("---")
            lines.append("")
    
    # Footer
    lines.append(_get_footer())
    
    return '\n'.join(lines)


def export_conversation(conversation: Dict[str, Any], mode: ExportMode = "all") -> str:
    """
    Export a conversation in the specified mode.
    
    Args:
        conversation: Full conversation dict with messages
        mode: Export mode - "all", "final_only", or "rankings_and_final"
        
    Returns:
        Markdown-formatted string
    """
    if mode == "final_only":
        return export_final_answer_only(conversation)
    elif mode == "rankings_and_final":
        return export_rankings_and_final(conversation)
    else:  # "all" or default
        return export_conversation_to_markdown(conversation)
