"""Shared utilities."""

import openai
import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException
from .config import LLMConfig, load_openai_key

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI (lazy loading)
_openai_initialized = False


def _ensure_openai_initialized():
    """Ensure OpenAI is initialized when needed."""
    global _openai_initialized
    if not _openai_initialized:
        try:
            openai.api_key = load_openai_key()
            _openai_initialized = True
        except Exception as e:
            logger.error(f"Failed to load OpenAI key: {e}")
            raise


async def call_llm(
    prompt: str,
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
) -> str:
    """Call OpenAI LLM with error handling and logging."""
    try:
        _ensure_openai_initialized()
        logger.info(f"Calling LLM with prompt length: {len(prompt)}")

        response = openai.chat.completions.create(
            model=model or LLMConfig.MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens or LLMConfig.MAX_TOKENS,
            temperature=temperature or LLMConfig.TEMPERATURE,
            timeout=LLMConfig.TIMEOUT,
        )

        content = response.choices[0].message.content.strip()
        logger.info(f"LLM response received, length: {len(content)}")

        return content

    except openai.RateLimitError:
        logger.error("OpenAI rate limit exceeded")
        raise HTTPException(
            status_code=429, detail="Rate limit exceeded. Please try again later."
        )

    except openai.AuthenticationError:
        logger.error("OpenAI authentication failed")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key. Please check your OpenAI configuration.",
        )

    except openai.APIError as e:
        logger.error(f"OpenAI API error: {e}")
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error calling LLM: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to process request: {str(e)}"
        )


def build_tool_response(output: str) -> Dict[str, str]:
    """Build standardized tool response."""
    return {"output": output}


def log_tool_invocation(tool_name: str, input_data: Dict[str, Any]) -> None:
    """Log tool invocation for monitoring."""
    # Sanitize input data for logging (remove sensitive content)
    sanitized_data = {}
    for key, value in input_data.items():
        if key == "transcript":
            sanitized_data[key] = f"[{len(str(value))} chars]"
        else:
            sanitized_data[key] = (
                str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
            )

    logger.info(f"Tool invoked: {tool_name} with input: {sanitized_data}")


async def process_transcript_tool(data: Any, prompt: str) -> Dict[str, str]:
    """Process transcript-based tools."""
    result = await call_llm(prompt)
    return build_tool_response(result)


def format_response(
    tool_name: str, result: Dict[str, Any], transcript: str
) -> Dict[str, Any]:
    """Format sub-agent response into user-friendly format."""
    try:
        if tool_name == "summarize_transcript":
            # Handle MCP-compliant response structure
            output = result.get("output", "")
            if not output:
                return {
                    "type": "summary",
                    "title": "📋 Meeting Summary",
                    "content": "No summary generated",
                    "metadata": {
                        "tool_used": "summarize_transcript",
                        "transcript_length": len(transcript),
                    },
                }

            return {
                "type": "summary",
                "title": "📋 Meeting Summary",
                "content": output,
                "metadata": {
                    "tool_used": "summarize_transcript",
                    "transcript_length": len(transcript),
                },
            }

        elif tool_name == "highlight_key_points":
            # Handle the actual response structure from sub-agents
            output = result.get("output", "")
            if not output:
                return {
                    "type": "key_points",
                    "title": "🎯 Key Points & Insights",
                    "content": "No key points identified",
                    "metadata": {
                        "tool_used": "highlight_key_points",
                        "transcript_length": len(transcript),
                        "points_count": 0,
                    },
                }

            # Replace hyphens with dots for better formatting
            formatted_output = output.replace("- ", "• ")

            return {
                "type": "key_points",
                "title": "🎯 Key Points & Insights",
                "content": formatted_output,
                "metadata": {
                    "tool_used": "highlight_key_points",
                    "transcript_length": len(transcript),
                    "points_count": output.count("-"),  # Rough count of bullet points
                },
            }

        elif tool_name == "extract_tasks":
            # Handle the actual response structure from task extractor
            # The task extractor returns JSON with "actionable_tasks" field wrapped in "output"
            output = result.get("output", "")
            if not output:
                return {
                    "type": "tasks",
                    "title": "📝 Action Items & Tasks",
                    "content": "No tasks identified",
                    "metadata": {
                        "tool_used": "extract_tasks",
                        "transcript_length": len(transcript),
                        "tasks_count": 0,
                    },
                }

            try:
                # Parse the JSON from the output field
                import json

                parsed_output = json.loads(output)
                actionable_tasks = parsed_output.get("actionable_tasks", [])

                if not actionable_tasks:
                    return {
                        "type": "tasks",
                        "title": "📝 Action Items & Tasks",
                        "content": "No tasks identified",
                        "metadata": {
                            "tool_used": "extract_tasks",
                            "transcript_length": len(transcript),
                            "tasks_count": 0,
                        },
                    }

                # Format the tasks as a bulleted list
                formatted_tasks = []
                for i, task in enumerate(actionable_tasks, 1):
                    formatted_tasks.append(f"{i}. {task}")

                return {
                    "type": "tasks",
                    "title": "📝 Action Items & Tasks",
                    "content": "\n".join(formatted_tasks),
                    "metadata": {
                        "tool_used": "extract_tasks",
                        "transcript_length": len(transcript),
                        "tasks_count": len(actionable_tasks),
                    },
                }
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from task extractor: {e}")
                return {
                    "type": "tasks",
                    "title": "📝 Action Items & Tasks",
                    "content": f"Error parsing task response: {str(e)}\n\nRaw output: {output}",
                    "metadata": {
                        "tool_used": "extract_tasks",
                        "transcript_length": len(transcript),
                        "tasks_count": 0,
                    },
                }

        else:
            # Fallback for unknown tools
            return {
                "type": "unknown",
                "title": f"🔧 {tool_name.replace('_', ' ').title()}",
                "content": str(result),
                "metadata": {
                    "tool_used": tool_name,
                    "transcript_length": len(transcript),
                },
            }

    except Exception as e:
        logger.error(f"Error formatting response for {tool_name}: {e}")
        return {
            "type": "error",
            "title": "❌ Processing Error",
            "content": f"An error occurred while formatting the response: {str(e)}\n\nRaw result: {str(result)}",
            "metadata": {
                "tool_used": tool_name,
                "transcript_length": len(transcript),
                "error": str(e),
            },
        }
