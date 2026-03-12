"""E2E tests for the sandbox service and its integration with controller/API."""
import os
import time
import zipfile
import io

import httpx

API_URL = os.environ.get("API_URL", "http://localhost:8100")
SANDBOX_URL = os.environ.get("SANDBOX_URL", "http://localhost:8105")


# ---- Sandbox direct health ----

def test_sandbox_health(http: httpx.Client):
    r = http.get(f"{SANDBOX_URL}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ---- Controller registration (via API proxy) ----

def test_sandbox_registered_with_controller(http: httpx.Client):
    """Sandbox should auto-register with controller; GET /sandboxes returns it."""
    # Give registration a moment to complete (should already be done by health wait)
    for _ in range(10):
        r = http.get(f"{API_URL}/sandboxes")
        assert r.status_code == 200
        sandboxes = r.json()
        if len(sandboxes) > 0:
            break
        time.sleep(1)
    else:
        raise AssertionError("No sandboxes registered after 10s")

    sb = sandboxes[0]
    assert "sandbox_id" in sb
    assert "sandbox_url" in sb
    assert sb["status"] in ("free", "allocated")
    assert isinstance(sb["labels"], list)
    assert "python" in sb["labels"]
    assert "git" in sb["labels"]


# ---- File operations ----

def test_write_and_read_file(http: httpx.Client):
    # Write a file
    r = http.put(
        f"{SANDBOX_URL}/files/test_hello.py",
        json={"content": "print('hello world')\n"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["path"] == "test_hello.py"

    # Read it back
    r = http.get(f"{SANDBOX_URL}/files/test_hello.py")
    assert r.status_code == 200
    body = r.json()
    assert body["content"] == "print('hello world')\n"
    assert body["size"] > 0


def test_list_files(http: httpx.Client):
    # Ensure at least one file exists
    http.put(f"{SANDBOX_URL}/files/list_test.txt", json={"content": "data"})

    r = http.get(f"{SANDBOX_URL}/files")
    assert r.status_code == 200
    body = r.json()
    assert "entries" in body
    names = [e["name"] for e in body["entries"]]
    assert "list_test.txt" in names


def test_delete_file(http: httpx.Client):
    # Create then delete
    http.put(f"{SANDBOX_URL}/files/to_delete.txt", json={"content": "temp"})
    r = http.delete(f"{SANDBOX_URL}/files/to_delete.txt")
    assert r.status_code == 200
    assert r.json()["deleted"] == "to_delete.txt"

    # Confirm gone
    r = http.get(f"{SANDBOX_URL}/files/to_delete.txt")
    assert r.status_code == 404


def test_mkdir(http: httpx.Client):
    r = http.post(f"{SANDBOX_URL}/mkdir/test_subdir/nested")
    assert r.status_code == 200
    assert r.json()["created"] == "test_subdir/nested"

    # Write a file inside and list
    http.put(f"{SANDBOX_URL}/files/test_subdir/nested/file.txt", json={"content": "nested"})
    r = http.get(f"{SANDBOX_URL}/files/test_subdir/nested/file.txt")
    assert r.status_code == 200
    assert r.json()["content"] == "nested"


# ---- Path traversal protection ----

def test_path_traversal_blocked(http: httpx.Client):
    # URL-encode the traversal to bypass client-side normalization
    r = http.get(f"{SANDBOX_URL}/files/..%2F..%2Fetc%2Fpasswd")
    assert r.status_code in (403, 400, 404)  # blocked one way or another


# ---- Command execution ----

def test_execute_command(http: httpx.Client):
    r = http.post(
        f"{SANDBOX_URL}/execute",
        json={"command": "echo hello"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["exit_code"] == 0
    assert "hello" in body["stdout"]


def test_execute_python(http: httpx.Client):
    r = http.post(
        f"{SANDBOX_URL}/execute",
        json={"command": "python3 -c \"print(2+2)\""},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["exit_code"] == 0
    assert "4" in body["stdout"]


def test_execute_failing_command(http: httpx.Client):
    r = http.post(
        f"{SANDBOX_URL}/execute",
        json={"command": "exit 42"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["exit_code"] == 42


# ---- Streaming execution ----

def test_execute_stream(http: httpx.Client):
    """POST /execute/stream returns SSE events with stdout lines."""
    r = http.post(
        f"{SANDBOX_URL}/execute/stream",
        json={"command": "echo line1 && echo line2"},
        headers={"Accept": "text/event-stream"},
    )
    assert r.status_code == 200
    text = r.text
    # SSE format: "data: ..." lines
    assert "line1" in text
    assert "line2" in text


# ---- Download workspace as zip ----

def test_download_workspace(http: httpx.Client):
    # Ensure a file exists
    http.put(f"{SANDBOX_URL}/files/download_test.txt", json={"content": "zip me"})

    r = http.get(f"{SANDBOX_URL}/download")
    assert r.status_code == 200
    assert "application/zip" in r.headers.get("content-type", "")

    # Verify it's a valid zip containing our file
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = zf.namelist()
    assert "download_test.txt" in names
    assert zf.read("download_test.txt").decode() == "zip me"


# ---- Write + Execute integration ----

def test_write_and_execute_script(http: httpx.Client):
    """Write a Python script, then execute it."""
    script = "import sys\nprint('args:', sys.argv[1:])\nsys.exit(0)\n"
    http.put(f"{SANDBOX_URL}/files/runner.py", json={"content": script})

    r = http.post(
        f"{SANDBOX_URL}/execute",
        json={"command": "python3 runner.py foo bar"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["exit_code"] == 0
    assert "foo" in body["stdout"]
    assert "bar" in body["stdout"]
