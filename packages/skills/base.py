from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class SkillResult(BaseModel):
    success: bool
    output: Any
    error: Optional[str] = None
    trace: List[Dict[str, Any]] = Field(default_factory=list)

class Skill(ABC):
    """
    Base class for all skills in the Personal Agent Workbench.
    A skill is a cohesive unit of capability (Bounded Context).
    """
    name: str
    description: str
    version: str = "1.0.0"

    @abstractmethod
    async def execute(self, action: str, args: Dict[str, Any]) -> SkillResult:
        pass

    def get_schema(self) -> Dict[str, Any]:
        """Returns the JSON schema for this skill's actions."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
        }
