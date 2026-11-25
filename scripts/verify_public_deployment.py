"""Record real public API checks without writing credentials to evidence.

Usage: AGENT_API_KEY=<secret> python scripts/verify_public_deployment.py --url <URL>
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def request(base, method, path, body=None, key=None):
    headers = {}
    if body is not None:
        headers['Content-Type'] = 'application/json'
    if key:
        headers['X-API-Key'] = key
    req = urllib.request.Request(
        base + path, method=method, headers=headers,
        data=json.dumps(body).encode() if body is not None else None,
    )
    try:
        response = urllib.request.urlopen(req, timeout=20)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        text = response.read().decode('utf-8', errors='replace')
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = text
        return {'method': method, 'path': path, 'status': response.code,
                'authenticated': bool(key), 'body': payload}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True)
    parser.add_argument('--wait-seconds', type=int, default=300)
    args = parser.parse_args()
    base = args.url.rstrip('/')
    key = os.environ.get('AGENT_API_KEY')
    if not key:
        raise SystemExit('Set AGENT_API_KEY in the process environment first')
    deadline = time.monotonic() + args.wait_seconds
    while True:
        try:
            if request(base, 'GET', '/ready')['status'] == 200:
                break
        except (OSError, urllib.error.URLError):
            pass
        if time.monotonic() >= deadline:
            raise SystemExit('Public service did not become ready in time')
        time.sleep(3)
    checks = [
        request(base, 'GET', '/health'),
        request(base, 'GET', '/ready'),
        request(base, 'POST', '/ask', {'question': 'Hello'}),
        request(base, 'POST', '/ask', {'question': 'What is deployment?'}, key),
    ]
    expected = [200, 200, 401, 200]
    actual = [check['status'] for check in checks]
    report = {
        'executed_at': datetime.now(timezone(timedelta(hours=7))).isoformat(),
        'public_url': base, 'expected_statuses': expected,
        'checks': checks, 'passed': actual == expected,
    }
    target = ROOT / 'evidence/part6/public-api.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for check in checks:
        print(f"{check['method']} {check['path']} authenticated={check['authenticated']} -> {check['status']}")
    if actual != expected:
        raise SystemExit(f'Public checks failed: {actual}')
    print('Public deployment passed all four required checks.')


if __name__ == '__main__':
    main()
