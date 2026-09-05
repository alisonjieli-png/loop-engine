"""Run offline repository checks with before/after source identity."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

root = Path('/home/username/loop-engine')
out = Path('/tmp/loop-learning-20260904.nM5vjD')
phase = sys.argv[1]
args = sys.argv[2:]

def source_identity():
    paths = sorted(path for base in ('src', 'devtools/src', 'benchmarks')
                   for path in (root/base).rglob('*.py') if '__pycache__' not in path.parts)
    rows = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths}
    return rows

before = source_identity()
started = datetime.now(timezone.utc).isoformat()
head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
(out/(phase+'-source-before.json')).write_text(json.dumps(before,sort_keys=True,indent=2)+'\n')
env = os.environ.copy()
env['PYTHONPATH'] = str(root/'src')+os.pathsep+str(root/'devtools/src')
env['PYTHONDONTWRITEBYTECODE'] = '1'
command = [sys.executable,*args]
start = time.monotonic()
result = subprocess.run(command,cwd=root,env=env,capture_output=True,text=True)
(out/(phase+'-stdout.txt')).write_text(result.stdout)
(out/(phase+'-stderr.txt')).write_text(result.stderr)
after = source_identity()
receipt = {'phase':phase,'started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),
           'head':head,'command':command,'exit_code':result.returncode,
           'elapsed_seconds':time.monotonic()-start,'source_files':len(before),
           'source_changes_during_check':[name for name in set(before)|set(after)
                                          if before.get(name)!=after.get(name)]}
try:
    data=json.loads(result.stdout)
    (out/(phase+'-result.json')).write_text(json.dumps(data,sort_keys=True,indent=2)+'\n')
    receipt['result_summary']={key:data[key] for key in ('passed','total','all_passed','all_gates_pass') if key in data}
except ValueError:
    receipt['stdout_tail']=result.stdout[-1000:]
(out/(phase+'-receipt.json')).write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
raise SystemExit(result.returncode)
