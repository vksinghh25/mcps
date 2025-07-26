"""Shared Pydantic models."""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from .config import validate_transcript


class TranscriptInput(BaseModel):
    """Base input model for transcript-based operations."""

    transcript: str = Field(
        ...,
        description="The meeting transcript to process",
        min_length=10,
        max_length=10000,
    )

    @validator("transcript")
    def validate_transcript_content(cls, v):
        """Validate transcript content."""
        validate_transcript(v)
        return v


class ToolResponse(BaseModel):
    """Standardized tool response model."""

    output: str = Field(..., description="The tool output")
    error: Optional[str] = Field(None, description="Error message if any")


class InvokeRequest(BaseModel):
    """MCP-compliant tool invocation request model."""

    name: str = Field(..., description="Name of the tool to invoke")
    arguments: Dict[str, Any] = Field(..., description="Arguments for the tool")
