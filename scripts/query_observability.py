"""Save Prometheus readings used by the report (not estimates)."""
import json
from pathlib import Path
import urllib.parse
import urllib.request

root = Path(__file__).resolve().parents[1]
queries = {
    'p95_seconds': 'histogram_quantile(0.95,sum by(le)(rate(http_request_duration_seconds_bucket{job="agent",route="/ask"}[1m])))',
    'avg_seconds': 'sum(rate(http_request_duration_seconds_sum{job="agent",route="/ask"}[1m])) / sum(rate(http_request_duration_seconds_count{job="agent",route="/ask"}[1m]))',
    'requests_per_instance': 'sum by(instance)(rate(http_requests_total{job="agent",route="/ask"}[1m]))',
    'tokens_per_type': 'sum by(type)(rate(llm_tokens_total{job="agent"}[1m]))',
    'error_rate': 'sum(rate(http_requests_total{job="agent",route="/ask",status=~"5.."}[1m])) / sum(rate(http_requests_total{job="agent",route="/ask"}[1m]))',
}
results = {}
for name, query in queries.items():
    url = 'http://localhost:9090/api/v1/query?' + urllib.parse.urlencode({'query': query})
    results[name] = {'query': query, 'response': json.load(urllib.request.urlopen(url))}
(root / 'evidence/part7/prometheus-baseline.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
print(json.dumps(results, indent=2))
