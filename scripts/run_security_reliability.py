"""Collect CP3/CP4 evidence from the supplied examples (Linux Python)."""
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import time
import psutil

ROOT = Path(__file__).resolve().parents[1]

# Reclaim only listeners started by this evidence script after an interrupted run.
for process in psutil.process_iter(["pid", "cmdline"]):
    args = process.info["cmdline"] or []
    if process.status() != psutil.STATUS_ZOMBIE and "uvicorn" in args and any(port in args for port in ("8014", "8015")):
        process.terminate()
        try:
            process.wait(timeout=3)
        except psutil.TimeoutExpired:
            if process.is_running() and process.status() != psutil.STATUS_ZOMBIE:
                process.kill()


def http(port, method, path, body=None, headers=None):
    headers = dict(headers or {})
    if body is not None:
        body = json.dumps(body)
        headers["Content-Type"] = "application/json"
    conn = HTTPConnection("localhost", port, timeout=15)
    try:
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        text = response.read().decode()
        return {"status": response.status, "headers": dict(response.getheaders()), "body": json.loads(text)}
    finally:
        conn.close()


def start(path, port, **env):
    log = (ROOT / "evidence" / (path.split("/")[0] + ".log")).open("a")
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", str(port)],
                            cwd=ROOT / path, env=dict(os.environ, **env), stdout=log,
                            stderr=subprocess.STDOUT, start_new_session=True)
    for _ in range(100):
        if proc.poll() is not None:
            raise RuntimeError("Example failed to start")
        try:
            # Any HTTP response confirms the listener is available.
            http(port, "GET", "/health")
            return proc, log
        except OSError:
            if proc.poll() is not None:
                raise RuntimeError("Example failed to start")
            time.sleep(0.1)
    raise RuntimeError("Example startup timeout")


def stop(proc, log):
    if proc.poll() is None:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
    log.close()


def curl_capture(headers=None):
    args = ['curl', '-sS', '-i', '-X', 'POST', 'http://localhost:8014/ask',
            '-H', 'Content-Type: application/json', '-d', '{"question":"Docker"}']
    for name, value in (headers or {}).items():
        args += ['-H', name + ': ' + value]
    return subprocess.check_output(args, text=True)


key = secrets.token_urlsafe(24)
proc, log = start("04-api-gateway/develop", 8014, AGENT_API_KEY=key)
try:
    basic = {
        "missing_key": http(8014, "POST", "/ask", {"question": "Hello"}),
        "valid_key": http(8014, "POST", "/ask", {"question": "What is Docker?"}, {"X-API-Key": key}),
    }
    curl_output = ["Missing API key:\n" + curl_capture(),
                   "Valid API key (request header redacted):\n" + curl_capture({"X-API-Key": key})]
finally:
    stop(proc, log)
assert basic["missing_key"]["status"] == 401 and basic["valid_key"]["status"] == 200

proc, log = start("04-api-gateway/production", 8014, JWT_SECRET=secrets.token_urlsafe(40))
try:
    login = http(8014, "POST", "/auth/token", {"username": "student", "password": "demo123"})
    assert login["status"] == 200, login
    token = login["body"]["access_token"]
    full = {"missing_token": http(8014, "POST", "/ask", {"question": "Hello"})}
    full["login"] = {"status": login["status"], "body": {"access_token": "[REDACTED]", "token_type": "bearer"}}
    full["burst"] = [http(8014, "POST", "/ask", {"question": "Docker"}, {"Authorization": "Bearer " + token}) for _ in range(12)]
    curl_output.append("JWT rate limit (request token redacted):\n" + curl_capture({"Authorization": "Bearer " + token}))
finally:
    stop(proc, log)
(ROOT / "evidence/part4/runtime.json").write_text(json.dumps({"basic": basic, "jwt": full}, ensure_ascii=False, indent=2), encoding="utf-8")
(ROOT / "evidence/part4/curl-http.txt").write_text("\n\n".join(curl_output), encoding="utf-8")

proc, log = start("05-scaling-reliability/develop", 8015)
try:
    result = {"health": http(8015, "GET", "/health"), "ready": http(8015, "GET", "/ready")}
    with ThreadPoolExecutor() as pool:
        future = pool.submit(http, 8015, "POST", "/ask?question=Hello")
        time.sleep(0.05)
        proc.send_signal(signal.SIGTERM)
        result["in_flight"] = future.result()
        proc.wait(timeout=15)
        result["sigterm_exit_code"] = proc.returncode
finally:
    stop(proc, log)
(ROOT / "evidence/part5/health_shutdown.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print("Saved Part 4 authentication/rate-limit and Part 5 shutdown evidence.")
