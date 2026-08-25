"""Build and enforce the DS-1000 evaluator container boundary."""
from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


BENCHMARK_DIR = Path(__file__).resolve().parent
RUNTIME_TAG = "loop-engine-ds1000-runtime:v1"
BASE_IMAGE_DIGEST = (
    "python@sha256:2407c61b1a18067393fecd8a22cf6fceede893b6aaca817bf9fbfe65e33614a3"
)


class RuntimeGateError(RuntimeError):
    """The evaluator image or sandbox controls failed closed."""


@dataclass(frozen=True)
class RuntimeImage:
    tag: str
    image_id: str
    platform: str
    base_image_digest: str
    requirements_sha256: str
    source_execution_sha256: str

    def as_dict(self) -> dict:
        return {
            "tag": self.tag,
            "image_id": self.image_id,
            "platform": self.platform,
            "base_image_digest": self.base_image_digest,
            "requirements_sha256": self.requirements_sha256,
            "source_execution_sha256": self.source_execution_sha256,
        }


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sandbox_command(image: RuntimeImage, *, interactive: bool = False) -> list[str]:
    command = [
        "docker", "run", "--rm",
        "--network", "none",
        "--read-only",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges:true",
        "--pids-limit", "128",
        "--memory", "4g",
        "--cpus", "2",
        "--ulimit", "nofile=256:256",
        "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=1073741824",
        "--env", "PYTHONDONTWRITEBYTECODE=1",
        "--env", "OMP_NUM_THREADS=1",
        "--env", "OPENBLAS_NUM_THREADS=1",
        "--env", "MKL_NUM_THREADS=1",
        "--env", "NUMEXPR_NUM_THREADS=1",
    ]
    if interactive:
        command.append("-i")
    command.append(image.image_id)
    return command


def build_runtime() -> RuntimeImage:
    requirements = BENCHMARK_DIR / "requirements.lock"
    execution = BENCHMARK_DIR / ".cache" / "upstream" / "execution.py"
    if not requirements.is_file() or not execution.is_file():
        raise RuntimeGateError(
            "runtime inputs are missing; prepare the pinned source first")
    requirements_sha = sha256_file(requirements)
    execution_sha = sha256_file(execution)
    labels = [
        "--label", "org.loop-engine.benchmark=ds1000-v1",
        "--label", f"org.loop-engine.requirements-sha256={requirements_sha}",
        "--label", f"org.loop-engine.execution-sha256={execution_sha}",
        "--label", f"org.loop-engine.base-image={BASE_IMAGE_DIGEST}",
    ]
    completed = subprocess.run(
        ["docker", "build", "--pull=false", *labels, "-t", RUNTIME_TAG, "."],
        cwd=BENCHMARK_DIR, text=True, capture_output=True)
    if completed.returncode != 0:
        raise RuntimeGateError(
            "evaluator image build failed:\n" + completed.stdout + completed.stderr)
    inspected = subprocess.run(
        ["docker", "image", "inspect", RUNTIME_TAG],
        check=True, text=True, capture_output=True)
    row = json.loads(inspected.stdout)[0]
    observed_labels = row.get("Config", {}).get("Labels", {}) or {}
    expected_labels = {
        "org.loop-engine.benchmark": "ds1000-v1",
        "org.loop-engine.requirements-sha256": requirements_sha,
        "org.loop-engine.execution-sha256": execution_sha,
        "org.loop-engine.base-image": BASE_IMAGE_DIGEST,
    }
    if any(observed_labels.get(key) != value
           for key, value in expected_labels.items()):
        raise RuntimeGateError("built image labels do not bind the frozen inputs")
    runtime = RuntimeImage(
        tag=RUNTIME_TAG,
        image_id=str(row["Id"]),
        platform=f"{row['Os']}/{row['Architecture']}",
        base_image_digest=BASE_IMAGE_DIGEST,
        requirements_sha256=requirements_sha,
        source_execution_sha256=execution_sha,
    )
    verify_sandbox(runtime)
    return runtime


def verify_sandbox(runtime: RuntimeImage) -> dict:
    probe = """
import json, os, socket
result = {"uid": os.getuid(), "root_write_blocked": False,
          "network_blocked": False, "tmp_write": False}
try:
    open('/sandbox-write-probe', 'w').write('x')
except OSError:
    result['root_write_blocked'] = True
try:
    s = socket.create_connection(('1.1.1.1', 53), timeout=1)
    s.close()
except OSError:
    result['network_blocked'] = True
try:
    open('/tmp/sandbox-probe', 'w').write('x')
    result['tmp_write'] = True
except OSError:
    pass
print(json.dumps(result, sort_keys=True))
"""
    completed = subprocess.run(
        [*sandbox_command(runtime), "python", "-c", probe],
        text=True, capture_output=True, timeout=30)
    try:
        result = json.loads(completed.stdout.strip())
    except json.JSONDecodeError as exc:
        raise RuntimeGateError(
            "sandbox probe did not return JSON: " + completed.stderr) from exc
    passed = (
        completed.returncode == 0
        and int(result.get("uid", 0)) != 0
        and result.get("root_write_blocked") is True
        and result.get("network_blocked") is True
        and result.get("tmp_write") is True
    )
    if not passed:
        raise RuntimeGateError(f"sandbox controls failed: {result}")
    return {
        "record_type": "ds1000_sandbox_verification/v1",
        "ok": True,
        "image_id": runtime.image_id,
        "controls": {
            "non_root": True,
            "network_none": True,
            "read_only_root": True,
            "capabilities_dropped": "ALL",
            "no_new_privileges": True,
            "pids_limit": 128,
            "memory_limit": "4g",
            "cpu_limit": 2,
            "tmpfs_only_write": True,
        },
    }

