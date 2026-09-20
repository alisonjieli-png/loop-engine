"""Validate the worker image recipe and the Kubernetes manifests offline.

The engine image is built from the repository Dockerfile; this example does
not build it (no Docker is required) and does not deploy anything. It
checks the Dockerfile for the facts a deployment needs (a base image, a
non-root user, the loop-engine entry point, no baked-in secret shape), and
it checks each manifest for the fields that keep a cluster honest: a kind
and version, a non-root security context, resource requests and limits on
every container, and an image reference placeholder that a deployment
replaces with a digest-pinned image.

Run:
    python3 examples/28_containerized_worker/run.py

No network, no external service, no model calls, no cluster.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from loop_engine import LoopLedger
from loop_engine.loop.encapsulate import as_practitioner_loop

HERE = Path(__file__).resolve().parent
REPOSITORY = HERE.parents[1]
MANIFESTS = ("k8s/worker-deployment.yaml", "k8s/solution-job.yaml")
_SECRET_SHAPES = (re.compile(r"sk-[A-Za-z0-9]{20,}"), re.compile(r"AKIA[0-9A-Z]{16}"),
                  re.compile(r"(?i)authorization:\s*bearer\s+\S+"))


def check_dockerfile(text: str) -> list[dict]:
    lines = [line.strip() for line in text.splitlines()]
    from_lines = [line for line in lines if line.startswith("FROM ")]
    users = [line.split(None, 1)[1].split(":", 1)[0].strip().lower()
             for line in lines if line.startswith("USER ")]
    commands = re.sub(r"\\\n\s*", " ", text).splitlines()
    installs = [line for line in commands
                if line.startswith("RUN ") and "pip install" in line]
    pinned = bool(from_lines) and bool(re.fullmatch(
        r"FROM\s+\S+@sha256:[0-9a-f]{64}(?:\s+AS\s+\S+)?", from_lines[0]))
    return [
        {"check": "one_base_image", "passed": len(from_lines) == 1,
         "detail": from_lines[0] if from_lines else "no FROM line"},
        {"check": "base_image_digest_pinned", "passed": pinned,
         "detail": "pinned" if pinned else "a valid sha256 base image digest is required"},
        {"check": "runs_as_non_root", "passed": bool(users) and users[-1] not in ("0", "root")},
        {"check": "installation_failure_is_not_suppressed",
         "passed": bool(installs) and all("||" not in line for line in installs)},
        {"check": "entry_point_is_loop_engine", "passed": any(line.startswith("ENTRYPOINT") and "loop-engine" in line for line in lines)},
        {"check": "no_secret_shape", "passed": not any(pattern.search(text) for pattern in _SECRET_SHAPES)},
    ]


def check_manifest(document: dict) -> list[dict]:
    kind = document.get("kind")
    spec = document.get("spec") or {}
    template = spec.get("template") or {}
    pod = template.get("spec") or {}
    containers = pod.get("containers") or []
    security = pod.get("securityContext") or {}
    checks = [
        {"check": "kind_and_version", "passed": bool(kind) and bool(document.get("apiVersion")), "detail": f"{document.get('apiVersion')} {kind}"},
        {"check": "non_root_security_context", "passed": security.get("runAsNonRoot") is True and isinstance(security.get("runAsUser"), int) and security.get("runAsUser") != 0},
        {"check": "every_container_has_requests_and_limits",
         "passed": bool(containers) and all(
             {"cpu", "memory"} <= set((item.get("resources") or {}).get("requests") or {})
             and {"cpu", "memory"} <= set((item.get("resources") or {}).get("limits") or {}) for item in containers)},
        {"check": "image_reference_placeholder", "passed": all(item.get("image") == "IMAGE_REFERENCE" for item in containers),
         "detail": "replace IMAGE_REFERENCE with a digest-pinned image at deployment"},
        {"check": "no_secret_shape", "passed": not any(pattern.search(json.dumps(document)) for pattern in _SECRET_SHAPES)},
    ]
    if kind == "Job":
        checks.append({"check": "job_does_not_retry_silently", "passed": spec.get("backoffLimit") == 0
                       and pod.get("restartPolicy") == "Never"})
    if kind == "Deployment":
        checks.append({"check": "worker_serves_the_api_with_a_readiness_probe",
                       "passed": bool(containers) and "api" in (containers[0].get("args") or [])
                       and bool(containers[0].get("readinessProbe"))})
    return checks


def validate(_inputs=None) -> dict:
    dockerfile = (REPOSITORY / "Dockerfile").read_text("utf-8")
    results = {"Dockerfile": check_dockerfile(dockerfile)}
    for relative in MANIFESTS:
        document = yaml.safe_load((HERE / relative).read_text("utf-8"))
        results[relative] = check_manifest(document)
    return results


def rejection_checks() -> list[dict]:
    """Counterexamples that must fail the recipe's named protections."""
    image = "FROM python:3.12-slim@sha256:" + "0" * 64 + "\n"
    clean = image + 'RUN python -m pip install .\nUSER 65534\nENTRYPOINT ["loop-engine"]\n'

    def passes(text, name):
        return next(item["passed"] for item in check_dockerfile(text) if item["check"] == name)

    return [
        {"check": "a_valid_recipe_passes", "passed": all(item["passed"] for item in check_dockerfile(clean))},
        {"check": "numeric_and_named_root_are_refused",
         "passed": all(not passes(clean.replace("USER 65534", "USER " + user), "runs_as_non_root")
                       for user in ("0", "0:0", "root", "root:65534"))},
        {"check": "invalid_and_missing_digests_are_refused",
         "passed": not passes(clean.replace("0" * 64, "invalid"), "base_image_digest_pinned")
         and not passes(clean.replace("@sha256:" + "0" * 64, ""), "base_image_digest_pinned")},
        {"check": "masked_installation_failure_is_refused",
         "passed": not passes(clean.replace("pip install .", "pip install . || true"),
                              "installation_failure_is_not_suppressed")},
    ]


def main() -> int:
    ledger = LoopLedger()
    outcome = as_practitioner_loop("validate the worker image recipe and manifests", validate, ledger=ledger)
    print("CONTAINERIZED WORKER")
    print(f"loop: {outcome['loop_id']}  ledger events: {len(ledger.events)}")
    all_passed = True
    for name, checks in {**outcome["value"], "rejection controls": rejection_checks()}.items():
        print()
        print(name.upper())
        for item in checks:
            mark = "ok  " if item["passed"] else "FAIL"
            all_passed = all_passed and item["passed"]
            detail = f": {item['detail']}" if item.get("detail") else ""
            print(f"  {mark} {item['check']}{detail}")
    print()
    print("Deployment itself needs a cluster and an account; this example proves only the recipes.")
    print(f"passed: {all_passed}")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
