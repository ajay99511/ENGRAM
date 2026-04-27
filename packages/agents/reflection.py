from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from packages.model_gateway.client import chat
from packages.shared.config import settings

logger = logging.getLogger(__name__)

class ReflectionResult(BaseModel):
    is_successful: bool
    critique: str
    suggestions: List[str] = []
    should_retry: bool = False

class Reflector:
    """
    Reflector agent that analyzes agent execution traces and provides feedback.
    Follows the 'Memento-Skills' Read-Write Reflection pattern.
    """
    
    async def reflect(self, task: str, execution_trace: List[Dict[str, Any]]) -> ReflectionResult:
        """
        Analyzes a task and its execution trace to determine success and provide critique.
        """
        trace_str = "\n".join([f"- {t.get('step', 'Step')}: {t.get('action', 'Action')} with result success={t.get('success', True)}" for t in execution_trace])
        
        prompt = f"""
        Analyze the following agent execution trace for the task: "{task}"
        
        Execution Trace:
        {trace_str}
        
        Determine if the task was successfully completed. Provide a detailed critique and suggestions for improvement if needed.
        Return your response in strict JSON format:
        {{
            "is_successful": bool,
            "critique": "string",
            "suggestions": ["suggestion1", "suggestion2"],
            "should_retry": bool
        }}
        """
        
        try:
            resp = await chat(
                messages=[{"role": "system", "content": "You are an expert agent performance critic."},
                          {"role": "user", "content": prompt}],
                model="active"
            )
            
            # Simple JSON extraction (best effort)
            import json
            import re
            match = re.search(r'\{.*\}', resp, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                return ReflectionResult(**data)
            
            return ReflectionResult(is_successful=True, critique="Could not parse reflection JSON", suggestions=[])
        except Exception as e:
            logger.error(f"Reflection failed: {e}")
            return ReflectionResult(is_successful=True, critique=f"Reflection error: {e}", suggestions=[])
