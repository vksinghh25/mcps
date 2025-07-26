"""Summarizer Agent."""

from fastapi import FastAPI, HTTPException
from typing import Dict, Any
import logging

from .models import TranscriptInput, InvokeRequest
from .utils import process_transcript_tool, log_tool_invocation

# Configure logging
logger = logging.getLogger(__name__)

summarizer_app = FastAPI(
    title="Summarizer Agent",
    description="Agent for summarizing transcripts and extracting key points",
    version="1.0.0",
)


@summarizer_app.get("/.well-known/mcp.json")
def discover() -> Dict[str, Any]:
    """Discover available tools for this agent (MCP compliant)."""
    return {
        "tools": [
            {
                "name": "summarize_transcript",
                "description": "Summarizes a transcript into a short paragraph.",
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
            },
            {
                "name": "highlight_key_points",
                "description": "Extracts 3–5 main insights from a transcript as bullet points.",
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
            },
        ],
        "resources": [],
        "capabilities": {"tools": {}},
    }


@summarizer_app.post("/invoke")
async def invoke_tool(request: InvokeRequest) -> Dict[str, Any]:
    """Route tool invocation to appropriate handler."""
    try:
        log_tool_invocation(request.name, request.arguments)

        if request.name == "summarize_transcript":
            # Validate and parse arguments
            data = TranscriptInput(**request.arguments)

            prompt = (
                "Summarize the following transcript in a brief, concise style:\n\n"
                f"{data.transcript}\n\n"
                "Please provide a clear, concise summary that captures the main points and outcomes of this meeting."
            )

            result = await process_transcript_tool(data, prompt)

            # Return MCP-compliant response
            return {"content": [{"type": "text", "text": result["output"]}]}

        elif request.name == "highlight_key_points":
            # Validate and parse arguments
            data = TranscriptInput(**request.arguments)

            prompt = (
                "Extract 3-5 key insights from the following transcript as bullet points:\n\n"
                f"{data.transcript}\n\n"
                "Please provide the key points in a clear, bulleted format. Focus on:\n"
                "- Main decisions made\n"
                "- Action items identified\n"
                "- Important insights or findings\n"
                "- Next steps discussed"
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


@summarizer_app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "agent": "summarizer"}
