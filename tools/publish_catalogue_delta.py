"""Publish one catalogue release to the live Machine by uploading only the blobs it adds.

The full-bundle publish uploads a whole tar of every blob the release names, so each slot re-sends the
bytes the volume already holds. The blobs are content-addressed (`blobs/sha256/<first two>/<digest>`),
so the set a release adds is exactly the set the remote lacks. This tool reads the remote's present
digests, uploads only the missing ones, then writes the release's own `bundle.json` and `items.jsonl`
and moves the pointer through the same `publish-catalogue` command every other release uses.

Nothing about the release changes. The pointer still moves in one batch that commits the release, the
pointer, the withdrawals and the marker together, and `publish-catalogue` still refuses a header that
differs from the digest the builder printed, a withdrawn item version that stays listed, and a body whose
bytes do not match the digest its entry names. A blob that never arrived therefore fails the publish
rather than reaching a customer, and a rerun after a partial upload resumes from what is present.

Measured on September 28, 2026 against the slot bundle daily-2026-09-28-10: 51,571 blobs and 386 MB
were uploaded whole, of which the volume already held almost every byte. This tool uploads the missing
share and writes the two manifest files instead.

Usage: publish_catalogue_delta.py NAME BUNDLE_FOLDER BUNDLE_DIGEST [--dry-run]
  NAME           the slot name, used for the staging folder and the record
  BUNDLE_FOLDER  the local bundle directory holding bundle.json, items.jsonl and blobs/
  BUNDLE_DIGEST  the digest the bundle builder printed

Every command is reached through tools/fly_operator.py, the same operator credential path the rest of the
release uses. No secret is read here and no address is taken from the environment.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

REMOTE_ROOT = "/data/incoming"
MACHINE = "83733ea7779068"
APP = "baltor-pilot"
#: The service user, as every catalogue write runs. An upload above it is an ordinary file write.
AS_SERVICE = "setpriv --reuid=65534 --regid=65534 --clear-groups"
#: How long one Fly call waits. A listing of tens of thousands of digests is well inside this.
EXEC_TIMEOUT = 600
#: How many bytes one sftp put carries. One put per blob is 1,500 round trips; one put for the whole
#: bundle is the 386 MB upload this tool exists to remove.
BATCH_BYTES = 24 * 1024 * 1024
#: How long to wait for the pointer to move before reporting that nothing was published.
POINTER_WAIT_SECONDS = 120 * 60


def fly(*arguments: str, timeout: int = EXEC_TIMEOUT) -> str:
    """Run one exact Fly command through the operator credential path and return its stdout."""
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("fly_operator.py")),
         "--account", "baltor", "--timeout", str(timeout), "--", *arguments],
        capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()[:400]
        raise RuntimeError(f"the Fly command {' '.join(arguments[:3])} failed: {detail}")
    return completed.stdout


def machine_exec(command: str, *, as_service: bool = False, timeout: int = EXEC_TIMEOUT) -> str:
    """Run one command on the Machine through the Machines API and return its stdout."""
    remote = f"{AS_SERVICE} {command}" if as_service else command
    answer = json.loads(fly("machine", "exec", MACHINE, remote, "--app", APP, "--json", timeout=timeout))
    code = answer.get("exit_code") or 0
    if code:
        detail = (answer.get("stdout") or answer.get("stderr") or "").strip()[:400]
        raise RuntimeError(f"the command failed on the Machine (exit {code}): {detail}")
    return (answer.get("stdout") or "").strip()


def blob_digests(folder: Path) -> list[str]:
    """Every blob digest a bundle folder holds, in a stable order."""
    return sorted(path.name for path in (folder / "blobs" / "sha256").glob("*/*")
                  if path.is_file() and len(path.name) == 64)


def remote_digests() -> set[str]:
    """Every blob digest already on the volume, wherever it was unpacked.

    A published release's own folder is removed after the pointer moves, so the present set is read
    from the whole data volume rather than from one release folder. An unreadable listing is an error
    rather than an empty set: treating it as empty would re-upload everything, which is correct but
    hides the fault this tool exists to avoid.
    """
    listing = machine_exec(
        f"find /data -type f -path '*/blobs/sha256/*/*' -printf '%f\\n' 2>/dev/null")
    return {name.strip() for name in listing.splitlines() if len(name.strip()) == 64}


def group_batches(missing: list[str], sizes: dict[str, int]) -> list[list[str]]:
    """Group the missing digests into puts of at most BATCH_BYTES."""
    grouped: list[list[str]] = []
    current: list[str] = []
    total = 0
    for digest in missing:
        size = sizes.get(digest, 0)
        if current and total + size > BATCH_BYTES:
            grouped.append(current)
            current, total = [], 0
        current.append(digest)
        total += size
    if current:
        grouped.append(current)
    return grouped


def stage_batch(bundle: Path, group: list[str], workdir: Path) -> Path:
    """A directory holding this batch's blobs at the relative paths the bundle reader expects."""
    stage = workdir / "batch"
    if stage.exists():
        shutil.rmtree(stage)
    for digest in group:
        target = stage / "blobs" / "sha256" / digest[:2] / digest
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(bundle / "blobs" / "sha256" / digest[:2] / digest, target)
    return stage


def upload_missing(bundle: Path, missing: list[str], remote: str) -> None:
    """Put the missing blobs into the remote release folder, then prove every one arrived whole.

    Each put carries a directory of blobs at their own relative paths, so the bytes land where the
    bundle reader looks for them. Afterwards the digests present under the release folder are read back
    and compared: a put that was cut short is a failure here, not a body that fails a customer's
    download later.
    """
    if not missing:
        return
    sizes = {path.name: path.stat().st_size
             for path in (bundle / "blobs" / "sha256").glob("*/*") if path.is_file()}
    groups = group_batches(missing, sizes)
    workdir = Path(tempfile.mkdtemp(prefix="catalogue-delta-"))
    try:
        for number, group in enumerate(groups, 1):
            stage = stage_batch(bundle, group, workdir)
            fly("ssh", "sftp", "put", "-r", "-g", str(stage), f"{REMOTE_ROOT}/{remote}/",
                "--app", APP, timeout=EXEC_TIMEOUT)
            print(f"  batch {number}/{len(groups)}: {len(group)} blobs, "
                  f"{sum(sizes.get(digest, 0) for digest in group) // 1024} KiB", flush=True)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    landed = machine_exec(
        f"find {REMOTE_ROOT}/{remote}/blobs/sha256 -type f -printf '%f\\n' 2>/dev/null")
    present = {name.strip() for name in landed.splitlines() if len(name.strip()) == 64}
    absent = [digest for digest in missing if digest not in present]
    if absent:
        raise RuntimeError(f"{len(absent)} blobs did not arrive, so nothing was published: {absent[:5]}")


def active_release() -> str:
    """The release the store's pointer names now, or an empty string when it cannot be read."""
    try:
        status = machine_exec(
            f"{AS_SERVICE} loop-engine service catalogue-status --config /data/host.json",
            as_service=True, timeout=120)
    except (RuntimeError, ValueError):
        return ""
    try:
        return (json.loads(status).get("result", {}) or {}).get("active_release_id", "")
    except ValueError:
        return ""


def publish(name: str, bundle: Path, digest: str) -> dict:
    """Upload what is missing, write the release folder, and move the pointer by the ordinary command."""
    remote = f"delta-{name}-{int(time.time())}"
    machine_exec(f"mkdir -p {REMOTE_ROOT}/{remote}/blobs/sha256")

    local = blob_digests(bundle)
    sizes = {path.name: path.stat().st_size
             for path in (bundle / "blobs" / "sha256").glob("*/*") if path.is_file()}
    present = remote_digests()
    missing = [value for value in local if value not in present]
    total_bytes = sum(sizes.values())
    missing_bytes = sum(sizes[value] for value in missing)
    plan = {"release": remote, "local_blobs": len(local),
            "already_present": len(local) - len(missing), "uploading": len(missing),
            "bundle_bytes": total_bytes, "upload_bytes": missing_bytes,
            "share_of_full_upload": round(missing_bytes / total_bytes, 4) if total_bytes else None,
            "batches": len(group_batches(missing, sizes))}
    print(json.dumps(plan, indent=2), flush=True)
    if not local:
        raise RuntimeError("the bundle holds no blobs, so nothing would be published")

    upload_missing(bundle, missing, remote)
    for filename in ("bundle.json", "items.jsonl"):
        fly("ssh", "sftp", "put", str(bundle / filename), f"{REMOTE_ROOT}/{remote}/{filename}",
            "--app", APP, timeout=EXEC_TIMEOUT)
    machine_exec(f"{AS_SERVICE} chown -R 65534:65534 {REMOTE_ROOT}/{remote}", as_service=True, timeout=300)

    before = active_release()
    if not before:
        raise RuntimeError("the active release could not be read before publishing; nothing was published")
    machine_exec(
        f"{AS_SERVICE} sh -c 'nohup loop-engine service publish-catalogue --config /data/host.json "
        f"--bundle {REMOTE_ROOT}/{remote} --expected-bundle-digest {digest} "
        f"> {REMOTE_ROOT}/delta.publish.json 2>&1 &'", as_service=True, timeout=120)

    deadline = time.monotonic() + POINTER_WAIT_SECONDS
    minute = 0
    while time.monotonic() < deadline:
        time.sleep(60)
        minute += 1
        now = active_release()
        if now and now != before:
            machine_exec(f"rm -r {REMOTE_ROOT}/{remote} {REMOTE_ROOT}/delta.publish.json", timeout=300)
            return {"published": True, "active_release_id": now, "waited_minutes": minute, **plan}
        try:
            refused = machine_exec(
                f"grep -q '\\\"refused\\\": true\\|Error\\|Traceback' {REMOTE_ROOT}/delta.publish.json "
                f"&& head -c 1200 {REMOTE_ROOT}/delta.publish.json", timeout=60)
        except RuntimeError:
            refused = ""
        if refused:
            raise RuntimeError(f"the publish refused:\n{refused}")
        print(f"  publishing, minute {minute} (active still {before[:12]})", flush=True)
    raise RuntimeError("the active release did not change within two hours; nothing was published")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("name")
    parser.add_argument("bundle_folder", type=Path)
    parser.add_argument("bundle_digest")
    parser.add_argument("--dry-run", action="store_true",
                        help="report the delta and write nothing")
    arguments = parser.parse_args()
    bundle = arguments.bundle_folder
    for required in ("bundle.json", "items.jsonl", "blobs"):
        if not (bundle / required).exists():
            print(f"the bundle folder has no {required}", file=sys.stderr)
            return 2
    if arguments.dry_run:
        local = blob_digests(bundle)
        sizes = {path.name: path.stat().st_size
                 for path in (bundle / "blobs" / "sha256").glob("*/*") if path.is_file()}
        present = remote_digests()
        missing = [value for value in local if value not in present]
        total = sum(sizes.values())
        print(json.dumps({"local_blobs": len(local), "already_present": len(local) - len(missing),
                          "uploading": len(missing), "bundle_bytes": total,
                          "upload_bytes": sum(sizes[value] for value in missing),
                          "share_of_full_upload": round(sum(sizes[v] for v in missing) / total, 4) if total else None,
                          "batches": len(group_batches(missing, sizes))}, indent=2))
        return 0
    try:
        print(json.dumps(publish(arguments.name, bundle, arguments.bundle_digest), indent=2))
    except RuntimeError as error:
        print(f"the delta publish failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
