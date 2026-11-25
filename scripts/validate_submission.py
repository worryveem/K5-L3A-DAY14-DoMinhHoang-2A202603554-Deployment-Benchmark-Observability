"""Check evidence consistency without replacing the original grading script."""
import csv
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
required = ['MISSION_ANSWERS.md', 'DEPLOYMENT.md', 'BENCHMARK_REPORT.md',
            'screenshots/grafana-dashboard.png', 'screenshots/jaeger-slow-trace.png',
            'screenshots/jaeger-error-trace.png', 'screenshots/prometheus-alert-firing.png']
for path in required:
    assert (root / path).is_file(), path
for protected in ['06-lab-complete/check_production_ready.py',
                  '06-lab-complete/benchmark-observability/develop/eval/golden_dataset.jsonl']:
    original = subprocess.check_output(['git', 'show', 'HEAD:' + protected], cwd=root)
    # Windows checkout may normalize newlines, so compare normalized text.
    assert original.decode().replace('\r\n', '\n') == (root / protected).read_text(encoding='utf-8'), protected

for path in (root / 'reports').glob('*.json'):
    source = root / '06-lab-complete/benchmark-observability/develop/reports' / path.name
    assert json.loads(path.read_text(encoding='utf-8')) == json.loads(source.read_text(encoding='utf-8')), path.name
fixed = json.loads((root / 'reports/eval_v2_fixed.json').read_text(encoding='utf-8'))
assert fixed['passed'] == fixed['total'] == 23
assert fixed['quality_gate']['passed'] and fixed['quality_gate']['regressions'] == []
for count in [1, 3]:
    name = f'scale_{count}_stats.csv'
    target = root / 'benchmark-results' / name
    source = root / '06-lab-complete/benchmark-observability/production/benchmark-results' / name
    assert target.read_bytes() == source.read_bytes(), name
    with target.open(encoding='utf-8-sig') as stream:
        aggregate = next(row for row in csv.DictReader(stream) if row['Name'] == 'Aggregated')
        assert int(aggregate['Request Count']) > 0
selected = json.loads((root / 'evidence/part7/selected-traces.json').read_text(encoding='utf-8'))
logs = json.loads((root / 'evidence/part7/trace-logs.json').read_text(encoding='utf-8'))
for kind in ['slow', 'error']:
    assert any(log['trace_id'] == selected[kind]['traceID'] for log in logs[kind])
readiness = (root / 'evidence/part6/readiness.txt').read_text(encoding='utf-8')
assert 'PASS 12/12' in readiness and '43/43 checks passed' in readiness
print('Local submission evidence is consistent. Cloud completion must be verified separately in DEPLOYMENT.md.')
