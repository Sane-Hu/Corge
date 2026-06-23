"""Stateless execution primitives — satisfies ``contracts.ToolRuntimePort``."""

from pathlib import Path

from corge.contracts import ToolAction, ToolResult


class ToolRuntime:
    """Concrete tool runtime.  Satisfies ``contracts.ToolRuntimePort``."""

    def read(self, path: Path) -> ToolResult:
        try:
            content = Path(path).read_text(encoding="utf-8")
            return ToolResult(action=ToolAction.READ, output=content, success=True)
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

        occurrences = original.count(old)
        if occurrences == 0:
            return ToolResult(
                action=ToolAction.EDIT,
                output="",
                success=False,
                stderr=f"String not found in {path}. Make sure to include exact whitespace.",
            )
        if occurrences > 1:
            return ToolResult(
                action=ToolAction.EDIT,
                output="",
                success=False,
                stderr=(
                    f"Ambiguous edit: old string appears {occurrences} times in {path}. "
                    "Include more surrounding context in 'old' to uniquely identify the target."
                ),
            )

        updated = original.replace(old, new, 1)

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
            output=f"Successfully edited {path}",
            success=True,
            stderr="",
        )

    def bash(self, command: str, cwd: Path) -> ToolResult:
        # security: `shell=True` allows shell expansion and metacharacters
        # (e.g., pipes, redirects).
        # This is an intentional design choice for maximum flexibility but
        # creates a shell injection risk.
        # It relies entirely on the human approval gateway (FR-009) to catch
        # malicious commands.
        timeout = 300  # 5 minutes default timeout
        try:
            import subprocess

            process = subprocess.Popen(
                command,
                cwd=cwd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                # Get any partial output
                stdout, stderr = process.communicate()
                return ToolResult(
                    action=ToolAction.BASH,
                    output=stdout,
                    success=False,
                    stderr=f"Command timed out after {timeout} seconds\n{stderr}",
                )

            success = process.returncode == 0
            return ToolResult(
                action=ToolAction.BASH,
                output=stdout,
                success=success,
                stderr=stderr if not success else "",
            )
        except OSError as exc:
            return ToolResult(
                action=ToolAction.BASH,
                output="",
                success=False,
                stderr=f"Failed to execute command: {exc}",
            )
