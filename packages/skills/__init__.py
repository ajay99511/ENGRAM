from .registry import registry
from .filesystem import FilesystemSkill

# Initialize registry with built-in skills
registry.register(FilesystemSkill())
