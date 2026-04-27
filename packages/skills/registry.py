from __future__ import annotations
import logging
from typing import Dict, List, Type
from .base import Skill

logger = logging.getLogger(__name__)

class SkillRegistry:
    """
    Registry for all available skills in the workbench.
    """
    _instance: SkillRegistry | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SkillRegistry, cls).__new__(cls)
            cls._instance._skills = {}
        return cls._instance

    def register(self, skill: Skill):
        logger.info(f"Registering skill: {skill.name}")
        self._skills[skill.name] = skill

    def get_skill(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def list_skills(self) -> List[Skill]:
        return list(self._skills.values())

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        return [skill.get_schema() for skill in self._skills.values()]

registry = SkillRegistry()
