"""Record actual Prometheus alert state transitions during chaos experiments."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('--started', type=float, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
history = []
first_firing = {}
for _ in range(50):
    payload = json.load(urllib.request.urlopen('http://localhost:9090/api/v1/alerts', timeout=10))
    elapsed = round(time.time() - args.started, 1)
    history.append({'elapsed_s': elapsed, 'response': payload})
    for alert in payload['data']['alerts']:
        if alert['state'] == 'firing':
            first_firing.setdefault(alert['labels']['alertname'], elapsed)
    report = {'started_at': datetime.fromtimestamp(args.started, timezone.utc).isoformat(),
              'experiments': ['A: MOCK_ERROR_RATE=0.2', 'D: pause one of two instances'],
              'first_firing_s': first_firing, 'history': history}
    (root / 'evidence/part7/alert-experiments.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('elapsed', elapsed, 'firing', first_firing, flush=True)
    firing_now = {a['labels']['alertname'] for a in payload['data']['alerts'] if a['state'] == 'firing'}
    if {'AgentHighErrorRate', 'AgentInstanceDown'} <= firing_now:
        print('Both required alerts are firing simultaneously.', flush=True)
        break
    time.sleep(5)
else:
    raise SystemExit('Alerts did not both reach firing within the observation window')
