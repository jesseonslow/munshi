"""
munshi_summarizer

Publication summarization and metadata extraction pipeline for the
Mat Munshi MBRAS historical digital encyclopedia.
"""

from __future__ import annotations

from munshi_summarizer.config import SummarizerConfig
from munshi_summarizer.summarizer import PublicationSummarizer

__all__ = [
    "SummarizerConfig",
    "PublicationSummarizer",
]