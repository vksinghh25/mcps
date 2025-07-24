"""Shared Pydantic models."""

from pydantic import BaseModel, Field, validator
from typing import List, Optional
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


class SummarizeInput(TranscriptInput):
    """Input model for summarization operations."""

    style: str = Field(
        default="brief", description="Summary style (brief, detailed, etc.)"
    )

    @validator("style")
    def validate_style(cls, v):
        """Validate summary style."""
        valid_styles = ["brief", "detailed", "executive", "technical"]
        if v not in valid_styles:
            raise ValueError(f"Style must be one of: {valid_styles}")
        return v


class ToolResponse(BaseModel):
    """Standardized tool response model."""

    output: str = Field(..., description="The tool output")
    error: Optional[str] = Field(None, description="Error message if any")
