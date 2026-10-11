"""Build the original website-demo source ZIP locally; never approve or publish it."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import stat
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from tools.candidate_review.prechecks.secrets import secret_patterns

ROOT = Path(__file__).resolve().parents[1]
MEMBERS = (
    "showcase/original-previews/orbit.mjs", "showcase/original-previews/orbit.html",
    "showcase/original-previews/score.json", "showcase/original-previews/music.mjs",
    "showcase/original-previews/export.mjs", "showcase/original-previews/test-originals.mjs",
    "showcase/original-previews/README.md", "showcase/original-previews/LICENSE",
    "showcase/tools/media-common.mjs", "showcase/package.json", "showcase/package-lock.json",
)


def build_archive(output, root=ROOT):
    root, output = Path(root).resolve(), Path(output)
    if not output.is_absolute() or output.exists() or output.is_symlink():
        raise ValueError("a new absolute source archive path is required")
    policy = root / "tools/candidate_review/resources/panel.json"
    patterns = secret_patterns(json.loads(policy.read_text())["precheck_engines"]["builtin_secret_patterns"])
    records, bodies = [], []
    for name in sorted(MEMBERS):
        path = root / name
        if path.resolve() != path or not stat.S_ISREG(path.stat().st_mode):
            raise ValueError("source archive inputs must be plain files")
        with path.open("rb") as source:
            body = source.read(128 * 1024 + 1)
        if not body or len(body) > 128 * 1024 or b"\0" in body:
            raise ValueError("source member exceeds its text-file bound")
        text = body.decode("utf-8")
        if any(pattern.search(text) for pattern in patterns):
            raise ValueError("source secret-pattern finding; content not echoed")
        bodies.append((name, body))
        records.append({"path": name, "sha256": sha256(body).hexdigest(), "bytes": len(body)})
    if sum(len(body) for _name, body in bodies) > 512 * 1024:
        raise ValueError("source archive exceeds its unpacked bound")
    with ZipFile(output, "x", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name, body in bodies:
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, body)
    body = output.read_bytes()
    if len(body) > 256 * 1024:
        raise ValueError("produced archive exceeds its byte bound; retained for inspection")
    return {"record_type": "website_example_source_archive/v1", "file": str(output), "sha256": sha256(body).hexdigest(),
            "bytes": len(body), "files": records, "secret_scan_engine": "builtin_secret_patterns",
            "secret_policy_sha256": sha256(policy.read_bytes()).hexdigest(), "secret_pattern_count": len(patterns),
            "secret_pattern_findings": 0, "publication": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(build_archive(args.output), indent=2))


if __name__ == "__main__":
    main()
