"""Independent bounded candidate runner; no host candidate imports or network."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True
TRUSTED_SOURCE = Path('/home/username/.le-codex-build/integration')
sys.path.insert(0, str(TRUSTED_SOURCE / 'src'))
from loop_engine.core.library_ingestion.processes import run_command

RUNNER = '''import os, resource, runpy, sys
resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
resource.setrlimit(resource.RLIMIT_NPROC, (1, 1))
resource.setrlimit(resource.RLIMIT_FSIZE, (65536, 65536))
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
for descriptor, target in ((1, "/stdout.bin"), (2, "/stderr.bin")):
    held = os.open(target, os.O_WRONLY)
    os.dup2(held, descriptor)
    os.close(held)
sys.argv = ["/package/tool.py"]
with open("/input.json", "r", encoding="utf-8") as stream:
    sys.stdin = stream
    runpy.run_path("/package/tool.py", run_name="__main__")
'''


def digest(value):
    return hashlib.sha256(value).hexdigest()


def strict_loads(value, *, parse_float=float):
    def pairs(rows):
        out = {}
        for name, value in rows:
            if name in out:
                raise ValueError('duplicate_json_key')
            out[name] = value
        return out
    def constant(value):
        raise ValueError('nonfinite_json_literal')
    return json.loads(value, object_pairs_hook=pairs, parse_constant=constant, parse_float=parse_float)


def run_bytes(script, raw_input, *, output_limit_bytes=65536):
    """Run frozen bytes, never a concurrently changing authored pathname."""
    if type(output_limit_bytes) is not int or not 65536 <= output_limit_bytes <= 1048576:
        raise ValueError("invalid_sandbox_output_bound")
    runner_text = RUNNER.replace("65536, 65536", f"{output_limit_bytes}, {output_limit_bytes}")
    with tempfile.TemporaryDirectory(prefix='baltor-independent-component-') as folder:
        root = Path(folder)
        paths = {name: root / name for name in ('tool.py', 'input.json', 'runner.py', 'stdout.bin', 'stderr.bin')}
        paths['tool.py'].write_bytes(script)
        paths['input.json'].write_bytes(raw_input)
        paths['runner.py'].write_text(runner_text)
        for name in ('stdout.bin', 'stderr.bin'):
            paths[name].write_bytes(b'')
        argv = ['/usr/bin/bwrap', '--unshare-all', '--die-with-parent', '--new-session', '--clearenv',
                '--cap-drop', 'ALL', '--ro-bind', '/usr', '/usr', '--symlink', 'usr/bin', '/bin',
                '--symlink', 'usr/lib', '/lib', '--symlink', 'usr/lib64', '/lib64',
                '--dev', '/dev', '--proc', '/proc', '--tmpfs', '/tmp', '--dir', '/work',
                '--ro-bind', str(paths['tool.py']), '/package/tool.py',
                '--ro-bind', str(paths['input.json']), '/input.json',
                '--ro-bind', str(paths['runner.py']), '/runner.py',
                '--bind', str(paths['stdout.bin']), '/stdout.bin',
                '--bind', str(paths['stderr.bin']), '/stderr.bin',
                '--chdir', '/work', '--setenv', 'HOME', '/tmp', '--setenv', 'PATH', '/usr/bin:/bin',
                '--', '/usr/bin/python3', '-I', '-S', '-B', '/runner.py']
        result = run_command(tuple(argv), timeout_seconds=4, maximum_output_bytes=2048,
                             environment={'PATH': '/usr/bin:/bin'})
        stdout, stderr = paths['stdout.bin'].read_bytes(), paths['stderr.bin'].read_bytes()
    try:
        output = strict_loads(stdout)
    except (ValueError, UnicodeError):
        output = None
    return {'runner_sha256': digest(runner_text.encode()), 'output_limit_bytes': output_limit_bytes, 'script_sha256': digest(script), 'input_sha256': digest(raw_input),
            'exit_code': result.exit_code, 'elapsed_ms': result.elapsed_ms,
            'timed_out': result.timed_out, 'launcher_truncated': result.truncated,
            'stdout_bytes': len(stdout), 'stderr_bytes': len(stderr),
            'stdout_sha256': digest(stdout), 'stderr_sha256': digest(stderr),
            'output': output, 'stderr_tail': stderr.decode('utf-8', 'replace')[-400:],
            'launcher_stderr': result.stderr_tail}


def bindings(folder):
    rows = []
    for path in sorted(folder.rglob('*')):
        if path.is_symlink():
            raise ValueError('authored_symlink_unsupported')
        if path.is_file():
            raw = path.read_bytes()
            rows.append({'path': path.relative_to(folder).as_posix(), 'digest': digest(raw), 'size_bytes': len(raw)})
    return {'files': rows, 'tree_binding_sha256': digest(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode())}
