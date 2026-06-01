"""
Abstract base class for all domain agents.

Each agent receives the shared orchestration state and returns a response string.
Concrete agents wrap downstream services (NLP-SQL, route optimization, etc.).
"""

from abc import ABC, abstractmethod

from orchestrator.state import AgentState


class BaseAgent(ABC):
    """Contract that every registered agent must implement."""

    @abstractmethod
    def execute(self, state: AgentState) -> str:
        """Run the agent logic and return a response string."""
