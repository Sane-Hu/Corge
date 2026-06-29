"""Stateless execution primitives — satisfies ``contracts.ToolRuntimePort``."""

from pathlib import Path

from corge.contracts import ToolAction, ToolResult


class ToolRuntime:
    """Concrete tool runtime.  Satisfies ``contracts.ToolRuntimePort``."""

    def __init__(self, repo_root: Path | str | None = None) -> None:
        self.repo_root = Path(repo_root).resolve() if repo_root else Path.cwd().resolve()
        self.modified_files: dict[Path, str | None] = {}

    def reset_modified_files(self) -> None:
        self.modified_files.clear()

    def _resolve_path(self, path: Path | str) -> Path:
        target = (self.repo_root / path).resolve()
        if not target.is_relative_to(self.repo_root):
            raise ValueError(f"Path escapes repository root: {path}")
        return target

    def read(self, path: Path | str) -> ToolResult:
        try:
            target = self._resolve_path(path)
            content = target.read_text(encoding="utf-8")
            return ToolResult(action=ToolAction.READ, output=content, success=True)
        except ValueError as exc:
            return ToolResult(
                action=ToolAction.READ,
                output="",
                success=False,
                stderr=str(exc),
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

    def write(self, path: Path | str, content: str) -> ToolResult:
        try:
            target = self._resolve_path(path)
            if target not in self.modified_files:
                if target.exists():
                    self.modified_files[target] = target.read_text(encoding="utf-8")
                else:
                    self.modified_files[target] = None
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
        except ValueError as exc:
            return ToolResult(
                action=ToolAction.WRITE,
                output="",
                success=False,
                stderr=str(exc),
            )

    def edit(self, path: Path | str, old: str, new: str) -> ToolResult:
        try:
            target = self._resolve_path(path)
            original = target.read_text(encoding="utf-8")
            if target not in self.modified_files:
                self.modified_files[target] = original
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
        except ValueError as exc:
            return ToolResult(
                action=ToolAction.EDIT,
                output="",
                success=False,
                stderr=str(exc),
            )

        occurrences = original.count(old)
        if occurrences == 0:
            return ToolResult(
                action=ToolAction.EDIT,
                output="",
                success=False,
                stderr=(
                    f"String not found in {path}. "
                    "Make sure to include exact whitespace."
                ),
            )
        if occurrences > 1:
            return ToolResult(
                action=ToolAction.EDIT,
                output="",
                success=False,
                stderr=(
                    f"Ambiguous edit: old string appears {occurrences} "
                    f"times in {path}. "
                    "Include more surrounding context in 'old' "
                    "to uniquely identify the target."
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

    def _is_safe_command(self, command: str, cwd: Path) -> tuple[bool, str]:
        import shlex
        try:
            parts = shlex.split(command)
        except ValueError as exc:
            return False, f"Invalid shell syntax: {exc}"

        blocked_executables = {"sudo", "su", "chown", "chmod"}
        for part in parts:
            if part in blocked_executables:
                return False, f"Command contains blocked administrative binary: {part}"

        resolved_cwd = Path(cwd).resolve()
        for i, part in enumerate(parts):
            if part == "rm" or (part.startswith("-") and "r" in part and i > 0 and parts[i-1] == "rm"):
                # Check targets of rm
                for target_part in parts[i+1:]:
                    if target_part.startswith("-"):
                        continue
                    try:
                        target_path = Path(target_part)
                        if target_path.is_absolute():
                            if not target_path.resolve().is_relative_to(resolved_cwd):
                                return False, f"Command attempts to delete absolute path outside project root: {target_part}"
                        else:
                            full_path = (resolved_cwd / target_path).resolve()
                            if not full_path.is_relative_to(resolved_cwd):
                                return False, f"Command attempts to delete path escaping project root: {target_part}"
                    except Exception:
                        if ".." in target_part or target_part.startswith("/"):
                            return False, f"Command attempts to delete path outside project root: {target_part}"
                    break

        if " > /" in command or " >> /" in command or " > ~" in command or " >> ~" in command:
            return False, "Redirection to absolute or home paths outside the workspace is blocked."

        return True, ""

    def bash(self, command: str) -> ToolResult:
        # Validate command safety
        cwd = self.repo_root
        is_safe, error_msg = self._is_safe_command(command, cwd)
        if not is_safe:
            return ToolResult(
                action=ToolAction.BASH,
                output="",
                success=False,
                stderr=f"Command validation failed: {error_msg}",
            )

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
