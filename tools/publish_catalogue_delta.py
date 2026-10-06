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

Usage: publish_catalogue_delta.py NAME BUNDLE_FOLDER BUNDLE_DIGEST
       --base-bundle BASE --base-release RELEASE --reconciliation-digest DIGEST
       [--body-root ROOT] [--accept-license LICENSE] [--dry-run]
  NAME           the slot name, used for the staging folder and the record
  BUNDLE_FOLDER  the local bundle directory holding bundle.json, items.jsonl and blobs/
  BUNDLE_DIGEST  the digest the bundle builder printed

Every command is reached through tools/fly_operator.py, the same operator credential path the rest of the
release uses. No secret is read here and no address is taken from the environment.

A version 2 (segmented) bundle is published the same way after one more step:
the tool asks the Machine which bundle versions its image reads
(`loop-engine service catalogue-formats`) and refuses before any upload when
the image does not read version 2; an image that predates that command reads
version 1 only. It then uploads, beside the missing bodies, only the segments
and item lines the live release does not hold, and the release's segment list
in place of `items.jsonl`.

Existing releases require an exact full baseline and the reconciliation proof
from reconcile_catalogue_bundle.py. A delta-only baseline needs explicit local
body roots for its missing files. Bootstrap and deliberate rollback remain the
existing service operator's separate operations; no-base delta publication is
not a bypass around preservation. Dry-run checks the local proof/bytes but makes
no live request, so it is not a current-live publication permission.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid
from pathlib import Path
from urllib.parse import urlunsplit
from urllib.request import urlopen

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
#: Content-addressed object directories in the supported catalogue bundle formats.
BLOB_OBJECT, SEGMENT_OBJECT, ITEM_OBJECT = UPLOAD_OBJECT_KINDS = ("blobs", "segments", "items")
#: How long to wait for the pointer to move before reporting that nothing was published.
POINTER_WAIT_SECONDS = 120 * 60
MAXIMUM_UPLOAD_WORKERS = 4
MAXIMUM_UPLOAD_ATTEMPTS = 3
STAGING_CONTEXT = "upload-context.json"
#: Transfer-state sentinels emitted by the remote file-presence probe below.
STAGING_DISPATCHED, STAGING_UNBOUND = "dispatched", "unbound"


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
    """Run one command on the Machine through the Machines API and return its stdout.

    The Machines API execs the command inside the Machine without a shell, so a redirect, a pipe or a glob
    reaches the program as a plain argument and `find` refuses it: on September 29, 2026 the first run of
    this tool failed with "paths must precede expression: `2>/dev/null'". The command is therefore wrapped in
    `sh -c` here, once, so every caller can use ordinary shell syntax. The service prefix stays outside the
    `sh -c` so it execs the command, not a shell, and the caller keeps its own environment.
    """
    # A command that already carries the service prefix is execed as it stands: the API runs it directly, so
    # `setpriv` is the first program the Machine starts and it can drop to the service user. Wrapping that same
    # command in a shell would start a shell as nobody first, and the inner setpriv would then fail to clear
    # groups: "setgroups failed: Operation not permitted", which is what the first publish attempt reported.
    remote = command if as_service else f"sh -c {shlex.quote(command)}"
    answer = json.loads(fly("machine", "exec", MACHINE, remote, "--app", APP, "--json", timeout=timeout))
    code = answer.get("exit_code") or 0
    if code:
        detail = (answer.get("stdout") or answer.get("stderr") or "").strip()[:400]
        raise RuntimeError(f"the command failed on the Machine (exit {code}): {detail}")
    return (answer.get("stdout") or "").strip()


def blob_digests(folder: Path) -> list[str]:
    """Every blob digest a bundle folder holds, in a stable order."""
    return sorted(path.name for path in (folder / "blobs" / "sha256").glob("*/*")
                  if path.is_file() and not path.is_symlink() and not path.parent.is_symlink()
                  and re.fullmatch(r"[0-9a-f]{64}", path.name) and path.parent.name == path.name[:2])


#: How many shard prefixes one Machines exec asks for. The API refuses a response over 10 MB once JSON encoded,
#: and one whole-volume listing refused it on September 29, 2026 once the volume held several releases' blobs.
#: A shard is one of the two hex characters a blob path starts with, so this bounds each answer to a small slice.
SHARDS_PER_CALL = 8


def shard_prefixes() -> list[str]:
    """Every two hex characters a blob's shard directory can start with."""
    return [f"{value:02x}" for value in range(256)]


def remote_digests(shards: list[str] | None = None) -> set[str]:
    """Every blob digest already on the volume, wherever it was unpacked.

    A published release's own folder is removed after the pointer moves, so the present set is read
    from the whole data volume rather than from one release folder. An unreadable listing is an error
    rather than an empty set: treating it as empty would re-upload everything, which is correct but
    hides the fault this tool exists to avoid.

    The volume is read a few shards at a time, because the whole-volume listing outgrew the response the
    Machines API will carry. Asking for a shard the volume does not hold returns nothing, so a shard that
    has never been written costs one empty answer rather than a fault.
    """
    prefixes = shard_prefixes() if shards is None else shards
    present: set[str] = set()
    for start in range(0, len(prefixes), SHARDS_PER_CALL):
        batch = prefixes[start:start + SHARDS_PER_CALL]
        paths = " -o ".join(f"-path '*/blobs/sha256/{value}/*'" for value in batch)
        listing = machine_exec(
            f"find /data -type f \\( {paths} \\) -printf '%f\\n' 2>/dev/null")
        present.update(name.strip() for name in listing.splitlines() if len(name.strip()) == 64)
    return present


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


def blob_path(digest: str) -> str:
    return f"blobs/sha256/{digest[:2]}/{digest}"


def stage_batch(bundle: Path, group: list[str], workdir: Path) -> Path:
    """A directory holding this batch's objects at the relative paths the bundle reader expects.

    A group names blob digests, or relative paths of a version 2 bundle's segments and item lines."""
    stage = workdir / "batch"
    if stage.exists():
        shutil.rmtree(stage)
    for name in group:
        relative = name if "/" in name else blob_path(name)
        target = stage / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(bundle / relative, target)
    return stage


FORMATS_COMMAND = "loop-engine service catalogue-formats --config /data/host.json"


def remote_formats():
    """The catalogue formats record the Machine's image states, or None when the image predates the command.

    The command only reads the host file. A refusal, an exit status other than zero or an answer that is not one
    JSON object is read as an image that reads version 1 only, so a version 2 bundle is refused before upload."""
    try:
        value = json.loads(machine_exec(f"{AS_SERVICE} {FORMATS_COMMAND}", as_service=True, timeout=120))
    except (RuntimeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def segmented_uploads(base, candidate) -> list[str]:
    """The relative paths of the segments and item lines a version 2 candidate adds to the live base release.

    The base is the live release (require_live_base checked its identity and content), so the service holds every
    item version it lists and, when it is a version 2 bundle, every segment it lists. Anything the service turns
    out to lack is refused by the service before activation, never served incomplete."""
    from reconcile_catalogue_bundle import SegmentedSource
    if not isinstance(candidate, SegmentedSource):
        return []
    held_segments = {ref.digest for ref in base.segments} if isinstance(base, SegmentedSource) else set()
    held_versions = {item.version for item in base.items}
    return ([f"segments/sha256/{ref.digest[:2]}/{ref.digest}" for ref in candidate.segments
             if ref.digest not in held_segments]
            + sorted(f"items/sha256/{item.version[:2]}/{item.version}" for item in candidate.items
                     if item.version not in held_versions))


def extract_archive(archive: str, digest: str, destination: str) -> None:
    """Verify one trusted archive, start extraction once and poll its bounded receipt."""
    measured = machine_exec(f"sha256sum {archive}").split()
    if not measured or measured[0] != digest:
        raise RuntimeError("uploaded archive digest differs; extraction was not started")
    status, log = archive + ".status", archive + ".log"
    command = f"tar -xf {archive} -C {destination} > {log} 2>&1; printf '%s' $? > {status}"
    machine_exec(f"nohup sh -c {shlex.quote(command)} </dev/null >/dev/null 2>&1 &")
    deadline = time.monotonic() + EXEC_TIMEOUT
    while time.monotonic() < deadline:
        state = machine_exec(f"test ! -f {status} || cat {status}").strip()
        if state:
            try:
                exit_code = int(state)
            except ValueError:
                raise RuntimeError("archive extraction returned an unreadable status") from None
            if exit_code != 0:
                raise RuntimeError("archive extraction failed: " + machine_exec(f"tail -c 800 {log}"))
            return
        time.sleep(2)
    raise RuntimeError("archive extraction outcome is uncertain; inspect its status before retrying")


def put_archive(archive, remote_archive, digest):
    """Bounded recovery of one staging upload, never of a catalogue publication.

    A lost SFTP acknowledgement is reconciled by a read-only remote hash.
    Retrying sends the same bytes to the same task-owned archive path. No
    extraction starts here, and failed recovery leaves the stage intact.
    """
    for attempt in range(1, MAXIMUM_UPLOAD_ATTEMPTS + 1):
        try:
            fly("ssh", "sftp", "put", str(archive), remote_archive,
                "--machine", MACHINE, "--app", APP, timeout=EXEC_TIMEOUT)
            return
        except RuntimeError:
            try:
                measured = machine_exec(f"test ! -f {remote_archive} || sha256sum {remote_archive}").split()
            except RuntimeError:
                measured = []
            if measured and measured[0] == digest:
                return
            if attempt == MAXIMUM_UPLOAD_ATTEMPTS:
                raise
            print(f"  staging upload acknowledgement not confirmed; retry {attempt + 1}/{MAXIMUM_UPLOAD_ATTEMPTS}", flush=True)
            time.sleep(2 * attempt)


def upload_missing(bundle: Path, missing: list[str], remote: str, extra_paths=(), *, workers=1, compress=False) -> None:
    """Put the missing blobs into the remote release folder, then prove every one arrived whole.

    Each put carries a checksum-verified archive of blobs at their relative paths. Extraction is detached
    and polled, so it is not bounded by the Machines API's short exec response window.
    Afterwards the digests present under the release folder are read back
    and compared: a put that was cut short is a failure here, not a body that fails a customer's
    download later.
    """
    if type(workers) is not int or not 1 <= workers <= MAXIMUM_UPLOAD_WORKERS or type(compress) is not bool:
        raise ValueError("upload workers are 1 to 4 and compression is an explicit Boolean")
    extra_paths = list(extra_paths)
    extra_groups = {}
    for relative in extra_paths:
        match = re.fullmatch(r"(segments|items)/sha256/([0-9a-f]{2})/([0-9a-f]{64})", relative)
        if match is None or match[2] != match[3][:2]:
            raise ValueError("a segmented upload must name an exact item or segment digest path")
        extra_groups.setdefault(match[1], []).append(match[3])
    if not missing and not extra_paths:
        return
    sizes = {path.name: path.stat().st_size
             for path in (bundle / "blobs" / "sha256").glob("*/*") if path.is_file()}
    sizes.update({relative: (bundle / relative).stat().st_size for relative in extra_paths})
    groups = group_batches(list(missing) + extra_paths, sizes)
    def send(number, group):
        # Each transfer owns its stage, archive and remote receipt. A failed
        # worker cannot delete or replace another worker's local files.
        with tempfile.TemporaryDirectory(prefix="catalogue-delta-") as temporary:
            workdir = Path(temporary)
            stage = stage_batch(bundle, group, workdir)
            suffix = ".tar.gz" if compress else ".tar"
            # Unique archive names also separate a resumed run from old receipts.
            archive = workdir / f"batch-{number}-{uuid.uuid4().hex[:12]}{suffix}"
            options = {"compresslevel": 1} if compress else {}
            with tarfile.open(archive, "w:gz" if compress else "w", **options) as stream:
                for name in group:
                    relative = name if "/" in name else blob_path(name)
                    stream.add(stage / relative, arcname=relative, recursive=False)
            remote_archive = f"{REMOTE_ROOT}/{remote}/{archive.name}"
            archive_digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            put_archive(archive, remote_archive, archive_digest)
            extract_archive(remote_archive, archive_digest,
                            f"{REMOTE_ROOT}/{remote}")
            return {"number": number, "objects": len(group), "archive_bytes": archive.stat().st_size,
                    "payload_bytes": sum(sizes.get(name, 0) for name in group)}
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="catalogue-upload") as pool:
        futures = [pool.submit(send, number, group) for number, group in enumerate(groups, 1)]
        try:
            for completed, future in enumerate(as_completed(futures), 1):
                result = future.result()
                print(f"  batch {completed}/{len(groups)} complete (batch {result['number']}): "
                      f"{result['objects']} objects, {result['payload_bytes'] // 1024} KiB payload, "
                      f"{result['archive_bytes'] // 1024} KiB transfer", flush=True)
        except BaseException:
            for future in futures:
                future.cancel()
            # Started transfers finish before the failure returns; their
            # receipts can then be reconciled without another writer racing.
            raise
    absent = absent_blobs(remote, missing)
    if absent:
        raise RuntimeError(f"{len(absent)} blobs did not arrive, so nothing was published: {absent[:5]}")
    for kind, expected in sorted(extra_groups.items()):
        absent = absent_blobs(remote, expected, kind=kind)
        if absent:
            raise RuntimeError(f"{len(absent)} {kind} did not arrive, so nothing was published: {absent[:5]}")


def _names_digest(names) -> str:
    """SHA-256 of names sorted bytewise, one per line, as `find | LC_ALL=C sort | sha256sum` prints it."""
    return hashlib.sha256("".join(f"{name}\n" for name in sorted(names)).encode()).hexdigest()


def bind_staging(remote, context, *, resume=False, adopt_unmarked=False):
    """Bind a transfer folder before any upload; never resume a dispatched publication.

    An old unmarked folder needs an explicit adoption after the operator has
    stopped its prior uploader and reconciled its outcome. This is transfer
    recovery only; the exact native publication and its checks are unchanged.
    """
    folder = f"{REMOTE_ROOT}/{remote}"
    state = machine_exec(f"if test -e {folder}/publish-result.json; then echo {STAGING_DISPATCHED}; "
                         f"elif test -f {folder}/{STAGING_CONTEXT}; then head -c 8193 {folder}/{STAGING_CONTEXT}; "
                         f"else echo {STAGING_UNBOUND}; fi")
    if state == STAGING_DISPATCHED:
        raise RuntimeError("publication was already dispatched; reconcile its result and active pointer before recovery")
    if state != STAGING_UNBOUND:
        try:
            held = json.loads(state)
        except ValueError:
            raise RuntimeError("staging context is unreadable; nothing was uploaded") from None
        if held != context:
            raise RuntimeError("staging belongs to another exact publication; nothing was uploaded")
        return
    if resume and not adopt_unmarked:
        raise RuntimeError("unmarked staging requires explicit adoption after the previous uploader has stopped")
    with tempfile.TemporaryDirectory(prefix="catalogue-staging-") as temporary:
        marker = Path(temporary) / STAGING_CONTEXT
        marker.write_text(json.dumps(context, sort_keys=True) + "\n", encoding="utf-8")
        fly("ssh", "sftp", "put", str(marker), f"{folder}/{STAGING_CONTEXT}", "--machine", MACHINE, "--app", APP)
        measured = machine_exec(f"sha256sum {folder}/{STAGING_CONTEXT}").split()
        if not measured or measured[0] != hashlib.sha256(marker.read_bytes()).hexdigest():
            raise RuntimeError("staging context upload did not verify; nothing was published")


def remaining_uploads(remote, missing, extra_paths):
    """Use staged names only as a transfer optimization; native publication still verifies every body."""
    remaining = absent_blobs(remote, missing)
    extras = []
    for kind in (SEGMENT_OBJECT, ITEM_OBJECT):
        selected = [path for path in extra_paths if path.startswith(kind + "/")]
        absent = set(absent_blobs(remote, [path.rsplit("/", 1)[-1] for path in selected], kind=kind))
        extras.extend(path for path in selected if path.rsplit("/", 1)[-1] in absent)
    return remaining, extras


def absent_blobs(remote: str, expected: list[str], *, kind: str = BLOB_OBJECT) -> list[str]:
    """The expected digests that are not in the remote release folder, read back in bounded pieces.

    One command prints a line per two-character prefix folder: the prefix, its number of files and the
    SHA-256 of their sorted names. Only a prefix whose line differs from the expected one is listed in
    full. On October 5, 2026 the earlier single listing of all 61,205 uploaded names exceeded the Machines
    API's 10 MiB exec response limit after every batch had landed, so a correct upload could not be
    confirmed. This answer stays near 256 short lines at any release size.
    """
    if kind not in UPLOAD_OBJECT_KINDS:
        raise ValueError("an upload has a declared object kind")
    if not expected:
        return []
    folder = f"{REMOTE_ROOT}/{remote}/{kind}/sha256"
    groups: dict[str, list[str]] = {}
    for digest in expected:
        groups.setdefault(digest[:2], []).append(digest)
    summary = machine_exec(
        f"cd {folder} 2>/dev/null || exit 0; for d in ??; do [ -d \"$d\" ] || continue; "
        f"n=$(find \"$d\" -maxdepth 1 -type f | wc -l); "
        f"h=$(find \"$d\" -maxdepth 1 -type f -printf '%f\\n' | LC_ALL=C sort | sha256sum | cut -c1-64); "
        f"echo \"$d $n $h\"; done")
    if not summary:
        # An empty kind has no prefixes to inspect. Avoid 256 identical empty
        # remote calls during recovery of a transfer still uploading bodies.
        return list(expected)
    seen = {}
    for line in summary.splitlines():
        parts = line.split()
        if len(parts) == 3:
            seen[parts[0]] = (parts[1], parts[2])
    absent = []
    for prefix, names in sorted(groups.items()):
        if seen.get(prefix) == (str(len(names)), _names_digest(names)):
            continue
        listing = machine_exec(f"[ -d {folder}/{prefix} ] && find {folder}/{prefix} -maxdepth 1 -type f "
                               f"-printf '%f\\n' || true")
        present = {name.strip() for name in listing.splitlines()}
        absent.extend(name for name in names if name not in present)
    return absent


def active_catalogue() -> dict:
    """Bounded public metadata only. A failed/unknown view grants nothing."""
    try:
        root = Path(__file__).resolve().parents[1]
        hostname = json.loads((root / "src/loop_engine/core/service_runtime/web_site_map.json").read_text())["canonical_hostname"]
        address = urlunsplit(("https", hostname, "/api/v1/health", "", ""))
        with urlopen(address, timeout=15) as response:
            raw = response.read(128 * 1024 + 1)
        if len(raw) > 128 * 1024:
            return {}
        view = json.loads(raw)["result"]["catalogue_release"]
        return view if isinstance(view, dict) else {}
    except (OSError, ValueError, KeyError):
        return {}


def active_release() -> str:
    """Current pointer observation; success also needs our exact result and header digest."""
    identifier = active_catalogue().get("release_id")
    return identifier if isinstance(identifier, str) and re.fullmatch(r"[0-9a-f]{64}", identifier) else ""


def base_digests(folder: Path) -> set[str]:
    """An earlier validated bundle supplies an upload optimization, never publication authority.

    The service rechecks every referenced body before activation. Missing or
    incorrect prior inventory therefore refuses publication rather than
    publishing partial content. Hash the inventory before trusting its names.
    """
    header = json.loads((folder / "bundle.json").read_bytes())
    inventory = (folder / "items.jsonl").read_bytes()
    if hashlib.sha256(inventory).hexdigest() != header["items_digest"]:
        raise ValueError("the base bundle inventory does not match its header")
    rows = [json.loads(line) for line in inventory.splitlines()]
    if len(rows) != header["items"]:
        raise ValueError("the base bundle population differs from its header")
    return {file["digest"] for row in rows for file in row["package"]["files"]}


def publication_inputs(bundle, digest, base_bundle, base_release, reconciliation_digest, body_roots, accepted_licenses,
                       *, verify_local_bodies=True):
    """Validate exact metadata and preservation before effects.

    Initial/adopted transfers also recheck all local bytes. Only recovery of
    an exactly bound stage reuses that earlier local-byte check. Complete
    native byte verification before activation is never optional.
    """
    from reconcile_catalogue_bundle import (PROOF_FILE, check_proof, load_bundle, read_control, verify_files)
    if (base_bundle is None or not isinstance(base_release, str) or not re.fullmatch(r"[0-9a-f]{64}", base_release)
            or not isinstance(reconciliation_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", reconciliation_digest)):
        raise ValueError("a current base bundle/release and exact reconciliation digest are required")
    raw, proof = read_control(bundle / PROOF_FILE)
    if hashlib.sha256(raw).hexdigest() != reconciliation_digest:
        raise ValueError("reconciliation proof differs from its expected digest")
    base, candidate = (load_bundle(Path(folder), accepted_licenses) for folder in (base_bundle, bundle))
    if candidate.digest != digest:
        raise ValueError("the expected bundle digest must match the local header before upload")
    changes = check_proof(base, candidate, proof)
    if changes.base_release != base_release:
        raise ValueError("publication and build name different base releases")
    if verify_local_bodies:
        held = verify_files(base, body_roots)
        roots = tuple(root for root in (base.folder / "blobs", *body_roots) if Path(root).is_dir())
        verify_files(candidate, roots)
    else:
        # Only the exact marked recovery path selects this mode. That stage
        # was bound after the full local check; metadata/proof checks above
        # still rerun. Native publication always verifies the complete bytes
        # before activation, including objects reused from this transfer.
        held = {file.digest for item in base.items for file in item.package.files}
    return base, changes, proof, set(held)


def publish(name: str, bundle: Path, digest: str, *, base_bundle: Path | None = None,
            base_release: str | None = None, reconciliation_digest: str | None = None,
            body_roots=(), accepted_licenses=("MIT",), upload_workers=1, compress=False,
            resume_staging=None, adopt_unmarked_staging=False) -> dict:
    """Upload what is missing, write the release folder, and move the pointer by the ordinary command."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}", name):
        raise ValueError("a release name must be one safe path segment")
    if type(upload_workers) is not int or not 1 <= upload_workers <= MAXIMUM_UPLOAD_WORKERS or type(compress) is not bool:
        raise ValueError("upload workers are 1 to 4 and compression is an explicit Boolean")
    if resume_staging is not None and (not isinstance(resume_staging, str)
            or not re.fullmatch(r"delta-" + re.escape(name) + r"-[0-9a-f]{12}", resume_staging)):
        raise ValueError("resume names one exact staging folder for this publication name")
    if type(adopt_unmarked_staging) is not bool or adopt_unmarked_staging and resume_staging is None:
        raise ValueError("adoption needs one explicit previous staging folder")
    if not re.fullmatch(r"[0-9a-f]{64}", digest) or hashlib.sha256((bundle / "bundle.json").read_bytes()).hexdigest() != digest:
        raise ValueError("the expected bundle digest must match the local header before upload")
    from reconcile_catalogue_bundle import load_bundle, require_live_base
    from loop_engine.core.service_runtime.catalogue_segments import bundle_record_type, negotiate_bundle_format
    reuse_local_verification = bool(resume_staging and not adopt_unmarked_staging)
    base, changes, proof, present = publication_inputs(bundle, digest, base_bundle, base_release,
        reconciliation_digest, body_roots, accepted_licenses, verify_local_bodies=not reuse_local_verification)
    require_live_base(base, changes, active_catalogue())
    # The service must read this bundle's version; this read changes nothing on the Machine.
    record_type = bundle_record_type(bundle)
    negotiate_bundle_format(remote_formats(), preference=(record_type,))
    candidate = load_bundle(bundle, accepted_licenses)
    extra_paths = segmented_uploads(base, candidate)
    remote = resume_staging or f"delta-{name}-{uuid.uuid4().hex[:12]}"
    result_path = f"{REMOTE_ROOT}/{remote}/publish-result.json"
    kept_receipt = f"{REMOTE_ROOT}/{remote}.publish.json"
    machine_exec(f"mkdir -p {REMOTE_ROOT}/{remote}/blobs/sha256")
    if resume_staging:
        context = {"record_type": "catalogue_upload_staging/v1", "name": name, "bundle_digest": digest,
                   "base_release": base_release, "reconciliation_digest": reconciliation_digest,
                   "result_release": proof["result_release"], "result_content_digest": proof["result_content_digest"]}
        bind_staging(remote, context, resume=True, adopt_unmarked=adopt_unmarked_staging)

    local = blob_digests(bundle)
    sizes = {path.name: path.stat().st_size
             for path in (bundle / "blobs" / "sha256").glob("*/*") if path.is_file()}
    missing = [value for value in local if value not in present]
    resumed_bodies, resumed_metadata = 0, 0
    if resume_staging:
        rest, extra_rest = remaining_uploads(remote, missing, extra_paths)
        resumed_bodies, resumed_metadata = len(missing) - len(rest), len(extra_paths) - len(extra_rest)
        missing, extra_paths = rest, extra_rest
    total_bytes = sum(sizes.values())
    missing_bytes = sum(sizes[value] for value in missing)
    plan = {"release": remote, "local_blobs": len(local),
            "already_present": len(local) - len(missing), "uploading": len(missing),
            "bundle_bytes": total_bytes, "upload_bytes": missing_bytes,
            "share_of_full_upload": round(missing_bytes / total_bytes, 4) if total_bytes else None,
            "batches": len(group_batches(missing, sizes)), "base_release": base_release,
            "reconciliation_digest": reconciliation_digest, "bundle_record_type": record_type,
            "segments_and_item_lines": len(extra_paths), "resumed_staged_bodies": resumed_bodies,
            "resumed_staged_metadata": resumed_metadata, "upload_workers": upload_workers, "compressed": compress,
            "local_body_verification": "reused_exact_marked_stage" if reuse_local_verification else "fresh_full_check",
            "native_complete_byte_verification": "required_before_activation"}
    print(json.dumps(plan, indent=2), flush=True)
    # A declared withdrawal-only/no-op snapshot can have no new local blobs.
    if extra_paths:
        upload_missing(bundle, missing, remote, extra_paths, workers=upload_workers, compress=compress)
    else:
        upload_missing(bundle, missing, remote, workers=upload_workers, compress=compress)
    listing = "release-segments.jsonl" if extra_paths or (bundle / "release-segments.jsonl").exists() else "items.jsonl"
    for filename in ("bundle.json", listing):
        fly("ssh", "sftp", "put", str(bundle / filename), f"{REMOTE_ROOT}/{remote}/{filename}",
            "--machine", MACHINE, "--app", APP, timeout=EXEC_TIMEOUT)
    # Payloads are readable; only the receipt's containing directory needs service ownership.
    machine_exec(f"chown 65534:65534 {REMOTE_ROOT}/{remote}", timeout=60)

    require_live_base(base, changes, active_catalogue())
    before = base_release
    machine_exec(
        f"{AS_SERVICE} sh -c 'nohup loop-engine service publish-catalogue --config /data/host.json "
        f"--bundle {REMOTE_ROOT}/{remote} --expected-bundle-digest {digest} --expected-release {before} "
        f"> {result_path} 2>&1 &'", as_service=True, timeout=120)

    deadline = time.monotonic() + POINTER_WAIT_SECONDS
    minute = 0
    while time.monotonic() < deadline:
        time.sleep(60)
        minute += 1
        observed = active_catalogue()
        now = observed.get("release_id", "")
        if now:
            try:
                receipt = json.loads(machine_exec(f"tail -c 8192 {result_path}", timeout=60))
                result = receipt.get("result", receipt)
            except (RuntimeError, ValueError):
                result = {}
            if (result.get("release_id") == now == proof["result_release"]
                    and result.get("content_digest") == observed.get("content_digest") == proof["result_content_digest"]
                    and result.get("bundle_digest") == digest):
                # Keep the receipt. Only this completed, identified staging folder is disposable.
                machine_exec(f"cp {result_path} {kept_receipt}", timeout=60)
                machine_exec(f"rm -r {REMOTE_ROOT}/{remote}", timeout=300)
                return {"published": True, "active_release_id": now, "waited_minutes": minute,
                        "receipt": kept_receipt, "bundle_digest": digest,
                        "content_digest": proof["result_content_digest"], **plan}
        try:
            refused = machine_exec(
                f"grep -q '\\\"refused\\\": true\\|Error\\|Traceback' {result_path} "
                f"&& head -c 1200 {result_path}", timeout=60)
        except RuntimeError:
            refused = ""
        if refused:
            raise RuntimeError(f"the publish refused:\n{refused}")
        print(f"  publishing, minute {minute} (active still {before[:12]})", flush=True)
    raise RuntimeError("the expected release was not confirmed before the wait deadline; inspect its receipt "
                       "and active state before retrying the uncertain publication")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("name")
    parser.add_argument("bundle_folder", type=Path)
    parser.add_argument("bundle_digest")
    parser.add_argument("--base-bundle", type=Path,
                        help="previous validated bundle inventory; avoids scanning the remote volume")
    parser.add_argument("--base-release", help="the active release represented by the base bundle")
    parser.add_argument("--reconciliation-digest", help="SHA-256 of the exact private reconciliation.json proof")
    parser.add_argument("--body-root", action="append", type=Path, default=[],
                        help="Explicit read-only blob root (holding sha256/) for a delta-only baseline")
    parser.add_argument("--accept-license", action="append", default=[], help="Repeat the host's accepted licence labels")
    parser.add_argument("--dry-run", action="store_true",
                        help="report the delta and write nothing")
    parser.add_argument("--upload-workers", type=int, default=1, choices=range(1, MAXIMUM_UPLOAD_WORKERS + 1))
    parser.add_argument("--compress", action="store_true", help="gzip transfer archives; catalogue bytes do not change")
    parser.add_argument("--resume-staging", help="resume one exact stopped transfer; a dispatched publication refuses")
    parser.add_argument("--adopt-unmarked-staging", action="store_true",
                        help="bind an older unmarked transfer only after its uploader has stopped and been reconciled")
    arguments = parser.parse_args()
    bundle = arguments.bundle_folder
    segmented = (bundle / "release-segments.jsonl").exists()
    for required in (("bundle.json", "release-segments.jsonl") if segmented else ("bundle.json", "items.jsonl", "blobs")):
        if not (bundle / required).exists():
            print(f"the bundle folder has no {required}", file=sys.stderr)
            return 2
    if arguments.dry_run:
        try:
            from reconcile_catalogue_bundle import load_bundle
            licences = tuple(arguments.accept_license) or ("MIT",)
            _base, _changes, _proof, present = publication_inputs(bundle, arguments.bundle_digest,
                arguments.base_bundle, arguments.base_release, arguments.reconciliation_digest,
                tuple(arguments.body_root), licences)
            extra_paths = segmented_uploads(_base, load_bundle(bundle, licences))
        except (OSError, ValueError, RuntimeError) as error:
            print(f"the delta plan refused: {error}", file=sys.stderr)
            return 1
        local = blob_digests(bundle)
        sizes = {path.name: path.stat().st_size
                 for path in (bundle / "blobs" / "sha256").glob("*/*") if path.is_file()}
        missing = [value for value in local if value not in present]
        total = sum(sizes.values())
        print(json.dumps({"local_blobs": len(local), "already_present": len(local) - len(missing),
                          "uploading": len(missing), "bundle_bytes": total,
                          "segments_and_item_lines": len(extra_paths),
                          "segments_and_item_line_bytes": sum((bundle / path).stat().st_size for path in extra_paths),
                          "upload_bytes": sum(sizes[value] for value in missing),
                          "share_of_full_upload": round(sum(sizes[v] for v in missing) / total, 4) if total else None,
                          "batches": len(group_batches(missing, sizes))}, indent=2))
        return 0
    try:
        print(json.dumps(publish(arguments.name, bundle, arguments.bundle_digest,
                                 base_bundle=arguments.base_bundle, base_release=arguments.base_release,
                                 reconciliation_digest=arguments.reconciliation_digest,
                                 body_roots=tuple(arguments.body_root),
                                 accepted_licenses=tuple(arguments.accept_license) or ("MIT",),
                                 upload_workers=arguments.upload_workers, compress=arguments.compress,
                                 resume_staging=arguments.resume_staging,
                                 adopt_unmarked_staging=arguments.adopt_unmarked_staging), indent=2))
    except (OSError, ValueError, RuntimeError) as error:
        print(f"the delta publish failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
