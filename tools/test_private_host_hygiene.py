"""No current file names the Tactical model server: its domains, its certificate's label or its address.

Roadmap step S-6.189 asks for a hygiene check that refuses the private model server's host and the certificate
hostname in current files and leaves dated records unchanged. The server's address is private configuration
(``tools/private_endpoints.py``). This check holds only SHA-256 digests of the names, never the names: it hashes
every host-like token, every DNS label and every IPv4 address of each tracked or new text file outside
``artifacts/`` and outside dated records, and fails on a digest it knows. Dated records keep their bytes as
history, and one of them is the known-wrong control that proves each digest still matches the real name.

```text
private host hygiene
├── names: the certificate's domain and label, the connect domain, the server address (digests only)
├── forms: any subdomain, upper case, escaped dots, inside URLs and longer host names
├── scope: tracked and new files, minus artifacts/ and dated records
└── known-wrong controls: invented names in every form, the dated binding record, and a tree that copies its
    lines into a current file
```
"""
from __future__ import annotations

import functools
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from test_tls_verification_guard import current  # noqa: E402  the same artifacts and dated-record rule

#: SHA-256 digest -> what it names. Two host-name labels or more are compared as a whole domain.
DOMAINS = {
    "6eab3e6b30a33f84469c2c6f9a413a194d3213e6bdf90edb642e9e3bc7557914": "the Tactical certificate's domain",
    "c3c8e9b35a608fe7ef52592bb62bb21efb8d1708ad90877acd6b56a7e839ea8d": "the Tactical connect domain",
}
LABELS = {
    "60abc3d05f945301fb100de9bb47165051e9e4b6807d5f401e75bfe17782ac21": "the Tactical certificate's own label",
}
ADDRESSES = {
    "2fb23ca51eb74efb752ba821f8c93d8ab21021dda027605cf7bd1fb2f288d764": "the Tactical server's address",
}
#: The dated record that names all four, kept as history; the real-data control reads it.
CONTROL_RECORD = "docs/verification/TACTICAL-GENERATION-BINDING-2026-09-23.md"

#: The lengths of the names above, so that only a candidate of a matching length is hashed. Each domain is a
#: registrable domain of exactly two labels. A length names nothing.
DOMAIN_LENGTHS = frozenset({15, 23})
LABEL_LENGTHS = frozenset({11})
#: Every byte that cannot be part of a host name or an address becomes a space before the text is split.
HOST_BYTES = frozenset(b"abcdefghijklmnopqrstuvwxyz0123456789.-")
SEPARATE = bytes(value if value in HOST_BYTES else 32 for value in range(256))
MAX_BYTES = 32 * 1024 * 1024


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def private_names(raw: bytes, domains=DOMAINS, labels=LABELS, addresses=ADDRESSES,
                  domain_lengths=DOMAIN_LENGTHS, label_lengths=LABEL_LENGTHS) -> set:
    """What the text names among the digests: each matching description, from every form the name can take.

    The text is lower-cased, escaped dots become dots, and every other byte outside host names splits it. Each
    distinct run is read once: as a dotted quad, as pairs of adjacent labels, and as single labels. Only a
    candidate of a listed length is hashed.
    """
    single, pairs, quads = set(), set(), set()
    for run in set(raw.lower().replace(b"\\.", b".").translate(SEPARATE).split()):
        run = run.strip(b".-")
        if b"." not in run:
            if len(run) in label_lengths:
                single.add(run)
            continue
        parts = run.split(b".")
        if len(parts) == 4 and all(part.isdigit() and len(part) <= 3 for part in parts):
            quads.add(run)
        for first, second in zip(parts, parts[1:]):
            if len(first) + len(second) + 1 in domain_lengths:
                pairs.add(first + b"." + second)
        single.update(part for part in parts if len(part) in label_lengths)
    found = {labels.get(_digest(label)) for label in single}
    found |= {domains.get(_digest(pair)) for pair in pairs}
    found |= {addresses.get(_digest(quad)) for quad in quads}
    found.discard(None)
    return found


def candidate_files(root: Path) -> list:
    """Tracked files and new files git does not ignore, when ``root`` is the top of a work tree."""
    try:
        top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True,
                             check=True, timeout=60, text=True).stdout.strip()
        if Path(top).resolve() == root.resolve():
            listed = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--cached", "--others",
                                     "--exclude-standard"], capture_output=True, check=True, timeout=120).stdout
            return sorted(set(item for item in listed.decode("utf-8", "surrogateescape").split("\0") if item))
    except (OSError, subprocess.SubprocessError):
        pass
    return sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()
                  and ".git" not in path.relative_to(root).parts)


def scan_tree(root: Path) -> dict:
    """{relative path: names} for every current text file under ``root`` that names a private name."""
    found = {}
    for relative in candidate_files(root):
        path = root / relative
        if not current(relative) or path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
            continue
        raw = path.read_bytes()
        if b"\0" in raw[:8192]:
            continue
        names = private_names(raw)
        if names:
            found[relative] = sorted(names)
    return found


@functools.lru_cache(maxsize=1)
def repository_scan() -> tuple:
    return tuple(sorted(scan_tree(ROOT).items()))


class RepositoryTest(unittest.TestCase):
    def test_no_current_file_names_the_tactical_server(self):
        found = dict(repository_scan())
        self.assertEqual(found, {}, "move the address into private configuration (tools/private_endpoints.py):\n"
                         + "\n".join(f"  {path}: {', '.join(names)}" for path, names in found.items()))

    def test_the_dated_record_still_names_all_four_so_every_digest_is_live(self):
        names = private_names((ROOT / CONTROL_RECORD).read_bytes())
        self.assertEqual(names, {*DOMAINS.values(), *LABELS.values(), *ADDRESSES.values()})
        self.assertFalse(current(CONTROL_RECORD), "a dated record is history, outside the scope of the check")


class KnownWrongControlTest(unittest.TestCase):
    INVENTED = {"domains": {_digest(b"forbidden-host.example"): "invented domain"},
                "labels": {_digest(b"forbiddenlabel"): "invented label"},
                "addresses": {_digest(b"192.0.2.77"): "invented address"},
                "domain_lengths": frozenset({len(b"forbidden-host.example")}),
                "label_lengths": frozenset({len(b"forbiddenlabel")})}

    def names(self, text: str) -> set:
        return private_names(text.encode(), **self.INVENTED)

    def test_every_form_of_an_invented_name_is_found(self):
        cases = {
            "https://ai.forbidden-host.example:6969/v1": "invented domain",
            "the certificate covers *.FORBIDDEN-HOST.EXAMPLE and its apex": "invented domain",
            r"pattern = 'ai\.forbidden-host\.example'": "invented domain",
            "edge.forbidden-host.example.cdn.example.net": "invented domain",
            "(forbidden-host.example)": "invented domain",
            "the forbiddenlabel zone": "invented label",
            "forbiddenlabel.example.org": "invented label",
            "connect to 192.0.2.77:6969": "invented address",
        }
        for text, name in cases.items():
            with self.subTest(text=text):
                self.assertIn(name, self.names(text))

    def test_neighbouring_names_are_not_found(self):
        for text in ("notforbidden-host.example", "forbidden-host-example.com", "forbidden-host.examples",
                     "forbiddenlabels and preforbiddenlabel", "192.0.2.7", "192.0.2.770", "10.192.0.2.77"):
            with self.subTest(text=text):
                self.assertEqual(self.names(text), set())

    def test_a_current_file_that_copies_the_record_fails_and_the_record_itself_does_not(self):
        lines = [line for line in (ROOT / CONTROL_RECORD).read_bytes().splitlines(keepends=True)
                 if private_names(line)]
        self.assertTrue(lines)
        copied = b"".join(lines)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in ("tools/new_client.py", "artifacts/run-1/record.json", CONTROL_RECORD,
                             "docs/context/NOTE-2026-10-16.md", "docs/guides/new-guide.md"):
                (root / relative).parent.mkdir(parents=True, exist_ok=True)
                (root / relative).write_bytes(copied)
            (root / "tools/binary.dat").write_bytes(b"\0" + copied)
            found = scan_tree(root)
        self.assertEqual(sorted(found), ["docs/guides/new-guide.md", "tools/new_client.py"])
        self.assertEqual(set(found["tools/new_client.py"]), {*DOMAINS.values(), *LABELS.values(), *ADDRESSES.values()})


if __name__ == "__main__":
    unittest.main()
