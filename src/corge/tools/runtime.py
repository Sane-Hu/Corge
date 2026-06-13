"""Stateless execution primitive boundaries."""

from pathlib import Path

from corge.contracts import ToolResult


class ToolRuntime:
    """Tool responsibilities from docs/04-module-contracts.md."""

    def read(self, path: Path) -> ToolResult:
        raise NotImplementedError

    def write(self, path: Path, content: str) -> ToolResult:
        raise NotImplementedError

    def edit(self, path: Path, old: str, new: str) -> ToolResult:
        raise NotImplementedError

    def bash(self, command: str, cwd: Path) -> ToolResult:
        raise NotImplementedError

