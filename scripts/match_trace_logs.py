"""Link selected Jaeger trace IDs to actual JSON logs before recreation."""
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
traces = json.loads((root / 'evidence/part7/selected-traces.json').read_text(encoding='utf-8'))
names = subprocess.check_output(['docker', 'ps', '--filter', 'label=com.docker.compose.project=k5-day14-observability',
                                 '--filter', 'label=com.docker.compose.service=agent', '--format', '{{.Names}}'], text=True).splitlines()
records = []
for name in names:
    result = subprocess.run(['docker', 'logs', name], capture_output=True, text=True)
    for line in (result.stdout + result.stderr).splitlines():
        try:
            record = json.loads(line)
            if isinstance(record, dict) and record.get('trace_id'):
                records.append(record)
        except json.JSONDecodeError:
            pass
matched = {}
for kind, trace in traces.items():
    matched[kind] = [record for record in records if record['trace_id'] == trace['traceID']]
    if not matched[kind]:
        raise SystemExit('No matching actual log for ' + kind)
(root / 'evidence/part7/trace-logs.json').write_text(json.dumps(matched, ensure_ascii=False, indent=2), encoding='utf-8')
print('Matched both trace IDs to actual JSON application logs.')
