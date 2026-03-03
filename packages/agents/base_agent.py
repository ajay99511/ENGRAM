"""
Agent Skeletons — placeholder agents that demonstrate the routing pattern.

These will be replaced with CrewAI agents in a future iteration.
Each agent implements:
    async def run(context: str, message: str) -> str
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from packages.model_gateway.client import chat

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base for all agents."""

    name: str = "base"

    @abstractmethod
    async def run(self, context: str, message: str) -> str:
        """Process a message with optional context and return a response."""
        ...


class PlannerAgent(BaseAgent):
    """
    Planner — breaks a user request into actionable steps.
    (Placeholder: just asks the LLM to make a plan.)
    """

    name = "planner"

    async def run(self, context: str, message: str) -> str:
        system = (
            "You are a planning assistant. Break the user's request into "
            "clear, numbered steps. Be concise and actionable."
        )
        messages = [
            {"role": "system", "content": system},
        ]
        if context:
            messages.append({"role": "system", "content": f"Context:\n{context}"})
        messages.append({"role": "user", "content": message})

        return await chat(messages, model="local")


class ResearcherAgent(BaseAgent):
    """
    Researcher — gathers information about a topic.
    (Placeholder: asks the LLM to summarize knowledge.)
    """

    name = "researcher"

    async def run(self, context: str, message: str) -> str:
        system = (
            "You are a research assistant. Provide comprehensive, factual "
            "information about the user's query. Cite what you know and "
            "note what you're uncertain about."
        )
        messages = [
            {"role": "system", "content": system},
        ]
        if context:
            messages.append({"role": "system", "content": f"Context:\n{context}"})
        messages.append({"role": "user", "content": message})

        return await chat(messages, model="local")


class SynthesizerAgent(BaseAgent):
    """
    Synthesizer — combines information into a coherent response.
    (Placeholder: asks the LLM to synthesize.)
    """

    name = "synthesizer"

    async def run(self, context: str, message: str) -> str:
        system = (
            "You are a synthesis assistant. Take the provided context and "
            "the user's question, then produce a clear, well-structured response."
        )
        messages = [
            {"role": "system", "content": system},
        ]
        if context:
            messages.append({"role": "system", "content": f"Context:\n{context}"})
        messages.append({"role": "user", "content": message})

        return await chat(messages, model="local")
