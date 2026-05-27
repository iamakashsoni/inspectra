"""Abstract base class for all LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """All LLM providers must implement this interface."""

    @abstractmethod
    async def review_code(self, prompt: str) -> str:
        """
        Send a prompt to the LLM and return the raw text response.

        Args:
            prompt: The fully-formed review prompt including diff content.

        Returns:
            Raw LLM response text.
        """
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__
