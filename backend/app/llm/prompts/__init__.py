"""Versioned prompt templates for each analysis stage.

Bump ``PROMPT_VERSION`` whenever any prompt text or output schema changes so
cached analyses produced by older prompts are invalidated.
"""

from app.llm.prompts.comparison import COMPARISON_PROMPT
from app.llm.prompts.competitor import EXTRACTION_PROMPT
from app.llm.prompts.scadable import SCADABLE_PROMPT

PROMPT_VERSION = "2026-10-19.1"

__all__ = ["COMPARISON_PROMPT", "EXTRACTION_PROMPT", "PROMPT_VERSION", "SCADABLE_PROMPT"]
