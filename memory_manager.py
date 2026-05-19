"""
Memory Manager - Context management and token calculation.
Implements sliding window to prevent context overflow.
"""

from typing import List, Dict, Optional
import tiktoken

import config


class MemoryManager:
    """
    Manages conversation history with token-based sliding window.
    Prevents context overflow while maintaining conversation continuity.
    """

    def __init__(self, max_tokens: int = None):
        self.max_tokens = max_tokens or config.MAX_TOKENS
        self.messages: List[Dict[str, str]] = []
        try:
            self.encoder = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.encoder = None

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        if self.encoder:
            return len(self.encoder.encode(text))
        return len(text) // 4

    def _calculate_total_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Calculate total tokens in messages list."""
        total = 0
        for msg in messages:
            total += self._estimate_tokens(msg.get("content", ""))
            total += self._estimate_tokens(msg.get("role", ""))
            total += 4
        return total

    def add_message(self, role: str, content: str):
        """Add a message to conversation history."""
        self.messages.append({"role": role, "content": content})

    def get_messages(self) -> List[Dict[str, str]]:
        """Get current messages, applying sliding window if needed."""
        total_tokens = self._calculate_total_tokens(self.messages)

        if total_tokens <= self.max_tokens:
            return self.messages.copy()

        pruned_messages = []
        system_msg = None

        for msg in self.messages:
            if msg["role"] == "system":
                system_msg = msg
                break

        if system_msg:
            pruned_messages.append(system_msg)

        conversation_msgs = [m for m in self.messages if m["role"] != "system"]

        while conversation_msgs:
            msg = conversation_msgs.pop(0)
            pruned_messages.append(msg)

            current_tokens = self._calculate_total_tokens(pruned_messages)
            if current_tokens > self.max_tokens * 0.9:
                break

        return pruned_messages

    def clear(self):
        """Clear conversation history."""
        self.messages = []

    def get_token_count(self) -> int:
        """Get current total token count."""
        return self._calculate_total_tokens(self.messages)