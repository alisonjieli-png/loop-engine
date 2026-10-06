"""The Baltor plugin package against OpenAI's submission rules, and each rule against a known-wrong package."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
import zipfile
import zlib

import build_chatgpt_app_package as package

ROOT = Path(__file__).resolve().parents[1]


def _png(path, width, height):
    """A valid one-colour PNG of the given size."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    rows = b"".join(b"\x00" + b"\xd9\x5b\x0f" * width for _ in range(height))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


class PackageRules(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="chatgpt-package-")
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name) / "chatgpt-app"
        shutil.copytree(package.PACKAGE, self.folder)

    def manifest(self):
        return json.loads((self.folder / "plugin.json").read_text())

    def write(self, value):
        (self.folder / "plugin.json").write_text(json.dumps(value))

    def interface(self, value):
        return value["extensions"]["com.openai"]["interface"]

    def test_the_committed_package_passes_every_rule(self):
        self.assertEqual(package.check(package.PACKAGE), [])
        manifest = json.loads((package.PACKAGE / "plugin.json").read_text())
        interface = self.interface(manifest)
        self.assertEqual(interface["supportURL"], "https://baltor.ai/support")
        self.assertEqual(len(interface["screenshots"]), len(interface["defaultPrompt"]))

    def test_each_rule_refuses_its_known_wrong_case(self):
        def listing(name, value):
            def change(manifest):
                self.interface(manifest)[name] = value
            return change

        def review(change_cases):
            def change(manifest):
                change_cases(manifest["extensions"]["com.openai"]["review"])
            return change
        cases = {
            "display name over 30": listing("displayName", "B" * 31),
            "two-line subtitle": listing("shortDescription", "Find skills\nand tools"),
            "no support page": lambda manifest: self.interface(manifest).pop("supportURL"),
            "plain HTTP privacy": listing("privacyPolicyURL", "http://baltor.ai/privacy"),
            "credentials in a URL": listing("termsOfServiceURL", "https://user@baltor.ai/terms"),
            "four starter prompts": listing("defaultPrompt", ["a", "b", "c", "d"]),
            "duplicate prompts": listing("defaultPrompt", ["Find a skill.", "find  a skill.", "Other."]),
            "an @mention": listing("defaultPrompt", ["Ask @baltor for a skill.", "b", "c"]),
            "pale brand colour": listing("brandColor", "#FFE8D6"),
            "dark colour on dark": listing("brandColorDark", "#2A2A2A"),
            "unknown category": listing("category", "Developer tools"),
            "21 capabilities": listing("capabilities", ["Search"] * 21),
            "a price in the listing": listing("longDescription", "Baltor Pro costs $29 a month."),
            "a dash in the listing": listing("shortDescription", "Skills — tools"),
            "a retired word": listing("longDescription", "Every component is reviewed."),
            "four positive cases": review(lambda value: value["test_cases"]["positive"].pop()),
            "two negative cases": review(lambda value: value["test_cases"]["negative"].pop()),
            "a case without its tools": review(lambda value: value["test_cases"]["positive"][0].pop("tools_triggered")),
            "a case naming an unknown tool": review(lambda value: value["test_cases"]["positive"][0].__setitem__(
                "tools_triggered", "provisioning_read")),
            "credentials in the package": review(lambda value: value.__setitem__("test_credentials", {"user": "x"})),
            "commerce declared": review(lambda value: value.__setitem__("commerce", True)),
            "lowercase country": lambda manifest: manifest["extensions"]["com.openai"]["publication"].__setitem__("countries", ["us"]),
            "no release notes": lambda manifest: manifest["extensions"]["com.openai"]["publication"].pop("release_notes"),
            "a name with capitals": lambda manifest: manifest.__setitem__("name", "Baltor"),
            "not a semantic version": lambda manifest: manifest.__setitem__("version", "1.0"),
            "an app reference": lambda manifest: manifest["extensions"]["com.openai"].__setitem__("apps", "./.app.json"),
            "a missing logo": listing("logo", "./assets/missing.png"),
            "a logo outside assets": listing("logo", "../logo.png"),
            "one screenshot short": listing("screenshots", ["./assets/screenshot-1.png", "./assets/screenshot-2.png"]),
        }
        good = self.manifest()
        for label, change in cases.items():
            wrong = copy.deepcopy(good)
            change(wrong)
            self.write(wrong)
            self.assertNotEqual(package.check(self.folder), [], label)
        self.write(good)
        self.assertEqual(package.check(self.folder), [])

    def test_images_and_server_rules_refuse_known_wrong_files(self):
        _png(self.folder / "assets" / "logo.png", 512, 500)
        self.assertTrue(any("square" in problem for problem in package.check(self.folder)))
        shutil.copy(package.PACKAGE / "assets" / "logo.png", self.folder / "assets" / "logo.png")
        _png(self.folder / "assets" / "screenshot-2.png", 700, 600)
        self.assertTrue(any("706" in problem for problem in package.check(self.folder)))
        _png(self.folder / "assets" / "screenshot-2.png", 706, 900)
        self.assertTrue(any("706" in problem for problem in package.check(self.folder)))
        shutil.copy(package.PACKAGE / "assets" / "screenshot-2.png", self.folder / "assets" / "screenshot-2.png")
        servers = json.loads((self.folder / "mcp.json").read_text())
        servers["mcpServers"]["baltor"]["url"] = "https://example.com/mcp"
        (self.folder / "mcp.json").write_text(json.dumps(servers))
        self.assertTrue(any("mcp.json" in problem for problem in package.check(self.folder)))
        (self.folder / "mcp.json").write_text((package.PACKAGE / "mcp.json").read_text())
        (self.folder / "notes.txt").write_text("private")
        self.assertTrue(any("notes.txt" in problem for problem in package.check(self.folder)))

    def test_the_archive_is_deterministic_and_holds_only_the_named_files(self):
        with tempfile.TemporaryDirectory() as folder:
            first, second = Path(folder) / "first.zip", Path(folder) / "second.zip"
            digest = package.build(first)
            self.assertEqual(package.build(second), digest)
            self.assertEqual(hashlib.sha256(first.read_bytes()).hexdigest(), digest)
            with zipfile.ZipFile(first) as archive:
                names = archive.namelist()
                self.assertEqual(names, sorted(names))
                self.assertEqual(set(names), set(package.entries()))
                self.assertNotIn("README.md", names)
                self.assertEqual(json.loads(archive.read("plugin.json")), json.loads((package.PACKAGE / "plugin.json").read_text()))


if __name__ == "__main__":
    unittest.main()
