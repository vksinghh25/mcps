"""Task Extractor Agent."""

from fastapi import FastAPI, HTTPException
from typing import Dict, Any
import logging

from .models import TranscriptInput, InvokeRequest
from .utils import process_transcript_tool, log_tool_invocation

# Configure logging
logger = logging.getLogger(__name__)

task_app = FastAPI(
    title="Task Extractor Agent",
    description="Agent for extracting tasks and assigning due dates",
    version="1.0.0",
)


@task_app.get("/.well-known/mcp.json")
def discover() -> Dict[str, Any]:
    """Discover available tools for this agent (MCP compliant)."""
    return {
        "tools": [
            {
                "name": "extract_tasks",
                "description": "Finds actionable tasks mentioned in a transcript and returns them as a JSON list.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "transcript": {
                            "type": "string",
                            "description": "The meeting transcript to process",
                            "minLength": 10,
                            "maxLength": 10000,
                        }
                    },
                    "required": ["transcript"],
                },
            }
        ],
        "resources": [],
        "capabilities": {"tools": {}},
    }


@task_app.post("/invoke")
async def invoke_tool(request: InvokeRequest) -> Dict[str, Any]:
    """Route tool invocation to appropriate handler."""
    try:
        log_tool_invocation(request.name, request.arguments)

        if request.name == "extract_tasks":
            # Validate and parse arguments
            data = TranscriptInput(**request.arguments)

            prompt = (
                "Extract all actionable tasks from the following transcript as a JSON list:\n\n"
                f"{data.transcript}\n\n"
                "Please return the tasks in this exact JSON format:\n"
                "{\n"
                '  "actionable_tasks": [\n'
                '    "Task 1 description",\n'
                '    "Task 2 description",\n'
                '    "Task 3 description"\n'
                "  ]\n"
                "}\n\n"
                "Focus on:\n"
                "- Specific action items assigned to people\n"
                "- Tasks with clear deliverables\n"
                "- Deadlines or timeframes mentioned\n"
                "- Follow-up actions required"
            )

            result = await process_transcript_tool(data, prompt)

            # Return MCP-compliant response
            return {"content": [{"type": "text", "text": result["output"]}]}

        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {request.name}")

    except HTTPException:
        # Re-raise HTTP exceptions as they're already properly formatted
        raise
    except Exception as e:
        logger.error(f"Error in invoke_tool: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to invoke tool: {str(e)}")


@task_app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "agent": "task_extractor"}
