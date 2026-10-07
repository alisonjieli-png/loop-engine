"""Compare the address ranges a forwarding proxy publishes today with the set this image pins.

The failed-attempt limit reads a forwarding proxy's client address header (Cloudflare's `CF-Connecting-IP`) only for a
request whose connecting address lies inside the proxy's pinned ranges, kept in
`src/loop_engine/data/forwarding_proxy_ranges.json` and read by `core/service_runtime/forwarding_proxy.py`. A provider
adds and retires ranges from time to time: a request from a new range would count under the edge address, and a
retired range would stay trusted. This check reads the documents the pinned set names (its own `sources`), compares
the published ranges with the pinned ones and prints one `forwarding_proxy_range_check/v1` record. On drift it also
prints a candidate set, verified by the same reader the service uses, for an engineer to review and add to the data
file in a new image. It never changes the data file, a host file or a deployment.

Network reads happen only with `--authorize-network-reads`; without it nothing is read and the command exits 2.

    PYTHONPATH=src:tools python tools/check_forwarding_proxy_ranges.py --authorize-network-reads

Exit status: 0 when the published ranges equal the pinned set, 1 on drift or when the documents disagree with each
other, 2 when the read was refused or a document could not be read.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import ipaddress
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request

REPOSITORY = Path(__file__).resolve().parents[1]
if str(REPOSITORY / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "src"))

from loop_engine.core.service_runtime.forwarding_proxy import (  # noqa: E402
    RANGE_SET_RECORD_TYPE, RANGE_SETS_RECORD_TYPE, RANGES_RESOURCE, parse_range_sets, pinned_range_sets,
    ranges_digest, read_range_sets)

RECORD_TYPE = "forwarding_proxy_range_check/v1"
USER_AGENT = "baltor-forwarding-proxy-range-check/1"
#: A published range document is a few hundred bytes; anything far larger is not the document this reads.
MAXIMUM_DOCUMENT_BYTES = 65_536
FAMILIES = (("ipv4", 4), ("ipv6", 6))
UNCHANGED, DRIFT, DISAGREE, UNREADABLE, REFUSED = "unchanged", "drift", "sources_disagree", "unreadable", "refused"
EXIT_CODES = {UNCHANGED: 0, DRIFT: 1, DISAGREE: 1, UNREADABLE: 2, REFUSED: 2}


def default_fetch(url, timeout):
    """(status, headers with lowercase names, body) of one unauthenticated read, the body bounded."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as answer:
            return answer.status, {key.lower(): value for key, value in answer.headers.items()}, \
                answer.read(MAXIMUM_DOCUMENT_BYTES + 1)
    except urllib.error.HTTPError as error:
        return error.code, {}, b""


def _networks(values, version):
    """The canonical form of each published range of one family, in published order; refused when one is not."""
    found = []
    for value in values:
        network = ipaddress.ip_network(value.strip(), strict=True)
        if network.version != version:
            raise ValueError(f"a range of another family: {value!r}")
        found.append(str(network))
    return found


def ranges_of(body):
    """The families one document publishes: the JSON interface lists both, each text list one family."""
    text = body.decode("utf-8")
    try:
        document = json.loads(text)
    except ValueError:
        document = None
    if isinstance(document, dict):
        result = document.get("result")
        if document.get("success") is not True or not isinstance(result, dict):
            raise ValueError("the interface did not answer with a successful result")
        return {name: _networks(result[f"{name}_cidrs"], version) for name, version in FAMILIES}
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("an empty range list")
    version = ipaddress.ip_network(lines[0], strict=True).version
    return {dict((number, name) for name, number in FAMILIES)[version]: _networks(lines, version)}


def read_sources(pinned_entry_sources, fetch, timeout):
    """Read every source document of the pinned set; (source rows, published families, outcome or None)."""
    rows, published, outcome = [], {}, None
    for source in pinned_entry_sources:
        row = {"url": source["url"]}
        try:
            status, headers, body = fetch(source["url"], timeout)
        except Exception as error:  # noqa: BLE001 - a failed read is recorded, never guessed
            rows.append({**row, "error": type(error).__name__})
            outcome = UNREADABLE
            continue
        row.update({"http_status": status, "body_sha256": hashlib.sha256(body).hexdigest()})
        for name in ("etag", "last-modified"):
            if headers.get(name):
                row[name.replace("-", "_")] = headers[name]
        if status != 200 or len(body) > MAXIMUM_DOCUMENT_BYTES:
            rows.append({**row, "error": "unexpected_answer"})
            outcome = UNREADABLE
            continue
        try:
            families = ranges_of(body)
        except (ValueError, KeyError, TypeError, UnicodeDecodeError):
            rows.append({**row, "error": "not_a_range_document"})
            outcome = UNREADABLE
            continue
        row["families"] = sorted(families)
        rows.append(row)
        for name, ranges in families.items():
            if name in published and published[name] != ranges:
                outcome = outcome or DISAGREE
            published.setdefault(name, ranges)
    return rows, published, outcome


def candidate_set(pinned, rows, published, checked_at):
    """A full range-set record for today's published ranges, checked by the reader the service uses."""
    day = checked_at[:10]
    set_id = f"{pinned.provider}-{day}"
    if set_id == pinned.set_id:
        set_id += "-2"
    sources = []
    for row in rows:
        source = {"url": row["url"], "body_sha256": row["body_sha256"]}
        if row.get("etag"):
            source["etag"] = row["etag"].strip('"')
        elif row.get("last_modified"):
            source["last_modified"] = row["last_modified"]
        sources.append(source)
    entry = {"record_type": RANGE_SET_RECORD_TYPE, "set_id": set_id, "provider": pinned.provider,
             "client_address_header": pinned.client_address_header, "retrieved_at": checked_at,
             "sources": sources, "ipv4": published.get("ipv4", []), "ipv6": published.get("ipv6", []),
             "ranges_sha256": ranges_digest(published.get("ipv4", []), published.get("ipv6", []))}
    read_range_sets({"record_type": RANGE_SETS_RECORD_TYPE, "sets": [entry]})
    return entry


def check(*, authorize_network_reads, set_id=None, fetch=default_fetch, timeout=20, now=None):
    """The check record and its exit code. Nothing is read without the network authorization."""
    sets = pinned_range_sets()
    pinned = sets.get(set_id) if set_id else max(sets.values(), key=lambda entry: entry.retrieved_at)
    checked_at = (now or datetime.datetime.now(datetime.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    record = {"record_type": RECORD_TYPE, "set_id": set_id if pinned is None else pinned.set_id,
              "checked_at": checked_at}
    if pinned is None:
        return {**record, "outcome": REFUSED, "reason": "unknown_set_id", "pinned": sorted(sets)}, 2
    if not authorize_network_reads:
        return {**record, "outcome": REFUSED, "reason": "network_reads_not_authorized"}, 2
    from importlib.resources import files
    document = parse_range_sets(files("loop_engine").joinpath(*RANGES_RESOURCE).read_text("utf-8"))
    entry = next(row for row in document["sets"] if row["set_id"] == pinned.set_id)
    rows, published, outcome = read_sources(entry["sources"], fetch, timeout)
    record["sources"] = rows
    if outcome is None and set(published) != {name for name, _version in FAMILIES}:
        outcome = UNREADABLE
    if outcome is not None:
        return {**record, "outcome": outcome}, EXIT_CODES[outcome]
    held = {name: [str(network) for network in pinned.networks if network.version == version]
            for name, version in FAMILIES}
    added = {name: [value for value in published[name] if value not in held[name]] for name, _version in FAMILIES}
    removed = {name: [value for value in held[name] if value not in published[name]] for name, _version in FAMILIES}
    record.update({"added": added, "removed": removed})
    if not any(added.values()) and not any(removed.values()):
        return {**record, "outcome": UNCHANGED}, 0
    try:
        record["candidate_set"] = candidate_set(pinned, rows, published, checked_at)
    except ValueError as error:
        record["candidate_refused"] = str(error)
    return {**record, "outcome": DRIFT}, 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--authorize-network-reads", action="store_true")
    parser.add_argument("--set-id", help="the pinned set to compare; the newest pinned set by default")
    parser.add_argument("--timeout", type=float, default=20)
    options = parser.parse_args(argv)
    record, code = check(authorize_network_reads=options.authorize_network_reads, set_id=options.set_id,
                         timeout=options.timeout)
    print(json.dumps(record, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
