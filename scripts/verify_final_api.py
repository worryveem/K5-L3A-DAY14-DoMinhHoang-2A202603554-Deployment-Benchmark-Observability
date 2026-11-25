"""Check the Compose agent including invalid input and concurrent rate limiting."""
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
import json
from pathlib import Path
import time

root = Path(__file__).resolve().parents[1]
env = dict(line.split('=', 1) for line in (root / '06-lab-complete/.env').read_text().splitlines() if '=' in line)
key = env['AGENT_API_KEY']

def call(method, path, body=None, authenticated=False):
    headers = {'Content-Type': 'application/json'}
    if authenticated:
        headers['X-API-Key'] = key
    conn = HTTPConnection('localhost', 8000, timeout=10)
    try:
        conn.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
        response = conn.getresponse()
        return {'method': method, 'path': path, 'status': response.status,
                'body': json.loads(response.read()), 'retry_after': response.getheader('Retry-After')}
    finally:
        conn.close()

for _ in range(100):
    try:
        if call('GET', '/ready')['status'] == 200:
            break
    except OSError:
        pass
    time.sleep(0.2)
else:
    raise SystemExit('Compose agent not ready')

checks = [call('GET', '/health'), call('GET', '/ready'), call('POST', '/ask', {'question': 'Hello'}),
          call('POST', '/ask', {'question': ''}, True), call('POST', '/ask', {'question': '   '}, True),
          call('POST', '/ask', {'question': 123}, True)]
with ThreadPoolExecutor(max_workers=20) as pool:
    burst = list(pool.map(lambda _: call('POST', '/ask', {'question': 'Docker'}, True), range(20)))
codes = [result['status'] for result in burst]
assert [result['status'] for result in checks] == [200, 200, 401, 422, 422, 422]
assert codes.count(200) == 10 and codes.count(429) == 10, codes
(root / 'evidence/part6/api-validation.json').write_text(json.dumps({'checks': checks, 'concurrent_burst': burst}, ensure_ascii=False, indent=2), encoding='utf-8')
print('Health/readiness/auth/invalid input verified; 20 concurrent requests: 10 accepted, 10 rate limited.')
