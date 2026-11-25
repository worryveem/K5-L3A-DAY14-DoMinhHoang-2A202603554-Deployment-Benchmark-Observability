"""Execute the actual workflow shell step in the Linux lab environment."""
import os
from pathlib import Path
import shutil
import subprocess
import yaml

root = Path(__file__).resolve().parents[1]
workflow = yaml.safe_load((root / '.github/workflows/eval.yml').read_text(encoding='utf-8'))
step = next(step for step in workflow['jobs']['eval']['steps']
            if step.get('name', '').startswith('Evaluate'))
result = subprocess.run(['bash', '-e', '-c', step['run']],
                        cwd=root / '06-lab-complete/benchmark-observability/develop',
                        env={**os.environ, **step['env']}, text=True, capture_output=True)
(root / 'evidence/part7/ci-local.txt').write_text(result.stdout + result.stderr, encoding='utf-8')
if result.returncode == 0:
    shutil.copyfile(root / '06-lab-complete/benchmark-observability/develop/reports/ci_eval.json',
                    root / 'reports/ci_eval.json')
print('Actual workflow shell step exit:', result.returncode)
print(result.stdout[-1800:])
raise SystemExit(result.returncode)
