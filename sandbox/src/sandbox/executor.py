"""Command execution and streaming for the sandbox."""
import asyncio
import logging
from collections.abc import AsyncGenerator
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str


async def execute_command(
    command: str, cwd: str, timeout: int = 300
) -> ExecutionResult:
    """Run a command and return the result after completion."""
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        return ExecutionResult(
            exit_code=proc.returncode or 0,
            stdout=stdout_bytes.decode(errors="replace"),
            stderr=stderr_bytes.decode(errors="replace"),
        )
    except TimeoutError:
        proc.kill()
        await proc.wait()
        return ExecutionResult(
            exit_code=-1,
            stdout="",
            stderr=f"Command timed out after {timeout} seconds",
        )
    except Exception as exc:
        return ExecutionResult(
            exit_code=-1,
            stdout="",
            stderr=str(exc),
        )


async def stream_command(
    command: str, cwd: str, timeout: int = 300
) -> AsyncGenerator[str, None]:
    """Run a command and yield SSE events for stdout/stderr lines."""
    proc = None
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        async def _read_lines(stream, stream_type: str):
            """Read lines from a stream and return them as SSE events."""
            events = []
            while True:
                line = await stream.readline()
                if not line:
                    break
                text = line.decode(errors="replace").rstrip("\n")
                events.append(f"event: {stream_type}\ndata: {text}\n\n")
            return events

        try:
            stdout_task = asyncio.create_task(_read_lines(proc.stdout, "stdout"))
            stderr_task = asyncio.create_task(_read_lines(proc.stderr, "stderr"))

            done, _ = await asyncio.wait(
                {stdout_task, stderr_task},
                timeout=timeout,
            )

            if stdout_task in done:
                for event in stdout_task.result():
                    yield event
            else:
                stdout_task.cancel()

            if stderr_task in done:
                for event in stderr_task.result():
                    yield event
            else:
                stderr_task.cancel()

            if len(done) < 2:
                proc.kill()
                yield f"event: error\ndata: Command timed out after {timeout} seconds\n\n"

        except Exception as exc:
            yield f"event: error\ndata: {exc}\n\n"

        await proc.wait()
        yield f"event: exit\ndata: {proc.returncode}\n\n"

    except Exception as exc:
        yield f"event: error\ndata: {exc}\n\n"
