#!/usr/bin/env python3
"""E01 pilot, run 2 (September 25, 2026): reproducible step materialization.

No model call is made. Two packages, five placement engines, two target layouts
(Claude Code .claude/skills/<name>/, Codex .agents/skills/<name>/), two fresh
roots per engine and package. Every root has its own git repository, an empty
HOME and the package at a different absolute path. Outbound network is closed
through an unreachable proxy; an engine whose offline run fails is rerun online
and marked, so network need is a recorded fact rather than an assumption.

Recorded per run: every command's exit status and seconds, the project tree
(kind, mode, SHA-256), every file created under HOME, for each expected native
path whether it exists, is byte-identical to the package file, keeps its mode,
and is reached through a symbolic link, whether the SKILL.md metadata keys
survived, and the extra files the engine wrote. Runs A and B are compared after
replacing each run's own absolute folder with a placeholder.
"""
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time

# Paths come from the environment so the run never writes inside the repository.
# E01_WORK: an empty folder for the runs (21 MB); E01_TOOLS: a folder holding
# npmtools/ (npm install @sentry/dotagents@3.1.0 opkg@0.11.3 rulesync@18.0.0)
# and apmvenv/ (python3 -m venv apmvenv && apmvenv/bin/pip install apm-cli==0.31.0).
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
HERE = os.environ["E01_WORK"]
REPO = os.path.abspath(os.path.join(SCRIPTS, "..", "..", ".."))
BODIES = f"{REPO}/examples/29_intelligence_service/starter-catalogue/bodies"
TOOLS = os.environ["E01_TOOLS"]
NPM_BIN = f"{TOOLS}/npmtools/node_modules/.bin"
APM = f"{TOOLS}/apmvenv/bin/apm"
NODE_DIR = os.path.dirname(shutil.which("node"))
PATH = f"{NPM_BIN}:{os.path.dirname(APM)}:{NODE_DIR}:/usr/local/bin:/usr/bin:/bin"
TARGETS = {"claude-code": ".claude/skills", "codex": ".agents/skills"}
DEAD_PROXY = "http://127.0.0.1:9"
META_KEYS = ("baltor-identity", "baltor-body-sha256")


def frontmatter(name, description, identity, body):
    digest = hashlib.sha256(body).hexdigest()
    return (f"---\nname: {name}\ndescription: {description}\nmetadata:\n"
            f"  baltor-identity: {identity}\n  baltor-body-sha256: {digest}\n---\n").encode() + body


def seeded_bytes(n):
    out, block = b"", b"baltor-e01-seed"
    while len(out) < n:
        block = hashlib.sha256(block).digest()
        out += block
    return out[:n]


def packages():
    b1 = open(f"{BODIES}/find_duplicate_records_with_blocking_keys.md", "rb").read()
    p1 = {"SKILL.md": (frontmatter(
        "find-duplicate-records-with-blocking-keys",
        "Find duplicate customer, company or contact rows in one table by comparing only rows that share a declared blocking key.",
        "find_duplicate_records_with_blocking_keys", b1), 0o644)}
    b2 = open(f"{BODIES}/split_address_lines_into_components.md", "rb").read()
    b2 += (b"\n## Files in this package\n\n- `scripts/split_address.py` splits one address line.\n"
           b"- `references/formats.md` lists the address formats this skill covers.\n"
           b"- `assets/sample.csv` holds two sample rows.\n")
    script = (b"#!/usr/bin/env python3\n\"\"\"Split one address line into street and locality.\"\"\"\n"
              b"import sys\n\n\ndef split(line):\n    street, _, rest = line.partition(',')\n"
              b"    return {'street': street.strip(), 'locality': rest.strip()}\n\n\n"
              b"if __name__ == '__main__':\n    print(split(sys.argv[1]))\n")
    p2 = {
        "SKILL.md": (frontmatter(
            "split-address-lines-into-components",
            "Split free-text address lines into street, locality, region and postal code, and hold every line whose reading is ambiguous for review instead of guessing.",
            "split_address_lines_into_components", b2), 0o644),
        "scripts/split_address.py": (script, 0o755),
        "references/formats.md": (b"# Address formats\n\nStreet first, then a comma, then locality.\n", 0o644),
        "assets/sample.csv": ("id,line\r\n1,\"Bahnhofstrasse 1, 8001 Zürich\"\r\n2,\"1 Main St, Springfield\"\r\n".encode(), 0o644),
        "assets/seed.bin": (seeded_bytes(256), 0o644),
    }
    return {"P1-single-file": ("find-duplicate-records-with-blocking-keys", p1),
            "P2-multi-file": ("split-address-lines-into-components", p2)}


def write_package(dst, files):
    for rel, (data, mode) in files.items():
        path = os.path.join(dst, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "wb").write(data)
        os.chmod(path, mode)


def tree(root, skip=(".git",)):
    out = {}
    for dp, dns, fns in os.walk(root, followlinks=False):
        dns[:] = [d for d in dns if d not in skip]
        for n in dns + fns:
            p = os.path.join(dp, n)
            rel = os.path.relpath(p, root)
            st = os.lstat(p)
            if stat.S_ISLNK(st.st_mode):
                out[rel] = {"kind": "link", "target": os.readlink(p)}
            elif stat.S_ISDIR(st.st_mode):
                out[rel] = {"kind": "dir", "mode": oct(st.st_mode & 0o777)}
            else:
                data = open(p, "rb").read()
                out[rel] = {"kind": "file", "mode": oct(st.st_mode & 0o777), "bytes": len(data),
                            "sha256": hashlib.sha256(data).hexdigest()}
    return out


def normalized_digest(path, base):
    data = open(path, "rb").read().replace(base.encode(), b"<RUN>")
    return hashlib.sha256(data).hexdigest()


def env_for(home, offline, extra=None):
    env = {"HOME": home, "PATH": PATH, "LANG": "C.UTF-8", "NO_COLOR": "1", "CI": "1",
           "XDG_CONFIG_HOME": f"{home}/.config", "XDG_CACHE_HOME": f"{home}/.cache",
           "XDG_DATA_HOME": f"{home}/.local/share", "npm_config_cache": f"{home}/.npm",
           "GIT_TERMINAL_PROMPT": "0", "TERM": "dumb"}
    if offline:
        for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
            env[k] = DEAD_PROXY
        env["npm_config_offline"] = "true"
    env.update(extra or {})
    return env


def run(cmd, cwd, env, logdir, idx):
    t = time.time()
    try:
        p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=300, shell=True)
        rc, out, err = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as e:
        rc, out, err = "timeout", str(e.stdout or ""), str(e.stderr or "")
    open(f"{logdir}/cmd{idx}.log", "w").write(f"$ {cmd}\nrc={rc}\n--- stdout\n{out}\n--- stderr\n{err}\n")
    return {"cmd": cmd, "rc": rc, "seconds": round(time.time() - t, 2),
            "stdout_tail": out[-500:], "stderr_tail": err[-500:]}


def steps_for(engine, src, prj, name, pkg_root):
    if engine == "native":
        return [f"python3 {SCRIPTS}/native_place.py {src} {prj} {name}"]
    if engine == "apm":
        return [f"{APM} install {src} --target claude,codex --no-policy </dev/null"]
    if engine == "dotagents":
        return [f"mkdir -p vendor && cp -rp {src} vendor/{name}",
                "dotagents --project init --agents claude,codex </dev/null",
                "python3 -c \"import re;p='agents.toml';t=open(p).read();"
                "t=re.sub(r'\\n\\[\\[skills\\]\\]\\nname = \\\"dotagents\\\"\\nsource = \\\"getsentry/dotagents\\\"\\n','\\n',t);"
                "open(p,'w').write(t)\"",
                "rm -rf .agents/skills/dotagents",
                f"dotagents --project add path:vendor/{name} </dev/null",
                "dotagents --project install </dev/null"]
    if engine == "rulesync":
        return [f"mkdir -p .rulesync/skills && cp -rp {src} .rulesync/skills/{name}",
                "rulesync generate --targets claudecode,codexcli --features skills </dev/null"]
    if engine == "opkg":
        return [f"opkg install {pkg_root} --skills {name} --platforms claude codex </dev/null"]
    raise ValueError(engine)


SOURCE_COPY_PREFIXES = ("vendor/", ".rulesync/")


def observe(prj, name, files):
    checks = {}
    for target, root in TARGETS.items():
        for rel, (data, mode) in files.items():
            path = os.path.join(prj, root, name, rel)
            rec = {"exists": os.path.isfile(path)}
            if rec["exists"]:
                got = open(path, "rb").read()
                rec["byte_identical"] = got == data
                rec["mode"] = oct(os.stat(path).st_mode & 0o777)
                rec["mode_preserved"] = (os.stat(path).st_mode & 0o777) == mode
                comps, cur, via_link = os.path.join(root, name, rel).split(os.sep), prj, False
                for c in comps:
                    cur = os.path.join(cur, c)
                    via_link = via_link or os.path.islink(cur)
                rec["reached_via_link"] = via_link
                if rel == "SKILL.md":
                    head = got.split(b"\n---\n", 1)[0].decode("utf-8", "replace")
                    rec["metadata_keys_kept"] = [k for k in META_KEYS if re.search(rf"^\s*{k}:", head, re.M)]
            checks[f"{target}:{rel}"] = rec
    return checks


def one_run(engine, pkg_key, name, files, label, offline):
    base = f"{HERE}/runs/{engine}/{pkg_key}/{label}-{'off' if offline else 'on'}-{os.urandom(3).hex()}"
    pkg_root, prj, home, logs = f"{base}/src", f"{base}/project", f"{base}/home", f"{base}/logs"
    src = f"{pkg_root}/skills/{name}"
    for d in (src, prj, home, logs):
        os.makedirs(d)
    write_package(src, files)
    extra = {"PYTHONPATH": f"{REPO}/src:{REPO}/tools"} if engine == "native" else None
    env = env_for(home, offline, extra)
    subprocess.run(["git", "init", "-q", prj], check=True, env=env_for(home, True))
    home_before = set(tree(home))
    cmd_logs = [run(c, prj, env, logs, i) for i, c in enumerate(steps_for(engine, src, prj, name, pkg_root))]
    t = tree(prj)
    home_after = tree(home)
    new_home = sorted(k for k in home_after if k not in home_before and home_after[k]["kind"] != "dir")
    native_prefixes = tuple(f"{root}/{name}" for root in TARGETS.values())
    extra_files = sorted(k for k, v in t.items() if v["kind"] != "dir"
                         and not k.startswith(native_prefixes) and not k.startswith(SOURCE_COPY_PREFIXES))
    links = {k: v["target"] for k, v in t.items() if v["kind"] == "link"}
    norm = {k: (v["kind"], v.get("mode"), normalized_digest(os.path.join(prj, k), base) if v["kind"] == "file"
                else v.get("target", "").replace(base, "<RUN>")) for k, v in t.items()}
    return {"base": base, "offline": offline, "commands": cmd_logs,
            "all_commands_ok": all(c["rc"] == 0 for c in cmd_logs),
            "checks": observe(prj, name, files), "extra_project_files": extra_files, "links": links,
            "home_new_file_count": len(new_home), "home_new_files_sample": new_home[:25],
            "normalized_tree": norm}


def versions():
    out = {}
    for label, cmd in {"apm": f"{APM} --version", "dotagents": "dotagents --version", "rulesync": "rulesync --version",
                       "opkg": "opkg --version", "node": "node --version", "git": "git --version",
                       "python": "python3 --version"}.items():
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env_for(f"{HERE}/vhome", True))
        out[label] = (p.stdout.strip() or p.stderr.strip()).splitlines()[-1][:120] if (p.stdout or p.stderr) else "?"
    return out


def main():
    os.makedirs(f"{HERE}/vhome", exist_ok=True)
    engines = sys.argv[1:] or ["native", "apm", "dotagents", "rulesync", "opkg"]
    result = {"record_type": "e01_materialization_pilot/v1", "date": time.strftime("%Y-%m-%d %H:%M %Z"),
              "tool_versions": versions(), "packages": {}, "runs": {}, "comparison": {}}
    for pkg_key, (name, files) in packages().items():
        result["packages"][pkg_key] = {"name": name, "files": {rel: {"sha256": hashlib.sha256(d).hexdigest(),
                                       "bytes": len(d), "mode": oct(m)} for rel, (d, m) in files.items()}}
        for engine in engines:
            a = one_run(engine, pkg_key, name, files, "A", offline=True)
            ok_offline = a["all_commands_ok"] and any(c["exists"] for c in a["checks"].values())
            if ok_offline:
                b = one_run(engine, pkg_key, name, files, "B", offline=True)
                runs = {"A": a, "B": b}
                network = "not needed: both runs offline"
            else:
                a_on = one_run(engine, pkg_key, name, files, "A", offline=False)
                b_on = one_run(engine, pkg_key, name, files, "B", offline=False)
                runs = {"A-offline-failed": a, "A": a_on, "B": b_on}
                network = "needed: the offline run failed or placed nothing, so both counted runs went online"
            key = f"{engine}/{pkg_key}"
            result["runs"][key] = runs
            ta, tb = runs["A"]["normalized_tree"], runs["B"]["normalized_tree"]
            diffs = sorted(k for k in set(ta) | set(tb) if ta.get(k) != tb.get(k))
            result["comparison"][key] = {"network": network, "a_b_identical_after_path_normalization": not diffs,
                                         "a_b_differences": diffs[:20]}
    json.dump(result, open(f"{HERE}/e01-pilot-result-2026-09-25.json", "w"), indent=1, sort_keys=True)
    print(json.dumps(result["tool_versions"]))
    for key, cmp in result["comparison"].items():
        a = result["runs"][key]["A"]
        checks = a["checks"]
        exact = sum(1 for c in checks.values() if c.get("byte_identical"))
        present = sum(1 for c in checks.values() if c["exists"])
        modes = [c.get("mode_preserved") for k, c in checks.items() if k.endswith("split_address.py") and c["exists"]]
        meta = {k.split(':')[0]: c.get("metadata_keys_kept") for k, c in checks.items() if k.endswith("SKILL.md")}
        print(f"{key}: ok={a['all_commands_ok']} present={present}/{len(checks)} exact={exact}/{len(checks)} "
              f"script_mode_kept={modes} meta={meta} links={a['links']} extra={a['extra_project_files']} "
              f"home_new={a['home_new_file_count']} ab_same={cmp['a_b_identical_after_path_normalization']} "
              f"diffs={cmp['a_b_differences'][:4]} network={cmp['network'][:12]}")


if __name__ == "__main__":
    main()
