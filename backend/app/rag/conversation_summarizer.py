"""Conversation History Summarizer (C-CHATSVC, SRS Optional Advanced Enhancement).

Generates condensed semantic summaries of older conversation turns
to preserve context window efficiency while retaining recent raw messages.
"""

from typing import List, Dict, Optional
from backend.app.core.logging import logger


class ConversationSummarizer:
    """Condenses older conversation turns into concise summary paragraphs."""

    def __init__(self, max_recent_raw: int = 4):
        self.max_recent_raw = max_recent_raw

    def partition_history(
        self,
        history: List[Dict[str, str]],
    ) -> tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """Splits conversation turns into (older_turns_to_summarize, recent_raw_turns)."""
        if len(history) <= self.max_recent_raw:
            return [], history
        return history[:-self.max_recent_raw], history[-self.max_recent_raw:]

    def summarize_turns(
        self,
        older_turns: List[Dict[str, str]],
    ) -> Optional[str]:
        """Summarizes older conversation turns into a compact paragraph.

        Uses deterministic semantic keypoint aggregation for zero latency and zero RAM.
        """
        if not older_turns:
            return None

        topics: List[str] = []
        for turn in older_turns:
            role = turn.get("role", "user")
            content = turn.get("content", "").strip()
            if not content:
                continue

            first_sentence = content.split(".")[0].strip()
            if role == "user":
                topics.append(f"Student asked about: '{first_sentence[:80]}'")
            else:
                topics.append(f"Assistant clarified: '{first_sentence[:80]}'")

        summary = "Earlier conversation summary: " + "; ".join(topics) + "."
        logger.info("Summarized %d older turns into: %s", len(older_turns), summary[:100])
        return summary


conversation_summarizer = ConversationSummarizer()
