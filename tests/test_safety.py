from pathlib import Path

from corge.tools.runtime import ToolRuntime


def test_safe_commands_are_allowed(tmp_path: Path) -> None:
    runtime = ToolRuntime(repo_root=tmp_path)
    # Simple echo command
    res = runtime.bash("echo 'hello'")
    assert res.success is True
    assert res.output.strip() == "hello"
    assert res.stderr == ""


def test_blocked_administrative_binaries(tmp_path: Path) -> None:
    runtime = ToolRuntime(repo_root=tmp_path)
    
    # test sudo
    res = runtime.bash("sudo apt-get update")
    assert res.success is False
    assert "blocked administrative binary" in res.stderr
    
    # test chmod
    res = runtime.bash("chmod +x run.sh")
    assert res.success is False
    assert "blocked administrative binary" in res.stderr


def test_blocked_escaped_deletions(tmp_path: Path) -> None:
    runtime = ToolRuntime(repo_root=tmp_path)
    
    # Attempting to delete path escaping the temp path
    res = runtime.bash("rm -rf ../outside")
    assert res.success is False
    assert "attempts to delete path escaping project root" in res.stderr


def test_blocked_absolute_deletions(tmp_path: Path) -> None:
    runtime = ToolRuntime(repo_root=tmp_path)
    
    # Attempting to delete absolute path outside root
    res = runtime.bash("rm -rf /usr/bin")
    assert res.success is False
    assert "attempts to delete absolute path outside project root" in res.stderr


def test_blocked_redirections(tmp_path: Path) -> None:
    runtime = ToolRuntime(repo_root=tmp_path)
    
    res = runtime.bash("echo 'malicious' > /etc/passwd")
    assert res.success is False
    assert "Redirection to absolute or home paths outside the workspace is blocked" in res.stderr
