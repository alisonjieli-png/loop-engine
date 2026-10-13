"""Actual, bounded negative controls for owned native-customer cgroups.

No native model, service account, timer or shared slice is touched. Each test
launches one fresh Bubblewrap namespace in its own transient user service.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

from loop_engine.core.harness_customer_resources import CustomerResourceLimits, CustomerResourceScope


def confined(code):
    return ["/usr/bin/bwrap", "--unshare-all", "--die-with-parent", "--new-session", "--clearenv",
            "--ro-bind", "/usr", "/usr", "--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib",
            "--symlink", "usr/lib64", "/lib64", "--proc", "/proc", "--dev", "/dev", "--size", "67108864", "--tmpfs", "/tmp",
            "--size", "268435456", "--tmpfs", "/work",
            "--setenv", "PATH", "/usr/bin:/bin", "--", "/usr/bin/python3", "-u", "-c", code]


def run(output):
    output.mkdir(mode=0o700)
    evidence = {"record_type": "customer_cgroup_negative_controls/v1", "model_calls": 0,
                "service_requests": 0, "tests": []}
    root = Path(__file__).resolve().parents[1]
    evidence["source_sha256"] = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in
        (Path(__file__).resolve(), root / "src/loop_engine/core/harness_customer_resources.py")}
    codes = {
        "memory": "import time; print('started'); time.sleep(.5); value=bytearray(256*1024*1024); value[::4096]=b'x'*65536; print('unbounded')",
        "tasks": """import os,time,signal,json
children=[]; refused=False
time.sleep(.5)
try:
    for _ in range(20):
        try: pid=os.fork()
        except OSError: refused=True; break
        if pid == 0: time.sleep(10); os._exit(0)
        children.append(pid)
    print(json.dumps({'started':len(children),'refused':refused}),flush=True)
finally:
    for pid in children:
        os.kill(pid,signal.SIGKILL); os.waitpid(pid,0)
""",
        "wall": "import time; print('started'); time.sleep(10); print('unbounded')",
        "cancel_descendants": """import os,time
pid=os.fork()
print('parent' if pid else 'child',flush=True)
time.sleep(10)
print('unbounded',flush=True)
""",
        "scratch_many_files": """import os,time,json,errno
time.sleep(.5)
count=0; refused=False
try:
    for index in range(20000):
        with open('/work/file-'+str(index),'xb') as stream: stream.write(b'x'*16384)
        count+=1
except OSError as error:
    refused=error.errno == errno.ENOSPC
usage=os.statvfs('/work')
print(json.dumps({'files':count,'refused':refused,'total_bytes':usage.f_blocks*usage.f_frsize}))
"""}
    for name, code in codes.items():
        scope = CustomerResourceScope(CustomerResourceLimits((512 if name == "scratch_many_files" else 128) * 1024 * 1024, 8, 100))
        row = {"name": name}
        proc = None
        started = time.monotonic()
        try:
            proc = subprocess.Popen(scope.command(confined(code), 2 if name == "wall" else 5),
                env=scope.environment(), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            scope.dispatched = True
            row["resources"] = scope.wait_verified(proc)
            if name == "cancel_descendants":
                time.sleep(.3)
                scope.stop()
            out, err = proc.communicate(timeout=7)
            row.update(exit_code=proc.returncode, stdout=out.decode(), stderr=err.decode())
            if name == "scratch_many_files":
                result = json.loads(out)
                row["passed"] = proc.returncode == 0 and result["refused"] and 1 < result["files"] < 20000 and result["total_bytes"] == 268435456
            elif name == "tasks":
                result = json.loads(out)
                row["passed"] = proc.returncode == 0 and result["refused"] and 0 < result["started"] < 20
            else:
                row["passed"] = proc.returncode != 0 and b"unbounded" not in out and bool(out.strip())
            row["elapsed_seconds"] = round(time.monotonic() - started, 4)
            if name == "wall":
                row["passed"] = row["passed"] and row["elapsed_seconds"] < 6
        except Exception as error:
            row.update(passed=False, error=type(error).__name__ + ": " + str(error))
        finally:
            try:
                scope.stop()
            except Exception as error:
                row.update(passed=False, cleanup_error=type(error).__name__ + ": " + str(error))
            if proc is not None:
                if proc.poll() is None:
                    proc.kill()
                proc.wait(timeout=3)
            row["cleanup_confirmed"] = scope.cleanup_confirmed
            row["passed"] = row.get("passed", False) and scope.cleanup_confirmed
            evidence["tests"].append(row)
    evidence["passed"] = all(row["passed"] for row in evidence["tests"])
    (output / "report.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps({"passed": evidence["passed"], "tests": len(evidence["tests"]), "report": str(output / "report.json")}))
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    raise SystemExit(run(parser.parse_args().output))
