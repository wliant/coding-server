import httpx
import os

API_URL     = os.environ.get("API_URL",     "http://localhost:8100")
WORKER_URL  = os.environ.get("WORKER_URL",  "http://localhost:8101")
TOOLS_URL   = os.environ.get("TOOLS_URL",   "http://localhost:8102")
SANDBOX_URL = os.environ.get("SANDBOX_URL", "http://localhost:8105")
BASE_URL    = os.environ.get("BASE_URL",    "http://localhost:3100")


def test_api_health(http: httpx.Client):
    r = http.get(f"{API_URL}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_worker_health(http: httpx.Client):
    r = http.get(f"{WORKER_URL}/health")
    assert r.status_code == 200


def test_tools_health(http: httpx.Client):
    r = http.get(f"{TOOLS_URL}/health")
    assert r.status_code == 200


def test_sandbox_health(http: httpx.Client):
    r = http.get(f"{SANDBOX_URL}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_web_health(http: httpx.Client):
    r = http.get(f"{BASE_URL}/api/health")
    assert r.status_code == 200
