"""Unit tests for sandbox.executor — execute_command and stream_command."""
from sandbox.executor import ExecutionResult, execute_command, stream_command


async def test_execute_command_echo(workspace):
    result = await execute_command("echo hello", cwd=str(workspace))
    assert result.exit_code == 0
    assert "hello" in result.stdout


async def test_execute_command_exit_code(workspace):
    result = await execute_command("exit 42", cwd=str(workspace))
    assert result.exit_code == 42


async def test_execute_command_stderr(workspace):
    result = await execute_command("echo err >&2", cwd=str(workspace))
    assert result.exit_code == 0
    assert "err" in result.stderr


async def test_execute_command_timeout(workspace):
    result = await execute_command("sleep 60", cwd=str(workspace), timeout=1)
    assert result.exit_code == -1
    assert "timed out" in result.stderr.lower()


async def test_execute_command_invalid_cwd():
    result = await execute_command("echo hello", cwd="/nonexistent_dir_xyz")
    assert result.exit_code == -1
    assert result.stderr  # should contain error message


async def test_execution_result_dataclass():
    r = ExecutionResult(exit_code=0, stdout="out", stderr="err")
    assert r.exit_code == 0
    assert r.stdout == "out"
    assert r.stderr == "err"


async def test_stream_command_echo(workspace):
    events = []
    async for event in stream_command("echo streamed", cwd=str(workspace)):
        events.append(event)
    # Should have at least a stdout event and an exit event
    stdout_events = [e for e in events if e.startswith("event: stdout")]
    exit_events = [e for e in events if e.startswith("event: exit")]
    assert len(stdout_events) >= 1
    assert "streamed" in stdout_events[0]
    assert len(exit_events) == 1
    assert "data: 0" in exit_events[0]


async def test_stream_command_stderr(workspace):
    events = []
    async for event in stream_command("echo err >&2", cwd=str(workspace)):
        events.append(event)
    stderr_events = [e for e in events if e.startswith("event: stderr")]
    assert len(stderr_events) >= 1
    assert "err" in stderr_events[0]
