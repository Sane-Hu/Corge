"""Coding agent — executes procedural steps."""

class ToolExecutionError(Exception):
    """Raised when a tool fails to execute or returns a non-zero exit code."""

class CodingAgent:
    """Runs the execution cycle using tool context bundles."""
    
    def __init__(self) -> None:
        raise NotImplementedError
