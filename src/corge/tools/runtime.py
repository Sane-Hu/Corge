"""Stateless execution primitives — satisfies ``contracts.ToolRuntimePort``."""
from pathlib import Path
import subprocess

from corge.contracts import ToolResult


class ToolRuntime:
    """Concrete tool runtime.  Satisfies ``contracts.ToolRuntimePort``."""

    def read(self, path: Path) -> ToolResult:
        try:
            content = Path(path).read_text(encoding="utf-8")
            return ToolResult(success=True, data=content, error=None)
        except FileNotFoundError:
            return ToolResult(success=False, data=None, error=f"File not found: {path}")
        except IsADirectoryError:
            return ToolResult(success=False, data=None, error=f"Path is a directory, not a file: {path}")
        except OSError as exc:
            return ToolResult(success=False, data=None, error=f"Failed to read {path}: {exc}")

    def write(self, path: Path, content: str) -> ToolResult:
        try:
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return ToolResult(
                success=True,
                data={"path": str(target), "bytes_written": len(content.encode("utf-8"))},
                error=None,
            )
        except OSError as exc:
            return ToolResult(success=False, data=None, error=f"Failed to write {path}: {exc}")

    def edit(self, path: Path, old: str, new: str) -> ToolResult:
        try:
            target = Path(path)
            original = target.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ToolResult(success=False, data=None, error=f"File not found: {path}")
        except OSError as exc:
            return ToolResult(success=False, data=None, error=f"Failed to read {path}: {exc}")

        if old not in original:
            return ToolResult(success=False, data=None, error=f"Target string not found in {path}")

        occurrences = original.count(old)
        updated = original.replace(old, new)

        try:
            target.write_text(updated, encoding="utf-8")
        except OSError as exc:
            return ToolResult(success=False, data=None, error=f"Failed to write {path}: {exc}")

        return ToolResult(
            success=True,
            data={"path": str(target), "occurrences_replaced": occurrences},
            error=None,
        )

    def bash(self, command: str, cwd: Path) -> ToolResult:
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=120,
            )
            return ToolResult(
                success=result.returncode == 0,
                data={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                },
                error=None if result.returncode == 0 else f"Command exited with code {result.returncode}",
            )
        except subprocess.TimeoutExpired as exc:
            return ToolResult(
                success=False,
                data={"stdout": exc.stdout or "", "stderr": exc.stderr or ""},
                error="Command timed out",
            )
        except OSError as exc:
            return ToolResult(success=False, data=None, error=f"Failed to execute command: {exc}")