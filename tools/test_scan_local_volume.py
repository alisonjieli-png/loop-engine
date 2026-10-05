"""The volume inventory reads only, classes each project by typed provenance signals, and writes outside the repository.

Roadmap step S-6.207. Each rule has a known-wrong case: a project whose git remote names another account, whose
licence names another holder, or whose source carries another copyright line is third-party material; a vendored
folder is skipped by name; an output inside this repository is refused; and no file is read beyond its first bytes.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "src")]

import scan_local_volume as scanner  # noqa: E402

MIT = "MIT License\n\nCopyright (c) 2026 Somebody Else\n\nPermission is hereby granted.\n"


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def fixture_volume(root: Path) -> None:
    """Five projects: the owner's, one cloned from another account, one under another holder's licence, one with
    another author's copyright line, and one that only vendored dependencies would make look large."""
    _write(root, "PROJECTS/resizer/README.md", "# Resizer\n\nResize every image in a folder.\n")
    _write(root, "PROJECTS/resizer/main.py", "\"\"\"Resize images.\"\"\"\nimport sys\n\ndef resize(path, width):\n    return path\n")
    _write(root, "PROJECTS/resizer/requirements.txt", "pillow>=10\n")
    _write(root, "PROJECTS/cloned/README.md", "# Cloned\n")
    _write(root, "PROJECTS/cloned/app.py", "print('x')\n")
    _write(root, "PROJECTS/cloned/.git/config", "[remote \"origin\"]\n\turl = https://github.com/someone-else/cloned.git\n")
    _write(root, "PROJECTS/licensed/README.md", "# Licensed\n")
    _write(root, "PROJECTS/licensed/LICENSE", MIT)
    _write(root, "PROJECTS/licensed/tool.py", "print('y')\n")
    _write(root, "PROJECTS/copied/README.md", "# Copied\n")
    _write(root, "PROJECTS/copied/lib.py", "# Copyright (c) 2021 Another Author\nprint('z')\n")
    _write(root, "PROJECTS/own-remote/README.md", "# Own remote\n")
    _write(root, "PROJECTS/own-remote/run.py", "print('w')\n")
    _write(root, "PROJECTS/own-remote/.git/config", "[remote \"origin\"]\n\turl = git@github.com:owner-account/own-remote.git\n")
    _write(root, "PROJECTS/resizer/node_modules/left-pad/index.js", "module.exports = 1;\n")
    _write(root, "PROJECTS/resizer/__pycache__/main.cpython-314.pyc", "binary")
    _write(root, "$RECYCLE.BIN/old.py", "print('gone')\n")


class InventoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.volume = self.root / "volume"
        fixture_volume(self.volume)
        self.output = self.root / "inventory"
        code = scanner.main(["--volume", str(self.volume), "--output", str(self.output),
                             "--owner-account", "owner-account", "--owner-name", "amarel"])
        self.assertEqual(code, 0)
        self.summary = json.loads((self.output / "summary.json").read_text())
        self.projects = {row["path"]: row for row in map(json.loads, (self.output / "projects.jsonl").read_text().splitlines())}

    def test_every_project_is_classed_by_its_typed_signals(self):
        classes = {path.split("/")[-1]: row["provenance_class"] for path, row in self.projects.items()}
        self.assertEqual(classes, {"resizer": scanner.OWNER_DECLARED, "cloned": scanner.THIRD_PARTY_REMOTE,
                                   "licensed": scanner.THIRD_PARTY_LICENCE, "copied": scanner.THIRD_PARTY_COPYRIGHT,
                                   "own-remote": scanner.OWNER_REMOTE})
        self.assertEqual(self.projects["PROJECTS/cloned"]["remote_owners"], ["someone-else"])
        self.assertEqual(self.projects["PROJECTS/licensed"]["licence_holders"], ["Somebody Else"])
        self.assertEqual(self.projects["PROJECTS/copied"]["copyright_holders"], ["Another Author"])
        self.assertEqual(self.summary["projects_by_provenance_class"][scanner.OWNER_DECLARED], 1)
        self.assertIn("declared on September 26, 2026", self.summary["provenance_basis"])

    def test_selected_top_level_project_is_not_lost(self):
        destination = self.root / "selected-root"
        self.assertEqual(scanner.main(["--volume", str(self.volume), "--root", "PROJECTS/resizer",
                                       "--output", str(destination)]), 0)
        summary = json.loads((destination / "summary.json").read_text())
        self.assertEqual(summary["projects"], 1)

    def test_roots_cannot_escape_and_inventory_cannot_feed_itself(self):
        for root in ("../", str(self.root)):
            with self.subTest(root=root):
                self.assertEqual(scanner.main(["--volume", str(self.volume), "--root", root,
                                               "--output", str(self.root / "refused")]), 2)
        self.assertEqual(scanner.main(["--volume", str(self.volume), "--output", str(self.volume / "inventory")]), 2)
        self.assertFalse((self.volume / "inventory").exists())
        # With selected roots, the inventory may sit inside the volume, never inside a walked root.
        self.assertEqual(scanner.main(["--volume", str(self.volume), "--root", "PROJECTS/resizer",
                                       "--output", str(self.volume / "PROJECTS/resizer/inventory")]), 2)
        self.assertFalse((self.volume / "PROJECTS/resizer/inventory").exists())
        inside = self.volume / "private" / "inventory"
        self.assertEqual(scanner.main(["--volume", str(self.volume), "--root", "PROJECTS/resizer",
                                       "--output", str(inside)]), 0)
        walked = {json.loads(line)["path"] for line in (inside / "files-001.jsonl").read_text().splitlines()}
        self.assertFalse(any(path.startswith("private/") for path in walked))

    def test_inventory_excerpts_and_remotes_remove_credentials_and_skip_symlinks(self):
        token = "ghp_" + "x" * 30
        text = "api_key=" + token + "\npassword=example-secret\n"
        self.assertNotIn(token, scanner._redact(text))
        self.assertNotIn("example-secret", scanner._redact(text))
        project = self.root / "remote-project"
        _write(project, ".git/config", "url = https://user:example-secret@github.com/owner/repo.git?token=private\n")
        self.assertEqual(scanner._remotes(str(project / ".git")), ["https://github.com/owner/repo.git"])
        _write(project, ".git/config", "url = https://[broken-host/repo\n")
        problems = []
        self.assertEqual(scanner._remotes(str(project / ".git"), problems=problems), [])
        self.assertEqual(problems, ["remote_url_unreadable"])
        self.assertEqual(scanner._classify({"provenance_issues": problems}, set(), set()), scanner.PROVENANCE_UNRESOLVED)
        _write(project, ".git/config", "url = https://" + token + "@github.com/owner/repo.git\n")
        self.assertEqual(scanner._remotes(str(project / ".git")), ["https://github.com/owner/repo.git"])
        outside = self.root / "outside.txt"
        outside.write_text("private marker")
        link = self.root / "link.txt"
        link.symlink_to(outside)
        self.assertEqual(scanner._read_head(str(link)), "")

    def test_vendored_and_system_folders_are_skipped_and_nothing_is_copied_or_hashed(self):
        files = [json.loads(line) for path in sorted(self.output.glob("files-*.jsonl"))
                 for line in path.read_text().splitlines()]
        paths = {row["path"] for row in files}
        self.assertNotIn("PROJECTS/resizer/node_modules/left-pad/index.js", paths)
        self.assertNotIn("PROJECTS/resizer/__pycache__/main.cpython-314.pyc", paths)
        self.assertNotIn("$RECYCLE.BIN/old.py", paths)
        self.assertIn("PROJECTS/resizer/main.py", paths)
        self.assertEqual(self.summary["skipped_folders"]["node_modules"], 1)
        self.assertEqual(set(files[0]), {"record_type", "path", "size_bytes", "extension", "language", "modified_at"})
        self.assertFalse(any("sha256" in row or "digest" in row for row in files))
        self.assertEqual(self.projects["PROJECTS/resizer"]["languages"], {"markdown": 1, "python": 1, "text": 1})
        self.assertEqual(self.projects["PROJECTS/resizer"]["source_files"], 1, "prose and data are not code")
        self.assertEqual(set(os.listdir(self.output)),
                         {"files-001.jsonl", "projects.jsonl", "excluded.jsonl", "summary.json", "progress.json"})
        self.assertEqual((self.output / "excluded.jsonl").read_text(), "", "nothing in this fixture is private")

    def test_known_wrong_an_output_inside_the_repository_is_refused(self):
        target = HERE.parent / "inventory-here"
        code = scanner.main(["--volume", str(self.volume), "--output", str(target)])
        self.assertEqual(code, 2)
        self.assertFalse(target.exists())
        self.assertEqual(scanner.main(["--volume", str(self.root / "missing"), "--output", str(self.root / "x")]), 2)

    def test_known_wrong_without_the_remote_rule_a_clone_would_pass_as_the_owners(self):
        project = dict(self.projects["PROJECTS/cloned"])
        self.assertEqual(scanner._classify(project, {"owner-account"}, {"amarel"}), scanner.THIRD_PARTY_REMOTE)
        self.assertEqual(scanner._classify({**project, "remote_owners": []}, {"owner-account"}, {"amarel"}),
                         scanner.OWNER_DECLARED)
        own = dict(self.projects["PROJECTS/own-remote"])
        self.assertEqual(scanner._classify(own, {"owner-account"}, {"amarel"}), scanner.OWNER_REMOTE)
        self.assertEqual(scanner._classify(own, set(), {"amarel"}), scanner.THIRD_PARTY_REMOTE)

    def test_a_copyright_line_naming_the_owner_keeps_the_owners_class(self):
        project = {**self.projects["PROJECTS/copied"], "copyright_holders": ["Taylor Amarel"], "licence_holders": []}
        self.assertEqual(scanner._classify(project, set(), {"amarel"}), scanner.OWNER_DECLARED)


SECRET_MARKER = "do-not-copy-this-value"


def private_volume(root: Path) -> None:
    """A home folder: one project with harness files, credentials beside it, a secret store, mail, and a folder of
    personal documents the operator excludes by name."""
    _write(root, "work/agent-kit/README.md", "# Agent kit\n")
    _write(root, "work/agent-kit/tool.py", "print('ok')\n")
    _write(root, "work/agent-kit/skills/resize-images/SKILL.md", "---\nname: resize-images\n---\n# Resize\n")
    _write(root, "work/agent-kit/.claude/agents/reviewer.md", "# Reviewer\n")
    _write(root, "work/agent-kit/.claude/commands/ship.md", "# Ship\n")
    _write(root, "work/agent-kit/AGENTS.md", "# Instructions\n")
    _write(root, "work/agent-kit/scene.blend", "binary")
    # Credentials and private material: none of these may be listed by name or opened.
    _write(root, "work/agent-kit/.env", "API_KEY=" + SECRET_MARKER + "\n")
    _write(root, "work/agent-kit/.mcp.json", '{"env": {"TOKEN": "' + SECRET_MARKER + '"}}\n')
    _write(root, "work/agent-kit/config/credentials.json", '{"key": "' + SECRET_MARKER + '"}\n')
    # A source file whose name says it holds a secret: if it were sampled, its copyright line would make the project
    # look like someone else's work.
    _write(root, "work/agent-kit/api_secret_store.py", "# Copyright (c) 2020 Credential Owner\nKEY='"
           + SECRET_MARKER + "'\n")
    _write(root, ".ssh/id_ed25519", SECRET_MARKER)
    _write(root, ".ssh/config", "Host build-server\n")  # an ordinary name inside a secret store
    _write(root, "mail/inbox/2026-10-01.eml", "Subject: " + SECRET_MARKER + "\n")
    # A browser profile an automation project kept beside its code (sessions and local storage, ordinary names).
    _write(root, "work/agent-kit/data/chrome-profile/Default/Local State", '{"session": "' + SECRET_MARKER + '"}')
    _write(root, "PERSONAL/Identity/passport.pdf", SECRET_MARKER)


class PrivateWalkTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.volume = self.root / "home"
        private_volume(self.volume)
        self.output = self.root / "inventory"
        code = scanner.main(["--volume", str(self.volume), "--output", str(self.output), "--root", "work",
                             "--root", "mail", "--root", ".ssh", "--root", "PERSONAL",
                             "--exclude-path", "PERSONAL/Identity=personal identity documents"])
        self.assertEqual(code, 0)
        self.rows = [json.loads(line) for path in sorted(self.output.glob("files-*.jsonl"))
                     for line in path.read_text().splitlines()]
        self.excluded = [json.loads(line) for line in (self.output / "excluded.jsonl").read_text().splitlines()]
        self.summary = json.loads((self.output / "summary.json").read_text())

    def test_harness_files_are_nominated_by_kind(self):
        kinds = {row["path"]: row.get("harness_kind", "") for row in self.rows}
        self.assertEqual(kinds["work/agent-kit/skills/resize-images/SKILL.md"], "skill")
        self.assertEqual(kinds["work/agent-kit/.claude/agents/reviewer.md"], "agent")
        self.assertEqual(kinds["work/agent-kit/.claude/commands/ship.md"], "command")
        self.assertEqual(kinds["work/agent-kit/AGENTS.md"], "instructions")
        self.assertEqual(kinds["work/agent-kit/scene.blend"], "blender")
        self.assertEqual(kinds["work/agent-kit/tool.py"], "", "code is counted by project, not as a harness kind")
        self.assertNotIn("harness_kind", next(row for row in self.rows if row["path"].endswith("tool.py")))
        self.assertEqual(self.summary["harness_kinds"],
                         {"skill": 1, "agent": 1, "command": 1, "instructions": 1, "blender": 1})

    def test_credentials_and_private_messages_are_never_listed_or_read(self):
        paths = {row["path"] for row in self.rows}
        for leaked in ("work/agent-kit/.env", "work/agent-kit/.mcp.json", "work/agent-kit/config/credentials.json",
                       "work/agent-kit/api_secret_store.py", "mail/inbox/2026-10-01.eml"):
            self.assertNotIn(leaked, paths)
        written = "".join(path.read_text() for path in self.output.iterdir())
        self.assertNotIn(SECRET_MARKER, written)
        for name in (".env", ".mcp.json", "credentials.json", "api_secret_store.py", "2026-10-01.eml", "id_ed25519",
                     "passport.pdf"):
            self.assertNotIn(name, (self.output / "excluded.jsonl").read_text(), "a left-out file is never named")
        by_class = {(row["folder"], row["class"]): row for row in self.excluded}
        self.assertEqual(by_class[("work/agent-kit", "dotenv")]["files"], 1)
        self.assertEqual(by_class[("work/agent-kit", "harness_settings")]["files"], 1)
        self.assertEqual(by_class[("work/agent-kit", "credential_file")]["files"], 1)
        self.assertEqual(by_class[("work/agent-kit/config", "credential_file")]["files"], 1)
        self.assertEqual(by_class[("mail/inbox", "private_message")]["files"], 1)
        self.assertIsNone(by_class[(".ssh", "secret_store")]["files"], "a secret store is not entered or counted")
        self.assertIsNone(by_class[("work/agent-kit/data/chrome-profile", "secret_store")]["files"])
        self.assertFalse(any("chrome-profile" in path for path in paths), "a browser profile is never walked")
        self.assertEqual(by_class[("PERSONAL/Identity", "operator_excluded")]["reason"], "personal identity documents")
        self.assertIsNone(by_class[("PERSONAL/Identity", "operator_excluded")]["files"], "not walked, not counted")
        projects = [json.loads(line) for line in (self.output / "projects.jsonl").read_text().splitlines()]
        kit = next(row for row in projects if row["path"] == "work/agent-kit")
        self.assertEqual(kit["copyright_holders"], [], "the secret-named file was never sampled")
        self.assertEqual(kit["provenance_class"], scanner.OWNER_DECLARED)

    def test_known_wrong_without_the_exclusion_a_secret_named_file_would_be_sampled(self):
        """The control: the same file read as an ordinary source file carries the other holder's line."""
        head = scanner._read_head(str(self.volume / "work/agent-kit/api_secret_store.py"))
        self.assertEqual(scanner._holders(head), ["Credential Owner"])
        self.assertEqual(scanner.excluded_class("work/agent-kit/api_secret_store.py")[0], "credential_file")
        self.assertEqual(scanner.excluded_class("work/agent-kit/tool.py"), ("", ""))
        self.assertEqual(scanner.excluded_class("work/agent-kit/README.md"), ("", ""))

    def test_secret_store_named_as_a_root_is_still_not_entered(self):
        self.assertFalse(any(row["path"].startswith(".ssh/") for row in self.rows))

    def test_exclusion_options_are_checked(self):
        for value in ("/abs=reason", "../up=reason", "PERSONAL", "=reason", "PERSONAL="):
            with self.subTest(value=value):
                self.assertEqual(scanner.main(["--volume", str(self.volume), "--output", str(self.root / "bad"),
                                               "--exclude-path", value]), 2)
                self.assertFalse((self.root / "bad").exists())
        destination = self.root / "skipping"
        self.assertEqual(scanner.main(["--volume", str(self.volume), "--output", str(destination), "--root", "work",
                                       "--skip-folder", "skills"]), 0)
        summary = json.loads((destination / "summary.json").read_text())
        self.assertEqual(summary["skipped_folders"].get("skills"), 1)
        self.assertNotIn("skill", summary["harness_kinds"])


class HarnessKindTest(unittest.TestCase):
    def test_paths_nominate_kinds_and_near_misses_do_not(self):
        cases = {
            "p/.claude/skills/x/SKILL.md": "skill", "p/skills/y/skill.md": "skill",
            "p/.claude/agents/a.md": "agent", "p/.github/agents/b.agent.md": "agent",
            "p/.opencode/agent/c.md": "agent", "p/.github/chatmodes/d.chatmode.md": "agent",
            "p/.claude/commands/deploy.md": "command", "p/.github/prompts/e.prompt.md": "command",
            "p/.gemini/commands/f.toml": "command", "p/plugin/hooks/hooks.json": "hook",
            "p/.claude/hooks/check.sh": "hook", "p/AGENTS.md": "instructions", "p/CLAUDE.md": "instructions",
            "p/.github/copilot-instructions.md": "instructions", "p/.github/instructions/g.instructions.md":
                "instructions", "p/.cursorrules": "rules", "p/.cursor/rules/h.mdc": "rules",
            "p/.clinerules/i.md": "rules", "p/.claude-plugin/plugin.json": "plugin",
            "p/.claude-plugin/marketplace.json": "marketplace", "p/gemini-extension.json": "plugin",
            "p/.github/workflows/ci.yml": "ci_workflow", "p/comfy/upscale_workflow.json": "workflow",
            "p/api/openapi.yaml": "openapi", "p/swagger.json": "openapi", "p/x.schema.json": "json_schema",
            "p/schemas/order.json": "json_schema", "p/tools.json": "tool_definition",
            "p/prompts/summary.md": "prompt_template", "p/system_prompt.txt": "prompt_template",
            "p/tests/fixtures/case.json": "test_fixture", "p/a.ipynb": "notebook", "p/data/rows.csv": "data_table",
            "p/scene.blend": "blender", "p/game/project.godot": "godot", "p/game/main.tscn": "godot",
            "p/fx/water.glsl": "shader", "p/m/robot.glb": "three_d_model", "p/icons/a.svg": "svg",
            "p/sfx/hit.wav": "audio", "p/song.mid": "midi",
        }
        for path, kind in cases.items():
            with self.subTest(path=path):
                self.assertEqual(scanner.harness_kind(path), kind)
        for near_miss in ("docs/agents/overview.md", "src/commands/run.md", "p/.ipynb_checkpoints/a-checkpoint.ipynb",
                          "p/main.py", "p/README.md", "p/hooks/pre-commit", "p/notes/skill-ideas.md"):
            with self.subTest(near_miss=near_miss):
                self.assertEqual(scanner.harness_kind(near_miss), "")

    def test_credential_names_are_classed_before_reading(self):
        for path, kind in {"a/.env": "dotenv", "a/.env.production": "dotenv", "a/prod.env": "dotenv",
                           "a/.mcp.json": "harness_settings", "h/.codex/config.toml": "harness_settings",
                           "h/.claude/settings.json": "harness_settings", "a/id_rsa.pub": "credential_file",
                           "a/server.pem": "key_material", "a/vault.kdbx": "key_material",
                           "a/client_secret_123.json": "credential_file", "a/.git-credentials": "credential_file",
                           "m/a.eml": "private_message", "m/people.vcf": "private_message",
                           "a/my_password_list.txt": "credential_file"}.items():
            with self.subTest(path=path):
                self.assertEqual(scanner.excluded_class(path)[0], kind)
        for ordinary in ("a/settings.json", "a/config.toml", "a/environment.yml", "a/keyboard.py", "a/tokenizer.py"):
            with self.subTest(ordinary=ordinary):
                self.assertEqual(scanner.excluded_class(ordinary), ("", ""))


if __name__ == "__main__":
    unittest.main()
