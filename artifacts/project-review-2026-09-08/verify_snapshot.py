"""Read-only package and checkout identity checks for this review."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

REVIEW = Path(__file__).resolve().parent
SOURCE = Path('/home/username/loop-engine/src/loop_engine')
SNAPSHOT = REVIEW / 'evidence/snapshot/src/loop_engine'

def identities(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*.py'))}

frozen = identities(SNAPSHOT)
current = identities(SOURCE)
wheel = REVIEW / 'dist/loop_engine-0.1.0-py3-none-any.whl'
with ZipFile(wheel) as archive:
    names = archive.namelist()
    wheel_python = {name.removeprefix('loop_engine/'):
                    hashlib.sha256(archive.read(name)).hexdigest()
                    for name in names
                    if name.startswith('loop_engine/') and name.endswith('.py')}
    local_state = [name for name in names
                   if '/evidence/runs/' in name or '/evidence/studio/' in name]
    dev_files = [name for name in names
                 if name.startswith(('devtools/', 'embodiments/', 'embodiment_lab/'))]

print(json.dumps({
    'source_python_modules': len(current),
    'snapshot_python_modules': len(frozen),
    'wheel_python_modules': len(wheel_python),
    'source_unchanged_since_snapshot': current == frozen,
    'wheel_python_exactly_matches_snapshot': wheel_python == frozen,
    'local_run_history_or_studio_files_in_wheel': local_state,
    'experimental_modules_in_wheel': dev_files,
    'wheel_sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(),
}, indent=2))
