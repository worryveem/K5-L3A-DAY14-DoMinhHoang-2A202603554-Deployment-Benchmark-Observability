"""Collect real HTTP responses and Docker sizes for Part 2."""
from http.client import HTTPConnection
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]

def request(port, method, path, body=None):
    headers = {}
    if body is not None:
        body = json.dumps(body)
        headers['Content-Type'] = 'application/json'
    conn = HTTPConnection('localhost', port, timeout=15)
    try:
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        return {'port': port, 'method': method, 'path': path, 'status': response.status,
                'body': json.loads(response.read().decode())}
    finally:
        conn.close()

results = []
for port, method, path, body in [
    (8012, 'POST', '/ask?question=Hello', None),
    (8013, 'GET', '/health', None),
    (8013, 'POST', '/ask', {'question': 'What is Docker?'}),
    (80, 'GET', '/health', None),
    (80, 'POST', '/ask', {'question': 'What is Docker?'}),
]:
    for attempt in range(60):
        try:
            result = request(port, method, path, body)
            if result['status'] == 200:
                break
        except OSError:
            pass
        time.sleep(1)
    else:
        raise RuntimeError(f'Part 2 HTTP failed on port {port}')
    results.append(result)
images = json.loads(subprocess.check_output(['docker', 'image', 'inspect', 'my-agent:develop', 'my-agent:advanced']))
sizes = {image['RepoTags'][0]: {'bytes': image['Size'], 'MiB': round(image['Size'] / 1024**2, 2)} for image in images}
reduction = (1 - images[1]['Size'] / images[0]['Size']) * 100
report = {'requests': results, 'image_sizes': sizes, 'size_reduction_percent': round(reduction, 2)}
(ROOT / 'evidence/part2/runtime.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
