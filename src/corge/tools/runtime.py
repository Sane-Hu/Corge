"""Stateless execution primitives — satisfies ``contracts.ToolRuntimePort``."""
from pathlib import Path

from corge.contracts import ToolAction, ToolResult


class ToolRuntime:
    """Concrete tool runtime.  Satisfies ``contracts.ToolRuntimePort``."""

    def read(self, path: Path) -> ToolResult:
        try:
            content = Path(path).read_text(encoding="utf-8")
            return ToolResult(
                action=ToolAction.READ, output=content, success=True
            )
        except FileNotFoundError:
            return ToolResult(
                action=ToolAction.READ,
                output="",
                success=False,
                stderr=f"File not found: {path}",
            )
        except IsADirectoryError:
            return ToolResult(
                action=ToolAction.READ,
                output="",
                success=False,
                stderr=f"Path is a directory, not a file: {path}",
            )
        except OSError as exc:
            return ToolResult(
                action=ToolAction.READ,
                output="",
                success=False,
                stderr=f"Failed to read {path}: {exc}",
            )

    def write(self, path: Path, content: str) -> ToolResult:
        try:
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return ToolResult(
                action=ToolAction.WRITE,
                output=f"path: {target}, bytes_written: {len(content.encode('utf-8'))}",
                success=True,
            )
        except OSError as exc:
            return ToolResult(
                action=ToolAction.WRITE,
                output="",
                success=False,
                stderr=f"Failed to write {path}: {exc}",
            )

    def edit(self, path: Path, old: str, new: str) -> ToolResult:
        try:
            target = Path(path)
            original = target.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ToolResult(
                action=ToolAction.EDIT,
                output="",
                success=False,
                stderr=f"File not found: {path}",
            )
        except OSError as exc:
            return ToolResult(
                action=ToolAction.EDIT,
                output="",
                success=False,
                stderr=f"Failed to read {path}: {exc}",
            )

        if old not in original:
            return ToolResult(
                action=ToolAction.EDIT,
                output="",
                success=False,
                stderr=f"Target string not found in {path}",
            )

        occurrences = original.count(old)
        updated = original.replace(old, new)

        try:
            target.write_text(updated, encoding="utf-8")
        except OSError as exc:
            return ToolResult(
                action=ToolAction.EDIT,
                output="",
                success=False,
                stderr=f"Failed to write {path}: {exc}",
            )

        return ToolResult(
            action=ToolAction.EDIT,
            output=f"path: {target}, occurrences_replaced: {occurrences}",
            success=True,
        )

    def bash(self, command: str, cwd: Path) -> ToolResult:
        raise NotImplementedError


