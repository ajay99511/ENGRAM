"""
Tier 1 Agent Cards

Pre-defined agent cards for Tier 1 (Full A2A) agents.
These agents benefit from capability discovery and async task delegation.

Tier 1 Agents:
- Code Reviewer
- Workspace Analyzer
- Test Generator
- Dependency Auditor

Usage:
    from packages.agents.a2a.agents import register_tier1_agents
    
    register_tier1_agents()
"""

import logging
from typing import Any

from packages.agents.a2a.registry import register_agent, get_registry

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Agent Card Definitions
# ─────────────────────────────────────────────────────────────────────────────

CODE_REVIEWER_CARD = {
    "agent_id": "code-reviewer",
    "name": "Code Review Agent",
    "description": "Reviews code for security vulnerabilities, performance issues, and style problems",
    "capabilities": ["code_review", "security_scan", "style_check", "best_practices"],
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to file or directory to review",
            },
            "focus": {
                "type": "string",
                "enum": ["security", "performance", "style", "all"],
                "default": "all",
                "description": "Focus area for the review",
            },
            "max_issues": {
                "type": "integer",
                "default": 20,
                "description": "Maximum number of issues to report",
            },
        },
        "required": ["path"],
    },
    "output_schema": {
        "type": "object",
        "properties": {
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "file": {"type": "string"},
                        "line": {"type": "integer"},
                        "severity": {"type": "string", "enum": ["critical", "high", "medium", "low", "info"]},
                        "category": {"type": "string"},
                        "message": {"type": "string"},
                        "suggestion": {"type": "string"},
                    },
                },
            },
            "summary": {"type": "string"},
            "score": {
                "type": "object",
                "properties": {
                    "security": {"type": "integer"},
                    "performance": {"type": "integer"},
                    "style": {"type": "integer"},
                    "overall": {"type": "integer"},
                },
            },
        },
    },
    "permissions": {
        "read": ["src/**/*", "lib/**/*", "app/**/*", "packages/**/*"],
        "write": [],
        "execute": False,
    },
}

WORKSPACE_ANALYZER_CARD = {
    "agent_id": "workspace-analyzer",
    "name": "Workspace Analysis Agent",
    "description": "Analyzes project structure, dependencies, and codebase health",
    "capabilities": ["workspace_analysis", "dependency_audit", "structure_review", "tech_stack_detection"],
    "input_schema": {
        "type": "object",
        "properties": {
            "project_path": {
                "type": "string",
                "description": "Path to project root",
            },
            "depth": {
                "type": "integer",
                "default": 3,
                "description": "Directory depth to analyze",
            },
            "include_hidden": {
                "type": "boolean",
                "default": False,
                "description": "Include hidden directories (.git, .venv, etc.)",
            },
        },
        "required": ["project_path"],
    },
    "output_schema": {
        "type": "object",
        "properties": {
            "structure": {
                "type": "object",
                "description": "Directory structure overview",
            },
            "dependencies": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "version": {"type": "string"},
                        "type": {"type": "string"},
                    },
                },
            },
            "tech_stack": {
                "type": "array",
                "items": {"type": "string"},
            },
            "recommendations": {
                "type": "array",
                "items": {"type": "string"},
            },
            "metrics": {
                "type": "object",
                "properties": {
                    "total_files": {"type": "integer"},
                    "total_dirs": {"type": "integer"},
                    "code_files": {"type": "integer"},
                    "config_files": {"type": "integer"},
                    "docs_files": {"type": "integer"},
                },
            },
        },
    },
    "permissions": {
        "read": ["**/*"],
        "write": [],
        "execute": True,  # Needs execute for some analysis commands
    },
}

TEST_GENERATOR_CARD = {
    "agent_id": "test-generator",
    "name": "Test Generation Agent",
    "description": "Generates test cases for functions and classes",
    "capabilities": ["test_generation", "test_coverage", "mock_generation", "fixture_creation"],
    "input_schema": {
        "type": "object",
        "properties": {
            "source_path": {
                "type": "string",
                "description": "Path to source file or directory",
            },
            "test_framework": {
                "type": "string",
                "enum": ["pytest", "unittest", "jest", "mocha"],
                "default": "pytest",
                "description": "Test framework to use",
            },
            "coverage_target": {
                "type": "integer",
                "default": 80,
                "description": "Target code coverage percentage",
            },
            "include_integration": {
                "type": "boolean",
                "default": False,
                "description": "Include integration tests",
            },
        },
        "required": ["source_path"],
    },
    "output_schema": {
        "type": "object",
        "properties": {
            "tests_generated": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "file": {"type": "string"},
                        "function": {"type": "string"},
                        "test_name": {"type": "string"},
                        "coverage": {"type": "string"},
                    },
                },
            },
            "coverage_estimate": {"type": "number"},
            "files_created": {"type": "array", "items": {"type": "string"}},
            "recommendations": {"type": "array", "items": {"type": "string"}},
        },
    },
    "permissions": {
        "read": ["src/**/*", "lib/**/*", "app/**/*"],
        "write": ["tests/**/*", "test/**/*"],
        "execute": True,  # To run tests and check coverage
    },
}

DEPENDENCY_AUDITOR_CARD = {
    "agent_id": "dependency-auditor",
    "name": "Dependency Audit Agent",
    "description": "Checks for outdated, vulnerable, or unused dependencies",
    "capabilities": ["dependency_audit", "security_scan", "version_check", "unused_detection"],
    "input_schema": {
        "type": "object",
        "properties": {
            "project_path": {
                "type": "string",
                "description": "Path to project root",
            },
            "check_outdated": {
                "type": "boolean",
                "default": True,
                "description": "Check for outdated packages",
            },
            "check_vulnerabilities": {
                "type": "boolean",
                "default": True,
                "description": "Check for security vulnerabilities",
            },
            "check_unused": {
                "type": "boolean",
                "default": False,
                "description": "Check for unused dependencies",
            },
        },
        "required": ["project_path"],
    },
    "output_schema": {
        "type": "object",
        "properties": {
            "outdated": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "current": {"type": "string"},
                        "latest": {"type": "string"},
                        "severity": {"type": "string"},
                    },
                },
            },
            "vulnerabilities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "version": {"type": "string"},
                        "cve": {"type": "string"},
                        "severity": {"type": "string"},
                        "fixed_in": {"type": "string"},
                    },
                },
            },
            "unused": {
                "type": "array",
                "items": {"type": "string"},
            },
            "recommendations": {"type": "array", "items": {"type": "string"}},
        },
    },
    "permissions": {
        "read": [
            "**/requirements.txt",
            "**/package.json",
            "**/Cargo.toml",
            "**/go.mod",
            "**/pyproject.toml",
            "**/setup.py",
        ],
        "write": [],
        "execute": True,  # To run pip list, npm outdated, etc.
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Agent Handlers (Stubs - to be implemented)
# ─────────────────────────────────────────────────────────────────────────────

async def handle_code_review(task: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """
    Handle code review task.
    
    Args:
        task: Task parameters (path, focus, max_issues)
        **kwargs: Additional arguments
    
    Returns:
        Review results
    """
    # TODO: Implement actual code review logic
    # For now, return a stub response
    return {
        "findings": [],
        "summary": "Code review not yet implemented",
        "score": {
            "security": 0,
            "performance": 0,
            "style": 0,
            "overall": 0,
        },
    }


async def handle_workspace_analysis(task: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """
    Handle workspace analysis task.
    
    Args:
        task: Task parameters (project_path, depth, include_hidden)
        **kwargs: Additional arguments
    
    Returns:
        Analysis results
    """
    # TODO: Implement actual workspace analysis
    return {
        "structure": {},
        "dependencies": [],
        "tech_stack": [],
        "recommendations": [],
        "metrics": {
            "total_files": 0,
            "total_dirs": 0,
            "code_files": 0,
            "config_files": 0,
            "docs_files": 0,
        },
    }


async def handle_test_generation(task: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """
    Handle test generation task.
    
    Args:
        task: Task parameters (source_path, test_framework, coverage_target)
        **kwargs: Additional arguments
    
    Returns:
        Generation results
    """
    # TODO: Implement actual test generation
    return {
        "tests_generated": [],
        "coverage_estimate": 0.0,
        "files_created": [],
        "recommendations": [],
    }


async def handle_dependency_audit(task: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    """
    Handle dependency audit task.
    
    Args:
        task: Task parameters (project_path, check_outdated, check_vulnerabilities)
        **kwargs: Additional arguments
    
    Returns:
        Audit results
    """
    # TODO: Implement actual dependency audit
    return {
        "outdated": [],
        "vulnerabilities": [],
        "unused": [],
        "recommendations": [],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Registration
# ─────────────────────────────────────────────────────────────────────────────

def register_tier1_agents() -> None:
    """
    Register all Tier 1 agents with the A2A registry.
    """
    # Code Reviewer
    register_agent(
        agent_id=CODE_REVIEWER_CARD["agent_id"],
        name=CODE_REVIEWER_CARD["name"],
        description=CODE_REVIEWER_CARD["description"],
        capabilities=CODE_REVIEWER_CARD["capabilities"],
        input_schema=CODE_REVIEWER_CARD["input_schema"],
        output_schema=CODE_REVIEWER_CARD["output_schema"],
        permissions=CODE_REVIEWER_CARD["permissions"],
        handler=handle_code_review,
    )
    logger.info(f"Registered Tier 1 agent: {CODE_REVIEWER_CARD['agent_id']}")
    
    # Workspace Analyzer
    register_agent(
        agent_id=WORKSPACE_ANALYZER_CARD["agent_id"],
        name=WORKSPACE_ANALYZER_CARD["name"],
        description=WORKSPACE_ANALYZER_CARD["description"],
        capabilities=WORKSPACE_ANALYZER_CARD["capabilities"],
        input_schema=WORKSPACE_ANALYZER_CARD["input_schema"],
        output_schema=WORKSPACE_ANALYZER_CARD["output_schema"],
        permissions=WORKSPACE_ANALYZER_CARD["permissions"],
        handler=handle_workspace_analysis,
    )
    logger.info(f"Registered Tier 1 agent: {WORKSPACE_ANALYZER_CARD['agent_id']}")
    
    # Test Generator
    register_agent(
        agent_id=TEST_GENERATOR_CARD["agent_id"],
        name=TEST_GENERATOR_CARD["name"],
        description=TEST_GENERATOR_CARD["description"],
        capabilities=TEST_GENERATOR_CARD["capabilities"],
        input_schema=TEST_GENERATOR_CARD["input_schema"],
        output_schema=TEST_GENERATOR_CARD["output_schema"],
        permissions=TEST_GENERATOR_CARD["permissions"],
        handler=handle_test_generation,
    )
    logger.info(f"Registered Tier 1 agent: {TEST_GENERATOR_CARD['agent_id']}")
    
    # Dependency Auditor
    register_agent(
        agent_id=DEPENDENCY_AUDITOR_CARD["agent_id"],
        name=DEPENDENCY_AUDITOR_CARD["name"],
        description=DEPENDENCY_AUDITOR_CARD["description"],
        capabilities=DEPENDENCY_AUDITOR_CARD["capabilities"],
        input_schema=DEPENDENCY_AUDITOR_CARD["input_schema"],
        output_schema=DEPENDENCY_AUDITOR_CARD["output_schema"],
        permissions=DEPENDENCY_AUDITOR_CARD["permissions"],
        handler=handle_dependency_audit,
    )
    logger.info(f"Registered Tier 1 agent: {DEPENDENCY_AUDITOR_CARD['agent_id']}")
    
    logger.info("All Tier 1 agents registered successfully")


def get_tier1_agent_ids() -> list[str]:
    """Get list of Tier 1 agent IDs."""
    return [
        CODE_REVIEWER_CARD["agent_id"],
        WORKSPACE_ANALYZER_CARD["agent_id"],
        TEST_GENERATOR_CARD["agent_id"],
        DEPENDENCY_AUDITOR_CARD["agent_id"],
    ]
