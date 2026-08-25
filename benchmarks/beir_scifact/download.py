#!/usr/bin/env python3
"""Download and freeze the official BEIR SciFact source archive.

This is the only benchmark step that uses the network. The benchmark runner
will not download data and will refuse a source that does not match this
manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
import urllib.request
import zipfile


SOURCE_URL = (
    "https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/"
    "datasets/scifact.zip"
)
EXPECTED_MD5 = "5f7d1de60b170fc8027bb7898e2efca1"
EXPECTED_SHA256 = (
    "536e14446a0ba56ed1398ab1055f39fe852686ecad24a6306c80c490fa8e0165"
)
REQUIRED_FILES = (
    "scifact/corpus.jsonl",
    "scifact/queries.jsonl",
    "scifact/qrels/test.tsv",
)


def _digest(path: Path, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def _verify_archive(path: Path) -> dict[str, object]:
    observed_md5 = _digest(path, "md5")
    observed_sha256 = _digest(path, "sha256")
    if observed_md5 != EXPECTED_MD5:
        raise ValueError(
            f"archive MD5 mismatch: expected {EXPECTED_MD5}, got "
            f"{observed_md5}"
        )
    if observed_sha256 != EXPECTED_SHA256:
        raise ValueError(
            f"archive SHA-256 mismatch: expected {EXPECTED_SHA256}, got "
            f"{observed_sha256}"
        )
    return {
        "url": SOURCE_URL,
        "archive_name": path.name,
        "archive_bytes": path.stat().st_size,
        "archive_md5": observed_md5,
        "archive_sha256": observed_sha256,
    }


def _safe_members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    members = archive.infolist()
    for member in members:
        name = PurePosixPath(member.filename)
        if name.is_absolute() or ".." in name.parts:
            raise ValueError(f"unsafe archive member {member.filename!r}")
        mode = member.external_attr >> 16
        if mode & 0o170000 == 0o120000:
            raise ValueError(f"symbolic link refused: {member.filename!r}")
    names = {member.filename.rstrip("/") for member in members}
    missing = [name for name in REQUIRED_FILES if name not in names]
    if missing:
        raise ValueError(f"archive is missing required files: {missing}")
    return members


def _line_count(path: Path) -> int:
    with path.open("rb") as stream:
        return sum(1 for _ in stream)


def _extracted_identity(data_root: Path) -> dict[str, dict[str, object]]:
    files: dict[str, dict[str, object]] = {}
    for relative in REQUIRED_FILES:
        path = data_root / relative
        if not path.is_file():
            raise FileNotFoundError(f"required extracted file missing: {path}")
        files[relative] = {
            "bytes": path.stat().st_size,
            "lines": _line_count(path),
            "sha256": _digest(path, "sha256"),
        }
    return files


def verify_existing_source(data_root: Path) -> dict[str, object]:
    """Verify a downloaded archive, extracted files, and their manifest."""
    data_root = data_root.resolve()
    manifest_path = data_root / "source-manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"source manifest missing at {manifest_path}; run download.py first"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("record_type") != "beir_source_manifest/v1":
        raise ValueError("source manifest has an unknown record type")
    if manifest.get("dataset") != "BEIR SciFact" or manifest.get("split") != "test":
        raise ValueError("source manifest is not BEIR SciFact test")
    archive = _verify_archive(data_root / "scifact.zip")
    files = _extracted_identity(data_root)
    if manifest.get("archive") != archive or manifest.get("files") != files:
        raise ValueError("source manifest does not match the downloaded data")
    return manifest


def download_and_extract(data_root: Path) -> dict[str, object]:
    data_root = data_root.resolve()
    data_root.mkdir(parents=True, exist_ok=True)
    archive_path = data_root / "scifact.zip"
    dataset_path = data_root / "scifact"
    manifest_path = data_root / "source-manifest.json"

    if manifest_path.exists():
        return verify_existing_source(data_root)

    if dataset_path.exists():
        raise FileExistsError(
            f"{dataset_path} exists without a verified source manifest; use "
            "a new data directory so existing data is not overwritten"
        )

    if archive_path.exists():
        archive_identity = _verify_archive(archive_path)
    else:
        part_path = data_root / "scifact.zip.part"
        if part_path.exists():
            raise FileExistsError(
                f"partial download already exists at {part_path}; inspect it "
                "before retrying"
            )
        request = urllib.request.Request(
            SOURCE_URL, headers={"User-Agent": "Loop-Engine-BEIR-SciFact/1"}
        )
        try:
            with urllib.request.urlopen(request) as response, part_path.open("wb") as out:
                for block in iter(lambda: response.read(1024 * 1024), b""):
                    out.write(block)
            archive_identity = _verify_archive(part_path)
            os.replace(part_path, archive_path)
            archive_identity["archive_name"] = archive_path.name
        except BaseException:
            if part_path.exists():
                part_path.unlink()
            raise

    with tempfile.TemporaryDirectory(
        prefix="scifact-extract-", dir=data_root
    ) as temporary:
        temporary_root = Path(temporary)
        with zipfile.ZipFile(archive_path) as archive:
            members = _safe_members(archive)
            archive.extractall(temporary_root, members=members)
        extracted = temporary_root / "scifact"
        if not extracted.is_dir():
            raise ValueError("archive did not produce the scifact directory")
        os.replace(extracted, dataset_path)

    manifest = {
        "record_type": "beir_source_manifest/v1",
        "dataset": "BEIR SciFact",
        "split": "test",
        "archive": archive_identity,
        "files": _extracted_identity(data_root),
    }
    temporary_manifest = data_root / "source-manifest.json.part"
    temporary_manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary_manifest, manifest_path)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(__file__).resolve().parent / "data",
    )
    args = parser.parse_args()
    manifest = download_and_extract(args.data_root)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
