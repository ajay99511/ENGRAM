from __future__ import annotations
from typing import Any, Dict
from .base import Skill, SkillResult
from packages.tools import fs

class FilesystemSkill(Skill):
    name = "filesystem"
    description = "Read, write, search and manage files and directories locally."

    async def execute(self, action: str, args: Dict[str, Any]) -> SkillResult:
        """
        Executes a filesystem action.
        Actions: read_file, write_file, find_files, list_directory, file_info
        """
        try:
            if action == "read_file":
                res = await fs.read_file(**args)
            elif action == "write_file":
                res = await fs.write_file(**args)
            elif action == "find_files":
                res = await fs.find_files(**args)
            elif action == "list_directory":
                res = await fs.list_directory(**args)
            elif action == "file_info":
                res = await fs.file_info(**args)
            else:
                return SkillResult(success=False, output=None, error=f"Unknown action: {action}")

            if "error" in res:
                return SkillResult(success=False, output=res, error=res["error"])
            
            return SkillResult(success=True, output=res)
        except Exception as e:
            return SkillResult(success=False, output=None, error=str(e))

    def get_schema(self) -> Dict[str, Any]:
        schema = super().get_schema()
        schema["actions"] = {
            "read_file": {
                "description": "Read file contents",
                "parameters": {"path": "str", "max_lines": "int?", "encoding": "str"}
            },
            "write_file": {
                "description": "Write to a file",
                "parameters": {"path": "str", "content": "str", "create_dirs": "bool"}
            },
            "find_files": {
                "description": "Search for files by pattern",
                "parameters": {"directory": "str", "pattern": "str", "recursive": "bool"}
            },
            "list_directory": {
                "description": "List directory contents",
                "parameters": {"path": "str", "show_hidden": "bool"}
            }
        }
        return schema
