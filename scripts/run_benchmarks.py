"""Run CP7 with real HTTP calls. Execute from the repository root on Linux.

Run --phase baseline before editing KNOWLEDGE_BASE, then --phase measurements.
Every command, exit code and fault-injection setting is recorded as evidence.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "06-lab-complete/benchmark-observability/develop"
EVIDENCE = ROOT / "evidence/part7"
EVIDENCE.mkdir(parents=True, exist_ok=True)


def run_agent(version, port, **overrides):
    env = dict(os.environ, AGENT_VERSION=version, PORT=str(port), **overrides)
    log = (EVIDENCE / f"agent_{version}_{port}.log").open("a", encoding="utf-8")
    proc = subprocess.Popen([sys.executable, "app.py"], cwd=APP, env=env,
                            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    for _ in range(200):
        if proc.poll() is not None:
            raise RuntimeError(f"Agent exited: {proc.returncode}")
        try:
            urllib.request.urlopen(f"http://localhost:{port}/health", timeout=1)
            return proc, log
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("Agent startup timed out")


def stop(agent):
    proc, log = agent
    if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=15)
    log.close()


def command(args, name):
    result = subprocess.run([sys.executable, *args], cwd=APP, capture_output=True, text=True)
    (EVIDENCE / (name + ".txt")).write_text(result.stdout + result.stderr, encoding="utf-8")
    print(name, "exit", result.returncode, flush=True)
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr)
    return {"command": ["python", *args], "exit_code": result.returncode}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["baseline", "measurements"], required=True)
    args = parser.parse_args()
    manifest = {"phase": args.phase, "runs": []}
    if args.phase == "baseline":
        for version, port in [("v1", 8001), ("v2", 8002)]:
            agent = run_agent(version, port, MOCK_ERROR_RATE="0", MOCK_SLOW_RATE="0")
            try:
                cmd = ["eval/run_eval.py", "--url", f"http://localhost:{port}", "--out", f"reports/eval_{version}.json"]
                if version == "v2":
                    cmd += ["--baseline", "reports/eval_v1.json"]
                manifest["runs"].append(command(cmd, "eval_" + version))
            finally:
                stop(agent)
        manifest["eval_environment"] = {"MOCK_ERROR_RATE": "0", "MOCK_SLOW_RATE": "0"}
    else:
        agent = run_agent("v2", 8002, MOCK_ERROR_RATE="0", MOCK_SLOW_RATE="0")
        try:
            manifest["runs"].append(command([
                "eval/run_eval.py", "--url", "http://localhost:8002", "--min-accuracy", "1.0",
                "--baseline", "reports/eval_v2.json", "--out", "reports/eval_v2_fixed.json",
            ], "eval_v2_fixed"))
            metrics = urllib.request.urlopen("http://localhost:8002/metrics").read().decode()
            (EVIDENCE / "metrics.txt").write_text(metrics, encoding="utf-8")
        finally:
            stop(agent)
        agent = run_agent("v2", 8002, MOCK_ERROR_RATE="0.01", MOCK_SLOW_RATE="0.03")
        try:
            for concurrency in [1, 10, 50, 100]:
                manifest["runs"].append(command([
                    "load_test.py", "--url", "http://localhost:8002", "--requests", "300",
                    "--concurrency", str(concurrency), "--out", f"reports/load_v2_c{concurrency}.json",
                ], f"load_v2_c{concurrency}"))
        finally:
            stop(agent)
        for slow in ["0", "0.03", "0.1"]:
            agent = run_agent("v2", 8002, MOCK_ERROR_RATE="0.01", MOCK_SLOW_RATE=slow)
            try:
                manifest["runs"].append(command([
                    "load_test.py", "--url", "http://localhost:8002", "--requests", "300",
                    "--concurrency", "20", "--out", f"reports/load_v2_slow_{slow}.json",
                ], f"load_v2_slow_{slow}"))
            finally:
                stop(agent)
        manifest["load_environment"] = {"MOCK_ERROR_RATE": "0.01", "MOCK_SLOW_RATE": "0.03 unless overridden"}
        manifest["eval_environment"] = {"MOCK_ERROR_RATE": "0", "MOCK_SLOW_RATE": "0"}
    (EVIDENCE / (args.phase + "_manifest.json")).write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
