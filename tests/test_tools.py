from pathlib import Path

from corge.tools.runtime import ToolRuntime


def test_tool_runtime():
    rt = ToolRuntime()
    res = rt.bash("echo Hello")
    assert res.success
    assert "Hello" in res.output

    # Test timeout
    res_timeout = rt.bash("sleep 0.1")
    assert res_timeout.success
