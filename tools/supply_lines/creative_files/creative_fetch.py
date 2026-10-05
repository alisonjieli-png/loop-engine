"""Fetch one pinned variant of a Baltor creative package and keep only the exact recorded bytes.

creative.json beside this file (creative_asset_manifest/v1) names the asset or project, its licence and, for
each variant (a resolution and format of one asset, or the media files of an editable project), every file's
exact download address, byte size and SHA-256. Nothing large is re-hosted: the bytes come from the origin the
manifest names, and this module keeps a file only when its size and digest are the recorded ones.

    python creative_fetch.py list                          the variants, their files and sizes
    python creative_fetch.py fetch [VARIANT] [FOLDER]      one variant into FOLDER (default variant, folder .)
    python creative_fetch.py check                         the manifest's own shape

What is refused, always before anything is written in place:

- an address that is not HTTPS on a host the manifest lists (plain HTTP to the loopback address only when the
  caller allows it, for tests and local mirrors), and a redirect to anywhere else;
- a placement path that is absolute, holds a parent step or a backslash, or otherwise leaves the folder;
- more bytes than recorded, fewer bytes, or other bytes (a SHA-256 mismatch): the partial file is removed;
- an archive whose members differ from the recorded members, or a member that is a link or has other bytes.

A file already in place with the recorded digest is kept as it is, so a second fetch downloads nothing.
Standard library only; Python 3.10 or later.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile

MANIFEST_NAME = "creative.json"
RECORD_TYPE = "creative_asset_manifest/v1"
USER_AGENT = "baltor-creative-fetch/1"
CHUNK_BYTES = 1024 * 1024
MAXIMUM_REDIRECTS = 5
LOOPBACK_HOSTS = ("127.0.0.1", "::1", "localhost")
ASSET_TYPES = ("hdri", "texture", "material", "model", "godot_project")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_SYMBOLIC_LINK = 0o120000


class FetchError(Exception):
    """A refused fetch, with a stable code; nothing the refusal concerns is left in place."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def load_manifest(path=None) -> dict:
    """The manifest beside this module (or at ``path``), refused when it is not a creative_asset_manifest/v1."""
    path = Path(path) if path else Path(__file__).resolve().parent / MANIFEST_NAME
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise FetchError("manifest_unreadable", f"{path}: {type(error).__name__}") from None
    if not isinstance(manifest, dict) or manifest.get("record_type") != RECORD_TYPE:
        raise FetchError("manifest_unreadable", f"{path} is not a {RECORD_TYPE}")
    return manifest


def placement(folder, relative: str) -> Path:
    """The path of a file inside ``folder``; refuse one that is absolute, has a parent step or leaves it."""
    text = str(relative)
    if not text or "\\" in text or "\x00" in text or text.startswith("/") or re.match(r"[A-Za-z]:", text):
        raise FetchError("placement_unsafe", repr(text[:120]))
    parts = PurePosixPath(text).parts
    if any(part in ("", ".", "..") for part in parts):
        raise FetchError("placement_unsafe", repr(text[:120]))
    base = Path(folder).resolve()
    target = base.joinpath(*parts)
    if os.path.commonpath([str(base), str(target.resolve())]) != str(base):
        raise FetchError("placement_unsafe", f"{text[:120]} leaves {base}")
    return target


def check_address(url: str, hosts=(), *, allow_loopback: bool = False) -> str:
    """The address when it is HTTPS on a listed host, or plain HTTP to the loopback address when allowed."""
    parts = urllib.parse.urlsplit(str(url))
    if parts.scheme == "https" and parts.hostname and parts.hostname in set(hosts):
        return str(url)
    if allow_loopback and parts.scheme in ("http", "https") and parts.hostname in LOOPBACK_HOSTS:
        return str(url)
    raise FetchError("address_refused", f"{str(url)[:160]} is not HTTPS on a listed host")


def _file_problems(row, where: str) -> list:
    problems = []
    if not isinstance(row, dict):
        return [f"{where} is not an object"]
    try:
        placement(".", row.get("path", ""))
    except FetchError as error:
        problems.append(f"{where}: {error}")
    size = row.get("size_bytes")
    if type(size) is not int or size < 0:
        problems.append(f"{where}: size_bytes is not a whole number of bytes")
    if not _DIGEST.match(str(row.get("sha256", ""))):
        problems.append(f"{where}: sha256 is not 64 lowercase hexadecimal digits")
    return problems


def manifest_problems(manifest, *, allow_loopback: bool = False) -> list:
    """What makes a manifest unusable: its record type, job, asset type, hosts and every pinned file."""
    if not isinstance(manifest, dict) or manifest.get("record_type") != RECORD_TYPE:
        return [f"not a {RECORD_TYPE}"]
    problems = []
    job = manifest.get("job")
    if not isinstance(job, dict) or not all(isinstance(job.get(name), str) and job.get(name)
                                            for name in ("source", "identity")):
        problems.append("job names no source and identity")
    if (manifest.get("asset") or {}).get("type") not in ASSET_TYPES:
        problems.append(f"the asset type is not one of {ASSET_TYPES}")
    hosts = manifest.get("hosts")
    if not isinstance(hosts, list) or not all(isinstance(host, str) and host for host in hosts):
        problems.append("hosts is not a list of host names")
        hosts = []
    variants = manifest.get("variants")
    if not isinstance(variants, list):
        return problems + ["variants is not a list"]
    seen = set()
    for index, row in enumerate(variants):
        identifier = row.get("id") if isinstance(row, dict) else None
        if not isinstance(identifier, str) or not identifier or identifier in seen:
            problems.append(f"variant {index} has no distinct id")
            continue
        seen.add(identifier)
        files = row.get("files")
        if not isinstance(files, list) or not files:
            problems.append(f"{identifier}: no files")
            continue
        for number, item in enumerate(files):
            where = f"{identifier} file {number}"
            problems += _file_problems(item, where)
            try:
                check_address(item.get("url", "") if isinstance(item, dict) else "", hosts,
                              allow_loopback=allow_loopback)
            except FetchError as error:
                problems.append(f"{where}: {error}")
            for position, member in enumerate((item.get("members") or []) if isinstance(item, dict) else []):
                problems += _file_problems(member, f"{where} member {position}")
            if isinstance(item, dict) and item.get("unpack") and not item.get("members"):
                problems.append(f"{where}: an archive to unpack lists no members")
        total = sum(item.get("size_bytes", 0) for item in files if isinstance(item, dict)
                    and type(item.get("size_bytes")) is int)
        if row.get("total_bytes") != total:
            problems.append(f"{identifier}: total_bytes is not the sum of its files")
    default = manifest.get("default_variant")
    if (variants and default not in seen) or (not variants and default is not None):
        problems.append("the default variant is not one of the variants")
    return problems


def variant(manifest: dict, identifier: "str | None" = None) -> dict:
    """One variant by its id, or the manifest's default variant; refuse an id the manifest does not list."""
    wanted = identifier or manifest.get("default_variant")
    for row in manifest.get("variants") or ():
        if row.get("id") == wanted:
            return row
    known = ", ".join(row.get("id", "?") for row in manifest.get("variants") or ()) or "none"
    raise FetchError("variant_unknown", f"{wanted!r} is not a variant of this package (variants: {known})")


def file_matches(path, size: int, sha256: str) -> bool:
    """Whether a file exists with exactly the recorded size and SHA-256."""
    path = Path(path)
    if not path.is_file() or path.stat().st_size != size:
        return False
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest() == sha256


class _ListedRedirects(urllib.request.HTTPRedirectHandler):
    """Follow a redirect only to an address check_address admits, at most MAXIMUM_REDIRECTS times."""

    max_redirections = MAXIMUM_REDIRECTS

    def __init__(self, hosts, allow_loopback: bool) -> None:
        super().__init__()
        self.hosts, self.allow_loopback = tuple(hosts), allow_loopback

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        try:
            check_address(newurl, self.hosts, allow_loopback=self.allow_loopback)
        except FetchError as error:
            fp.close()
            raise urllib.error.HTTPError(newurl, code, str(error), headers, None) from None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def opener(hosts=(), *, allow_loopback: bool = False, proxies: "dict | None" = None):
    """The URL opener a fetch uses: redirects checked, proxies from the environment unless ``proxies`` is given
    (an empty mapping sends every request directly, as a test against the loopback address needs)."""
    handlers = [_ListedRedirects(hosts, allow_loopback)]
    if proxies is not None:
        handlers.insert(0, urllib.request.ProxyHandler(proxies))
    return urllib.request.build_opener(*handlers)


def _streamed(source, temporary: Path, size: int, label: str) -> str:
    """Copy at most ``size`` bytes from ``source`` into ``temporary``; the SHA-256, or refuse a size mismatch."""
    digest, count = hashlib.sha256(), 0
    with open(temporary, "wb") as stream:
        while True:
            chunk = source.read(CHUNK_BYTES)
            if not chunk:
                break
            count += len(chunk)
            if count > size:
                raise FetchError("size_mismatch", f"{label} sent more than the recorded {size} bytes")
            digest.update(chunk)
            stream.write(chunk)
    if count != size:
        raise FetchError("size_mismatch", f"{label} sent {count} bytes, not the recorded {size}")
    return digest.hexdigest()


def _temporary_beside(target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=".fetch-", suffix=".partial", dir=target.parent)
    os.close(handle)
    return Path(name)


def download(url: str, target, *, size: int, sha256: str, hosts=(), allow_loopback: bool = False,
             open_url=None, timeout: float = 60.0) -> Path:
    """Download one file into ``target`` and keep it only with the recorded size and SHA-256."""
    check_address(url, hosts, allow_loopback=allow_loopback)
    target = Path(target)
    if file_matches(target, size, sha256):
        return target
    temporary = _temporary_beside(target)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    try:
        open_url = open_url or opener(hosts, allow_loopback=allow_loopback).open
        with open_url(request, timeout=timeout) as answer:
            status = getattr(answer, "status", 200)
            if status != 200:
                raise FetchError("download_failed", f"{url[:160]} answered {status}")
            length = (answer.headers or {}).get("Content-Length") if hasattr(answer, "headers") else None
            if length is not None and str(length).isdigit() and int(length) != size:
                raise FetchError("size_mismatch", f"{url[:160]} announces {length} bytes, not the recorded {size}")
            found = _streamed(answer, temporary, size, url[:160])
        if found != sha256:
            raise FetchError("digest_mismatch", f"{url[:160]} has SHA-256 {found}, not the recorded {sha256}")
        os.replace(temporary, target)
        return target
    except urllib.error.HTTPError as error:
        error.close()
        code = "address_refused" if "address_refused" in str(error.msg) else "download_failed"
        raise FetchError(code, f"{url[:160]}: {error.code} {error.msg}"[:300]) from None
    except (urllib.error.URLError, OSError) as error:
        raise FetchError("download_failed", f"{url[:160]}: {error}"[:300]) from None
    finally:
        if temporary.exists():
            temporary.unlink()


def unpack(archive, folder, members) -> list:
    """Extract exactly the recorded members of a verified archive into ``folder``, each checked by SHA-256."""
    recorded = {member["path"]: member for member in members}
    written = []
    with zipfile.ZipFile(archive) as opened:
        entries = [entry for entry in opened.infolist() if not entry.is_dir()]
        names = sorted(entry.filename for entry in entries)
        if names != sorted(recorded):
            raise FetchError("archive_members_differ", f"{Path(archive).name} holds {len(names)} files, "
                                                       f"{len(recorded)} recorded")
        for entry in entries:
            if (entry.external_attr >> 16) & 0o170000 == _SYMBOLIC_LINK:
                raise FetchError("archive_member_unsafe", f"{entry.filename} is a link")
            expected = recorded[entry.filename]
            target = placement(folder, entry.filename)
            if entry.file_size != expected["size_bytes"]:
                raise FetchError("size_mismatch", f"{entry.filename} is {entry.file_size} bytes, not the recorded "
                                                  f"{expected['size_bytes']}")
            if not file_matches(target, expected["size_bytes"], expected["sha256"]):
                temporary = _temporary_beside(target)
                try:
                    with opened.open(entry) as source:
                        found = _streamed(source, temporary, expected["size_bytes"], entry.filename)
                    if found != expected["sha256"]:
                        raise FetchError("digest_mismatch", f"{entry.filename} has SHA-256 {found}, not the "
                                                            f"recorded {expected['sha256']}")
                    os.replace(temporary, target)
                finally:
                    if temporary.exists():
                        temporary.unlink()
            written.append(target)
    return written


def fetch(identifier: "str | None" = None, folder=".", *, manifest: "dict | None" = None,
          allow_loopback: bool = False, open_url=None, timeout: float = 60.0, keep_archives: bool = True) -> list:
    """Fetch every file of one variant into ``folder`` and return the paths now in place.

    Every placement and address is checked before the first request, so a refused variant writes nothing."""
    manifest = manifest if manifest is not None else load_manifest()
    problems = manifest_problems(manifest, allow_loopback=allow_loopback)
    if problems:
        raise FetchError("manifest_invalid", "; ".join(problems[:3]))
    chosen = variant(manifest, identifier)
    hosts = manifest["hosts"]
    for item in chosen["files"]:
        placement(folder, item["path"])
        check_address(item["url"], hosts, allow_loopback=allow_loopback)
        for member in item.get("members") or ():
            placement(folder, member["path"])
    written = []
    for item in chosen["files"]:
        members = item.get("members") or []
        if item.get("unpack") and all(file_matches(placement(folder, member["path"]), member["size_bytes"],
                                                   member["sha256"]) for member in members):
            written += [placement(folder, member["path"]) for member in members]
            continue
        target = download(item["url"], placement(folder, item["path"]), size=item["size_bytes"],
                          sha256=item["sha256"], hosts=hosts, allow_loopback=allow_loopback, open_url=open_url,
                          timeout=timeout)
        if item.get("unpack"):
            written += unpack(target, folder, members)
            if not keep_archives:
                target.unlink()
                continue
        written.append(target)
    return written


def describe(manifest: dict) -> str:
    """The variants as text: id, total size, file count and the main file."""
    lines = [f"{manifest['asset'].get('name', manifest['job']['identity'])} ({manifest['asset']['type']}), "
             f"licence {manifest.get('licence', {}).get('spdx', 'unknown')}"]
    for row in manifest.get("variants") or ():
        mark = " (default)" if row["id"] == manifest.get("default_variant") else ""
        lines.append(f"  {row['id']:<20} {row['total_bytes']:>13,} bytes  {len(row['files'])} files  "
                     f"{row.get('main') or ''}{mark}")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Fetch one pinned variant of this creative package.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="the variants with their sizes")
    commands.add_parser("check", help="the manifest's own shape")
    one = commands.add_parser("fetch", help="download one variant and verify every byte")
    one.add_argument("variant", nargs="?", help="a variant id (default: the manifest's default variant)")
    one.add_argument("folder", nargs="?", default=".", help="where the files go (default: this folder)")
    one.add_argument("--remove-archives", action="store_true", help="remove an archive once it is unpacked")
    arguments = parser.parse_args(argv)
    try:
        manifest = load_manifest()
        if arguments.command == "list":
            print(describe(manifest))
        elif arguments.command == "check":
            problems = manifest_problems(manifest)
            print("\n".join(problems) if problems else "the manifest pins every file by address, size and SHA-256")
            return 1 if problems else 0
        else:
            for path in fetch(arguments.variant, arguments.folder, manifest=manifest,
                              keep_archives=not arguments.remove_archives):
                print(path)
    except FetchError as error:
        print(error, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
