"""Test a base wheel in an isolated environment outside the source checkout."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from datetime import datetime, timezone

out = Path('/tmp/loop-learning-20260904.nM5vjD')
python = out/'wheel-env/bin/python'
wheel = out/'dist-delivery/loop_engine-0.1.0-py3-none-any.whl'
env = os.environ.copy()
env.pop('PYTHONPATH', None)
env['PYTHONDONTWRITEBYTECODE'] = '1'
started = datetime.now(timezone.utc).isoformat()
start = time.monotonic()
identity = subprocess.check_output([str(python), '-c',
    'import loop_engine,sys; print(loop_engine.__file__); print(sys.version)'],cwd=out,env=env,text=True)
command = [str(python),'-m','loop_engine','--self-test','--format','json']
result = subprocess.run(command,cwd=out,env=env,capture_output=True,text=True)
(out/'delivery-wheel-stdout.txt').write_text(result.stdout)
(out/'delivery-wheel-stderr.txt').write_text(result.stderr)
data = json.loads(result.stdout)
(out/'delivery-wheel-result.json').write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
receipt = {'record_type':'clean_base_wheel_check/v1','started_at':started,
    'finished_at':datetime.now(timezone.utc).isoformat(),'command':command,
    'cwd':str(out),'import_identity':identity,'exit_code':result.returncode,
    'elapsed_seconds':time.monotonic()-start,
    'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),
    'result':data,'scope':'Isolated base dependencies only; optional adapters may be not tested.'}
(out/'delivery-wheel-receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps(receipt,indent=2))
raise SystemExit(result.returncode)
