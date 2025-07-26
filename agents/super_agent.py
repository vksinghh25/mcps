"""Super Agent."""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Dict, Any, List
import httpx
import logging

from .config import MicroAgentConfig
from .utils import call_llm, log_tool_invocation, format_response

# Configure logging
logger = logging.getLogger(__name__)

super_app = FastAPI(
    title="Super Agent",
    description="Orchestrates calls to sub-agents based on user prompts",
    version="1.0.0",
)

# Mount static files for serving the web UI
super_app.mount("/static", StaticFiles(directory="."), name="static")

# Global tool registry populated at startup
tool_registry: Dict[str, Dict[str, Any]] = {}


class AskInput(BaseModel):
    """Input model for the ask endpoint."""

    transcript: str = Field(
        ...,
        description="The meeting transcript to analyze",
        min_length=10,
        max_length=10000,
    )
    prompt: str = Field(
        ...,
        description="User's request/prompt for analysis",
        min_length=1,
        max_length=500,
    )


async def fetch_tools_from_plugin(endpoint: str) -> List[Dict[str, Any]]:
    """
    Fetch tool definitions from a plugin endpoint.

    Args:
        endpoint: The plugin endpoint URL

    Returns:
        List of tool definitions

    Raises:
        HTTPException: If the request fails
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(endpoint)
            response.raise_for_status()
            data = response.json()
            return data.get("tools", [])
    except httpx.RequestError as e:
        logger.error(f"Failed to fetch tools from {endpoint}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch tools from {endpoint}"
        )
    except Exception as e:
        logger.error(f"Error processing response from {endpoint}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error processing response from {endpoint}"
        )


async def populate_tool_registry():
    """Populate the tool registry by fetching tools from all sub-agents."""
    global tool_registry
    tool_registry.clear()

    for endpoint in MicroAgentConfig.PLUGIN_ENDPOINTS:
        try:
            tools = await fetch_tools_from_plugin(endpoint)
            for tool in tools:
                # Use 'name' field as per MCP standards
                tool_registry[tool["name"]] = tool
                logger.info(f"Registered tool: {tool['name']}")
        except Exception as e:
            logger.error(f"Failed to populate tools from {endpoint}: {e}")

    logger.info(f"Tool registry populated: {list(tool_registry.keys())}")


def determine_sub_agent_url(tool_name: str) -> str:
    """
    Determine which sub-agent URL to use based on tool name.

    Args:
        tool_name: Name of the tool

    Returns:
        Base URL for the appropriate sub-agent
    """
    if "summarize" in tool_name or "highlight" in tool_name:
        return MicroAgentConfig.SUMMARIZER_URL
    elif "extract" in tool_name or "assign" in tool_name:
        return MicroAgentConfig.TASK_EXTRACTOR_URL
    else:
        raise ValueError(f"Unknown tool type: {tool_name}")


@super_app.get("/")
async def serve_ui() -> HTMLResponse:
    """Serve the web UI."""
    try:
        with open("index.html", "r") as f:
            content = f.read()
        return HTMLResponse(content=content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="UI file not found")


@super_app.post("/ask")
async def ask(data: AskInput) -> Dict[str, Any]:
    """
    Route user request to appropriate sub-agent based on LLM analysis.

    Args:
        data: Input containing transcript and user prompt

    Returns:
        Response from the selected sub-agent
    """
    try:
        log_tool_invocation(
            "ask", {"transcript_length": len(data.transcript), "prompt": data.prompt}
        )

        # Build tool list for LLM prompt
        tool_list = "\n".join(
            [
                f"- {tool['name']}: {tool.get('description', '')}"
                for tool in tool_registry.values()
            ]
        )

        llm_prompt = f"""Given the following user prompt and transcript, which tool should be used?

Available tools (respond with the EXACT tool name):
{tool_list}

User prompt: {data.prompt}
Transcript: {data.transcript[:500]}...

IMPORTANT: Respond with ONLY the exact tool name from the list above. Do not add any additional text or descriptions."""

        # Get tool selection from LLM
        tool_name = await call_llm(llm_prompt, max_tokens=32, temperature=0)
        tool_name = tool_name.strip()

        # Clean up the tool name - remove any extra text and get just the tool name
        tool_name = tool_name.split()[0] if tool_name else ""

        logger.info(f"LLM selected tool: {tool_name}")

        if tool_name not in tool_registry:
            logger.error(f"Tool '{tool_name}' not found in registry")
            return {
                "error": f"Tool '{tool_name}' not found in registry. Available tools: {list(tool_registry.keys())}"
            }

        # Prepare payload for sub-agent
        tool = tool_registry[tool_name]
        payload = {"transcript": data.transcript}

        # Add optional parameters based on tool requirements
        if "context" in tool.get("parameters", {}).get("properties", {}):
            payload["context"] = "end of week"

        # Determine sub-agent URL and make request using MCP standard
        sub_agent_url = determine_sub_agent_url(tool_name)
        invoke_url = f"{sub_agent_url}/invoke"

        # Prepare MCP standard request
        mcp_payload = {"name": tool_name, "arguments": payload}

        logger.info(f"Calling sub-agent: {invoke_url} with tool: {tool_name}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(invoke_url, json=mcp_payload)
            response.raise_for_status()

            try:
                result = response.json()
                logger.info(f"Sub-agent response received for {tool_name}")

                # Extract content from MCP-compliant response
                if "content" in result and result["content"]:
                    # Get the text content from the MCP response
                    mcp_content = result["content"][0]
                    if mcp_content.get("type") == "text":
                        # Convert MCP response to our internal format
                        internal_result = {"output": mcp_content["text"]}
                    else:
                        internal_result = {"output": str(mcp_content)}
                else:
                    # Fallback for non-MCP responses
                    internal_result = result

                # Format the response based on the tool type
                return format_response(tool_name, internal_result, data.transcript)
            except Exception as e:
                logger.error(f"Failed to parse response from sub-agent: {e}")
                return {
                    "error": "Failed to parse response from sub-agent.",
                    "raw": response.text,
                }

    except HTTPException:
        # Re-raise HTTP exceptions as they're already properly formatted
        raise
    except Exception as e:
        logger.error(f"Error in ask endpoint: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to process request: {str(e)}"
        )


@super_app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agent": "super",
        "tools_registered": str(len(tool_registry)),
    }


@super_app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    await populate_tool_registry()
