"""Shared configuration."""

import os
from typing import Optional


class LLMConfig:
    """LLM configuration."""

    MODEL = "gpt-3.5-turbo"
    MAX_TOKENS = 256
    TEMPERATURE = 0.7
    TIMEOUT = 30  # seconds


class MicroAgentConfig:
    """MicroAgent configuration."""

    SUMMARIZER_URL = "http://localhost:8001"
    TASK_EXTRACTOR_URL = "http://localhost:8002"
    PLUGIN_ENDPOINTS = [
        f"{SUMMARIZER_URL}/.well-known/mcp.json",
        f"{TASK_EXTRACTOR_URL}/.well-known/mcp.json",
    ]


def load_openai_key() -> str:
    """Load OpenAI API key from file."""
    try:
        with open("openai_key.txt", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(
            "openai_key.txt not found. Please create this file with your OpenAI API key."
        )
    except Exception as e:
        raise Exception(f"Error loading OpenAI key: {str(e)}")


def validate_transcript(transcript: str) -> None:
    """Validate transcript input."""
    if not transcript or not transcript.strip():
        raise ValueError("Transcript cannot be empty")

    if len(transcript.strip()) < 10:
        raise ValueError("Transcript must be at least 10 characters long")

    if len(transcript) > 10000:
        raise ValueError("Transcript is too long (max 10,000 characters)")
