"""Stateless execution primitives — satisfies ``contracts.ToolRuntimePort``."""

from pathlib import Path

from corge.contracts import ToolResult


class ToolRuntime:
    """Concrete tool runtime stub.  Satisfies ``contracts.ToolRuntimePort``."""

    def read(self, path: Path) -> ToolResult:
        raise NotImplementedError

    def write(self, path: Path, content: str) -> ToolResult:
        raise NotImplementedError

    def edit(self, path: Path, old: str, new: str) -> ToolResult:
        raise NotImplementedError

    def bash(self, command: str, cwd: Path) -> ToolResult:
        raise NotImplementedError
