"""The first-party Baltor library skill in integrations/baltor-library, checked as a customer receives it.

Kind: continuous integration check.

The folder integrations/baltor-library carries one skill, version 0.4.0, with a Claude Code plugin, a Codex
plugin and a Pi package around the same six files. This module holds the promises its README makes:

- the files are the pinned bytes of release.json, whose package digest is the digest of catalogue candidate
  baltor_library_client, and every manifest names the same version;
- every path a manifest declares stays inside the folder, and the skill's name matches its folder;
- the project skill folder named for each client is the folder that tools/install_selected_material.py places
  skills in, so the README and the placement profiles cannot drift apart;
- the configuration names the token variable that the setup page uses and never holds a token, and the client
  reads the token from that variable, sends it only in the request header and never prints it;
- the website serves the same six files byte for byte under /assets/baltor-library/, with their digests, and the
  client's own placement table names the folders the release names;
- the client's own offline tests pass, and the pinned client works against the service application of this
  revision, run in the same process with network connections refused: it fetches a package exactly, declares its
  effects in the header, and places a fetched skill byte for byte.

Each rule is a function that returns its problems, and each has a known-wrong control that must report one.
Nothing here starts a harness, reaches the network or reads a real credential.
"""
from __future__ import annotations

import asyncio
import contextlib
from email.message import Message
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import socket
import sys
import tempfile
import unittest
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "integrations" / "baltor-library"
SKILL_NAME = "baltor-library"
CLIENTS = ("claude-code", "codex", "opencode", "pi")
RECIPES = ROOT / "src" / "loop_engine" / "core" / "service_runtime" / "web_assets" / "client-recipes.json"
POLICY = ROOT / "src" / "loop_engine" / "forbidden_paths.json"
#: The frontmatter keys the four clients read from a skill definition. Another key is a sign that the file
#: was written for one client only.
FRONTMATTER_KEYS = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
SKILL_NAME_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
ORIGIN = "https://offline.invalid"
SERVED_ROOT = "/assets/baltor-library/"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(path: Path, name: str):
    """Import one file of the package under a private module name, writing no bytecode into the package."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    previous, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def skill_folder(package: Path) -> Path:
    return package / read_json(package / "release.json")["skill_folder"]


# ---------------------------------------------------------------------------
# Rules. Each returns a list of problems for the folder it is given.
# ---------------------------------------------------------------------------

def pin_problems(package: Path) -> list:
    """The files, the package digest, SHA256SUMS and every version agree with release.json."""
    from loop_engine.core.service_runtime.catalogue_packages import CataloguePackage, CataloguePackageFile
    release = read_json(package / "release.json")
    problems = []
    folder = skill_folder(package)
    # A bytecode cache is written by Python, ignored by git and never part of the package.
    present = sorted(path.relative_to(folder).as_posix() for path in folder.rglob("*")
                     if path.is_file() and "__pycache__" not in path.relative_to(folder).parts)
    pinned = sorted(row["path"] for row in release["files"])
    if present != pinned:
        problems.append(f"the skill folder holds {present}, the release pins {pinned}")
    for row in release["files"]:
        path = folder / row["path"]
        if not path.is_file():
            continue
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != row["digest"] or len(data) != row["size_bytes"]:
            problems.append(f"{row['path']} is not the pinned file")
    package_record = CataloguePackage(tuple(CataloguePackageFile(row["path"], row["digest"], row["size_bytes"],
                                                                 row["media_type"], row["role"])
                                            for row in release["files"]), release["package"]["body_form"])
    if package_record.package_digest != release["package"]["package_digest"]:
        problems.append("the pinned files do not make the pinned package digest")
    sums = (package / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    expected = [f"{row['digest']}  {release['skill_folder']}/{row['path']}" for row in release["files"]]
    if sums != expected:
        problems.append("SHA256SUMS does not list the pinned digests")
    version = release["version"]
    script = (folder / "scripts" / "baltor.py").read_text(encoding="utf-8")
    if f"VERSION = '{version}'" not in script:
        problems.append(f"the client does not declare version {version}")
    manifests = release["manifests"]
    claude_plugin = read_json(package / manifests["claude_code_plugin"])
    claude_market = read_json(package / manifests["claude_code_marketplace"])
    codex_plugin = read_json(package / manifests["codex_plugin"])
    pi_package = read_json(package / manifests["pi_package"])
    entries = [entry for entry in claude_market.get("plugins", []) if entry.get("name") == release["name"]]
    for label, value in (("Claude Code plugin", claude_plugin.get("version")),
                         ("Claude Code marketplace entry", entries[0].get("version") if entries else None),
                         ("Codex plugin", codex_plugin.get("version")), ("Pi package", pi_package.get("version"))):
        if value != version:
            problems.append(f"the {label} names version {value!r}, the release pins {version}")
    for label, value in (("Claude Code plugin", claude_plugin.get("name")), ("Codex plugin", codex_plugin.get("name")),
                         ("Pi package", pi_package.get("name"))):
        if value != release["name"]:
            problems.append(f"the {label} is named {value!r}")
    return problems


def served_copy_problems(package: Path) -> list:
    """Every file of the skill is served at /assets/baltor-library/<path> with the same bytes, and the served
    SHA256SUMS names each file's digest by its path inside the skill folder."""
    from loop_engine.core.service_runtime import web_pages
    release = read_json(package / "release.json")
    folder = skill_folder(package)
    problems = []

    def served(address):
        if address not in web_pages.WEB_ASSETS:
            return None
        return web_pages.read_packaged_asset(web_pages.WEB_ASSETS[address][0])
    for row in release["files"]:
        body = served(SERVED_ROOT + row["path"])
        if body is None:
            problems.append(f"the website does not serve {row['path']}")
        elif body != (folder / row["path"]).read_bytes():
            problems.append(f"the website serves other bytes for {row['path']}")
    sums = served(SERVED_ROOT + "SHA256SUMS")
    expected = "".join(f"{row['digest']}  {row['path']}\n" for row in release["files"]).encode()
    if sums != expected:
        problems.append("the served SHA256SUMS does not list the pinned digests by their paths in the skill folder")
    listed = {address[len(SERVED_ROOT):] for address in web_pages.WEB_ASSETS if address.startswith(SERVED_ROOT)}
    if listed != {row["path"] for row in release["files"]} | {"SHA256SUMS"}:
        problems.append(f"the website serves {sorted(listed)} under {SERVED_ROOT}")
    return problems


def placement_table_problems(package: Path, table: dict) -> list:
    """The client's own table of skill folders, which its install command writes to, is the release's table."""
    release = read_json(package / "release.json")
    problems = []
    for client in CLIENTS:
        for scope in ("project", "user"):
            placed = f"{table.get(client, {}).get(scope)}/{release['name']}"
            if placed != release["native_skill_folders"][client][scope]:
                problems.append(f"{client} {scope}: the client places in {placed!r}, the release names "
                                f"{release['native_skill_folders'][client][scope]!r}")
    return problems


def inside(package: Path, declared: str) -> bool:
    """A declared manifest path starts with ./, names no parent folder and exists inside the folder."""
    if not isinstance(declared, str) or not declared.startswith("./") or ".." in declared.split("/"):
        return False
    target = (package / declared).resolve()
    return target.exists() and (target == package.resolve() or package.resolve() in target.parents)


def manifest_problems(package: Path) -> list:
    """Every manifest path the clients follow stays inside the folder and reaches the one skills folder."""
    release = read_json(package / "release.json")
    manifests = release["manifests"]
    problems = []
    claude_market = read_json(package / manifests["claude_code_marketplace"])
    for entry in claude_market.get("plugins", []):
        if not inside(package, entry.get("source")):
            problems.append(f"the Claude Code marketplace source {entry.get('source')!r} leaves the folder")
    codex_plugin = read_json(package / manifests["codex_plugin"])
    if not inside(package, codex_plugin.get("skills")) or (package / codex_plugin["skills"]).resolve() != (
            package / "skills").resolve():
        problems.append(f"the Codex plugin skills path {codex_plugin.get('skills')!r} is not ./skills/")
    codex_market = read_json(package / manifests["codex_marketplace"])
    for entry in codex_market.get("plugins", []):
        source = entry.get("source") or {}
        if source.get("source") != "local" or not inside(package, source.get("path")):
            problems.append(f"the Codex marketplace source {source!r} leaves the folder")
    pi_package = read_json(package / manifests["pi_package"])
    skills = (pi_package.get("pi") or {}).get("skills")
    if not isinstance(skills, list) or not skills or any(not inside(package, path) for path in skills):
        problems.append(f"the Pi package skills paths {skills!r} leave the folder")
    if pi_package.get("private") is not True:
        problems.append("the Pi package is not marked private, so a registry could publish it")
    return problems


def frontmatter_problems(folder: Path) -> list:
    """The skill definition carries a name equal to its folder, a description and nothing client-specific."""
    text = (folder / "SKILL.md").read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if not text.startswith("---\n") or len(parts) < 3:
        return ["SKILL.md does not start with frontmatter"]
    fields = yaml.safe_load(parts[1])
    problems = []
    name = fields.get("name")
    if name != folder.name or not isinstance(name, str) or not SKILL_NAME_PATTERN.fullmatch(name) or len(name) > 64:
        problems.append(f"the skill name {name!r} does not match its folder {folder.name!r}")
    description = fields.get("description")
    if not isinstance(description, str) or not 1 <= len(description) <= 1024:
        problems.append("the description is missing or longer than 1,024 characters")
    unknown = sorted(set(fields) - FRONTMATTER_KEYS)
    if unknown:
        problems.append(f"the frontmatter has keys another client may refuse: {unknown}")
    return problems


def native_folder_problems(package: Path, profiles: dict) -> list:
    """The project folder of each client is where the installer's placement profile puts a skill."""
    release = read_json(package / "release.json")
    readme = (package / "README.md").read_text(encoding="utf-8")
    problems = []
    folders = release["native_skill_folders"]
    if sorted(folders) != sorted(CLIENTS):
        problems.append(f"the release names folders for {sorted(folders)}, not for {list(CLIENTS)}")
    for client in CLIENTS:
        expected = "/".join((*profiles[client].location_for("skill").directory_segments, release["name"]))
        named = folders.get(client, {})
        if named.get("project") != expected:
            problems.append(f"{client}: the release names {named.get('project')!r}, the placement profile {expected!r}")
        for scope in ("project", "user"):
            if not named.get(scope) or named[scope] not in readme:
                problems.append(f"{client}: the README does not name the {scope} folder {named.get(scope)!r}")
    return problems


def credential_problems(package: Path, recipes_text: str, secret_patterns: list) -> list:
    """The configuration names the setup page's token variable, and no file holds a token-shaped value."""
    release = read_json(package / "release.json")
    folder = skill_folder(package)
    example = read_json(folder / "assets" / "client.example.json")
    problems = []
    if set(example) != {"record_type", "origin", "credential_environment", "authority_effects"}:
        problems.append(f"the example configuration has the fields {sorted(example)}")
    variable = example.get("credential_environment")
    if not isinstance(variable, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,79}", variable):
        problems.append("the example configuration does not name an environment variable")
    if variable != release["configuration"]["credential_environment"]:
        problems.append("the example configuration and the release name different variables")
    used = set(re.findall(r"BALTOR_[A-Z_]+", recipes_text))
    if used != {variable}:
        problems.append(f"the setup page uses {sorted(used)}, the skill uses {variable!r}")
    for path in sorted(package.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in secret_patterns:
            if re.search(pattern, text):
                problems.append(f"{path.relative_to(package)} holds a value shaped like a secret")
    return problems


# ---------------------------------------------------------------------------
# The checks
# ---------------------------------------------------------------------------

def copied_package(directory: str) -> Path:
    target = Path(directory) / "baltor-library"
    shutil.copytree(PACKAGE, target)
    return target


class PinnedReleaseChecks(unittest.TestCase):
    """The folder is exactly the pinned release, and each rule reports a known-wrong copy."""

    def test_the_folder_is_the_pinned_release(self):
        self.assertEqual(pin_problems(PACKAGE), [])

    def test_a_changed_byte_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            copy = copied_package(directory)
            path = skill_folder(copy) / "SKILL.md"
            path.write_bytes(path.read_bytes().replace(b"Baltor", b"Baltor ", 1))
            self.assertIn("SKILL.md is not the pinned file", pin_problems(copy))

    def test_an_extra_file_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            copy = copied_package(directory)
            (skill_folder(copy) / "agents").mkdir()
            (skill_folder(copy) / "agents" / "openai.yaml").write_text("interface: {}\n", encoding="utf-8")
            self.assertTrue(any("the skill folder holds" in problem for problem in pin_problems(copy)))

    def test_a_manifest_version_that_moved_alone_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            copy = copied_package(directory)
            manifest = copy / ".codex-plugin" / "plugin.json"
            value = read_json(manifest)
            value["version"] = "0.3.1"
            manifest.write_text(json.dumps(value), encoding="utf-8")
            self.assertTrue(any("Codex plugin names version '0.3.1'" in problem for problem in pin_problems(copy)))

    def test_the_package_digest_is_the_pinned_version(self):
        # Version 0.4.0 replaced the 0.3.0 catalogue candidate's bytes; the new bytes need their own review.
        release = read_json(PACKAGE / "release.json")
        self.assertEqual(release["package"]["catalogue_identity"], "baltor_library_client")
        self.assertEqual(release["package"]["package_digest"],
                         "c27908e828db2ca64e1749bee0215a6253c5bb7a1ec03e771d1e3bbbfc224d20")
        self.assertEqual(release["source"]["previous_package_digest"],
                         "ab45e58b1e1a601b4bc97ab0df84e4c4b37ca814b6c1c9bba5dfdc32578e3926")
        self.assertEqual(release["package"]["catalogue_publication"], "not_published")

    def test_the_website_serves_the_pinned_files(self):
        self.assertEqual(served_copy_problems(PACKAGE), [])

    def test_a_served_byte_that_differs_is_reported(self):
        from loop_engine.core.service_runtime import web_pages
        original = web_pages.read_packaged_asset

        def changed(name):
            body = original(name)
            return body + b"# retyped" if name.endswith("baltor.py.txt") else body
        with mock.patch.object(web_pages, "read_packaged_asset", changed):
            self.assertIn("the website serves other bytes for scripts/baltor.py", served_copy_problems(PACKAGE))

    def test_the_client_places_skills_where_the_release_says(self):
        module = load_module(skill_folder(PACKAGE) / "scripts" / "baltor.py", "baltor_library_client_table")
        self.assertEqual(placement_table_problems(PACKAGE, module.NATIVE_SKILL_ROOTS), [])
        moved = {**module.NATIVE_SKILL_ROOTS, "codex": {"project": ".codex/skills", "user": "~/.codex/skills"}}
        self.assertTrue(placement_table_problems(PACKAGE, moved))


class ManifestChecks(unittest.TestCase):
    """Each client's manifest reaches the one skills folder and nothing outside the package."""

    def test_every_manifest_path_stays_inside(self):
        self.assertEqual(manifest_problems(PACKAGE), [])

    def test_a_path_that_leaves_the_folder_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            copy = copied_package(directory)
            manifest = copy / ".codex-plugin" / "plugin.json"
            value = read_json(manifest)
            value["skills"] = "../skills/"
            manifest.write_text(json.dumps(value), encoding="utf-8")
            (Path(directory) / "skills").mkdir()
            self.assertTrue(any("Codex plugin skills path" in problem for problem in manifest_problems(copy)))

    def test_a_publishable_pi_package_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            copy = copied_package(directory)
            value = read_json(copy / "package.json")
            value.pop("private")
            (copy / "package.json").write_text(json.dumps(value), encoding="utf-8")
            self.assertIn("the Pi package is not marked private, so a registry could publish it",
                          manifest_problems(copy))

    def test_the_skill_definition_suits_every_client(self):
        self.assertEqual(frontmatter_problems(skill_folder(PACKAGE)), [])

    def test_a_folder_that_differs_from_the_skill_name_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            renamed = Path(directory) / "baltor-client"
            shutil.copytree(skill_folder(PACKAGE), renamed)
            self.assertTrue(any("does not match its folder" in problem for problem in frontmatter_problems(renamed)))

    def test_the_existing_integration_structure_check_passes(self):
        """integrations/tests/check_integrations.py reads every skill under integrations, this one included."""
        module = load_module(ROOT / "integrations" / "tests" / "check_integrations.py", "check_integrations_for_ci")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            module.main()
        report = json.loads(output.getvalue())
        self.assertTrue(report["all_passed"])
        self.assertGreaterEqual(report["skills"], 7)


class NativeFolderChecks(unittest.TestCase):
    """The README's folders are the placement profiles' folders."""

    @classmethod
    def setUpClass(cls):
        import install_selected_material
        cls.profiles = install_selected_material.CLIENT_LAYOUT_PROFILES

    def test_each_client_folder_matches_its_placement_profile(self):
        self.assertEqual(native_folder_problems(PACKAGE, self.profiles), [])

    def test_a_folder_the_profile_does_not_use_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            copy = copied_package(directory)
            release = read_json(copy / "release.json")
            release["native_skill_folders"]["opencode"]["project"] = ".opencode/skill/baltor-library"
            (copy / "release.json").write_text(json.dumps(release), encoding="utf-8")
            self.assertTrue(any(problem.startswith("opencode: the release names")
                                for problem in native_folder_problems(copy, self.profiles)))


class CredentialChecks(unittest.TestCase):
    """The token comes from the variable the configuration names, reaches only the header and is never printed."""

    TOKEN = "synthetic-token-for-the-integration-check"

    @classmethod
    def setUpClass(cls):
        cls.client = load_module(skill_folder(PACKAGE) / "scripts" / "baltor.py", "baltor_library_client_for_ci")
        cls.patterns = read_json(POLICY)["secret_patterns"]

    def test_the_configuration_names_the_setup_page_variable_and_holds_no_secret(self):
        self.assertEqual(credential_problems(PACKAGE, RECIPES.read_text(encoding="utf-8"), self.patterns), [])

    def test_a_configuration_that_holds_a_token_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            copy = copied_package(directory)
            path = skill_folder(copy) / "assets" / "client.example.json"
            value = read_json(path)
            value["token"] = "Bearer " + "a" * 32
            path.write_text(json.dumps(value), encoding="utf-8")
            problems = credential_problems(copy, RECIPES.read_text(encoding="utf-8"), self.patterns)
            self.assertTrue(any("has the fields" in problem for problem in problems))
            self.assertTrue(any("shaped like a secret" in problem for problem in problems))

    def test_a_variable_the_setup_page_does_not_use_is_reported(self):
        problems = credential_problems(PACKAGE, '{"token_env": "BALTOR_OTHER_TOKEN"}', self.patterns)
        self.assertTrue(any("the setup page uses" in problem for problem in problems))

    def config_file(self, directory: str, **changes) -> Path:
        value = {"record_type": "baltor_library_client_configuration/v2", "origin": ORIGIN,
                 "credential_environment": "BALTOR_SERVICE_TOKEN", "authority_effects": ["reads_fs"], **changes}
        path = Path(directory) / "client.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def run_main(self, arguments, environment):
        stdout, stderr = io.StringIO(), io.StringIO()
        stdout.buffer = io.BytesIO()
        with mock.patch.dict(os.environ, environment, clear=False), \
             mock.patch("sys.stdout", stdout), mock.patch("sys.stderr", stderr):
            code = self.client.main(arguments)
        return code, stdout.buffer.getvalue().decode("utf-8") + stdout.getvalue(), stderr.getvalue()

    def test_the_token_is_read_from_the_named_variable_and_reaches_only_the_header(self):
        capabilities = {"record_type": "service_capabilities/v1", "api_version": "v1",
                        "retrieval": {"request_record_type": "service_retrieval_request/v2", "modes": ["lexical"],
                                      "returns_bodies": False},
                        "library": {"provisioning_request_record_types": ["service_provisioning_request/v2"],
                                    "step_effects": ["reads_fs"]},
                        "delivery": {"download_endpoint": "/api/v1/download", "package_files": "download_by_path",
                                     "body_format": "utf8_text", "download_bytes": 1024},
                        "limits": {"search_results": 5, "request_bytes": 65536, "response_bytes": 65536}}
        answers = [("capabilities", capabilities),
                   ("retrieval", {"record_type": "service_retrieval_result/v1", "bodies_loaded": False, "hits": []})]
        sent = []

        class Transport:
            def open(self, request, timeout):
                sent.append(request)
                operation, result = answers.pop(0)
                body = json.dumps({"record_type": "service_http_result/v1", "operation": operation,
                                   "result": result}).encode()
                return FakeResponse(200, request.full_url, {"Content-Type": "application/json"}, body)

        original = self.client.Client
        with tempfile.TemporaryDirectory() as directory, \
             mock.patch.object(self.client, "Client", lambda config, key: original(config, key, Transport())):
            code, out, err = self.run_main(["--config", str(self.config_file(directory)), "search", "review inputs",
                                            "--limit", "3"], {"BALTOR_SERVICE_TOKEN": self.TOKEN})
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["hits"], [])
        self.assertNotIn(self.TOKEN, out + err)
        self.assertIsNone(sent[0].get_header("Authorization"), "the capabilities read sends no token")
        self.assertEqual(sent[1].get_header("Authorization"), "Bearer " + self.TOKEN)
        self.assertNotIn(self.TOKEN.encode(), sent[1].data)

    def test_a_token_on_the_command_line_is_refused_without_echo(self):
        with tempfile.TemporaryDirectory() as directory, \
             mock.patch.object(self.client, "Client", side_effect=AssertionError("no request may start")):
            code, out, err = self.run_main(["--config", str(self.config_file(directory)), "search", self.TOKEN],
                                           {"BALTOR_SERVICE_TOKEN": self.TOKEN})
        self.assertEqual(code, 2)
        self.assertIn("credential_in_arguments", err)
        self.assertNotIn(self.TOKEN, out + err)

    def test_a_configuration_with_a_token_field_is_refused(self):
        with tempfile.TemporaryDirectory() as directory, \
             mock.patch.object(self.client, "Client", side_effect=AssertionError("no request may start")):
            code, out, err = self.run_main(["--config", str(self.config_file(directory, token=self.TOKEN)),
                                            "capabilities"], {})
        self.assertEqual(code, 2)
        self.assertIn("configuration_shape", err)
        self.assertNotIn(self.TOKEN, out + err)

    def test_a_missing_variable_stops_before_any_request(self):
        with tempfile.TemporaryDirectory() as directory, \
             mock.patch.object(self.client, "Client", side_effect=AssertionError("no request may start")):
            code, _out, err = self.run_main(["--config", str(self.config_file(directory)), "search", "review"],
                                            {"BALTOR_SERVICE_TOKEN": ""})
        self.assertEqual(code, 2)
        self.assertIn("credential_missing_or_invalid", err)


class FakeResponse(io.BytesIO):
    """The part of an HTTP response the pinned client reads."""

    def __init__(self, status, url, headers, body, lost=False):
        super().__init__(body)
        self.status, self.url, self.lost = status, url, lost
        self.headers = Message()
        for name, values in headers.items():
            for value in (values if isinstance(values, list) else [values]):
                self.headers[name] = value

    def geturl(self):
        return self.url

    def read1(self, size=-1):
        if self.lost:
            raise OSError("the response was lost after the service answered")
        return super().read1(size)


class InProcessOpener:
    """Carries the client's requests to the service application in this process. No socket is opened."""

    def __init__(self, application):
        import httpx
        self.loop = asyncio.new_event_loop()
        self.http = httpx.AsyncClient(transport=httpx.ASGITransport(app=application), base_url=ORIGIN)
        self.requests = []
        self.lose_next_download = False

    def open(self, request, timeout):
        self.requests.append(request)
        response = self.loop.run_until_complete(self.http.request(
            request.get_method(), request.full_url, headers=dict(request.header_items()), content=request.data))
        lost = self.lose_next_download and request.full_url.endswith("/download")
        if lost:
            self.lose_next_download = False
        headers = {}
        for name, value in response.headers.multi_items():
            headers.setdefault(name, []).append(value)
        return FakeResponse(response.status_code, str(response.url), headers, response.content, lost=lost)

    def close(self):
        self.loop.run_until_complete(self.http.aclose())
        self.loop.close()


class ServiceContractChecks(unittest.TestCase):
    """The pinned client against this revision's service application, with every network connection refused."""

    FILES = (("SKILL.md", b"# Clean supplier names\nFollow the supplied cleanup steps.\n", "text/markdown",
              "skill_definition"),
             ("assets/example.bin", b"\x00\xff\x80\r\n", "application/octet-stream", "skill_asset"))
    PROCESS = (("scripts/clean.sh", b"#!/bin/sh\nprintf never-run\n", "text/x-shellscript", "skill_script"),)

    def setUp(self):
        from loop_engine.core.service_runtime.catalogue_release_checks import Fixture, bundle_line
        from loop_engine.core.service_runtime.http import ServiceHttpApplication, ServiceHttpConfiguration
        from loop_engine.core.service_runtime.http_auth import ServiceHttpAuthentication
        guards = (mock.patch.object(socket.socket, "connect", side_effect=AssertionError("network refused")),
                  mock.patch.object(socket.socket, "connect_ex", side_effect=AssertionError("network refused")),
                  mock.patch.object(socket, "create_connection", side_effect=AssertionError("network refused")),
                  mock.patch.object(socket, "getaddrinfo", side_effect=AssertionError("name lookup refused")))
        for guard in guards:
            guard.start()
            self.addCleanup(guard.stop)
        temporary = tempfile.TemporaryDirectory(prefix="baltor-library-service-")
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.case = Fixture(self.folder / "service")
        self.case._bytes = {"supplier_cleanup": tuple(row[1] for row in self.FILES),
                            "supplier_runner": tuple(row[1] for row in self.PROCESS)}
        runner = bundle_line("supplier_runner", self.PROCESS, effects=("spawns_process",))
        self.runner_digest = runner["reference"]["digest"]
        self.case.publish([bundle_line("supplier_cleanup", self.FILES, effects=("reads_fs",)), runner])
        application = ServiceHttpApplication(self.case.runtime, self.case.binding(),
                                             ServiceHttpConfiguration(ORIGIN, ("offline.invalid",)),
                                             ServiceHttpAuthentication())
        self.addCleanup(application._workers.shutdown, wait=True)
        self.opener = InProcessOpener(application.create_app())
        self.addCleanup(self.opener.close)
        self.module = load_module(skill_folder(PACKAGE) / "scripts" / "baltor.py", "baltor_library_client_service")
        config = {"record_type": "baltor_library_client_configuration/v2", "origin": ORIGIN,
                  "credential_environment": "BALTOR_SERVICE_TOKEN", "authority_effects": ["reads_fs"]}
        self.client = self.module.Client(config, self.case.key.key, opener=self.opener)
        self.client.handshake()

    def usage_records(self) -> int:
        runtime = self.case.runtime
        return runtime.usage_for(runtime.authenticate_key(self.case.key.key))["records"]

    def selection(self):
        found = self.client.search("supplier cleanup", 5)
        hit = next(hit for hit in found["hits"] if hit["reference"]["identity"] == "supplier_cleanup")
        return found, hit["reference"]["body_digest"]

    def test_a_package_fetch_is_exact_and_counts_once_across_an_exact_retry(self):
        found, digest = self.selection()
        self.assertEqual(self.usage_records(), 0, "a search is not a download")
        receipt = self.module.fetch(self.client, "supplier_cleanup", digest, "one-logical-read",
                                    self.folder / "first", found)
        self.assertTrue(receipt["complete"])
        self.assertFalse(receipt["installed"])
        self.assertFalse(receipt["executed"])
        for path, data, _media, _role in self.FILES:
            self.assertEqual((self.folder / "first" / "payload" / path).read_bytes(), data)
        self.assertEqual(self.usage_records(), 1)
        self.module.fetch(self.client, "supplier_cleanup", digest, "one-logical-read", self.folder / "retry", found)
        self.assertEqual(self.usage_records(), 1, "the same item version is one download")
        for request in self.opener.requests:
            if request.data:
                sent = json.loads(request.data)
                # The configured effects travel in the header, so the service marks what it shows.
                self.assertNotIn("authority_effects", sent)
                self.assertEqual(request.get_header("Baltor-step-effects"), "reads_fs")
                self.assertNotIn("library_tiers", sent)
        for path in (self.folder / "first").rglob("*.json"):
            self.assertNotIn(self.case.key.key, path.read_text(encoding="utf-8"))

    def test_a_lost_response_keeps_its_request_identity_for_the_retry(self):
        found, digest = self.selection()
        self.opener.lose_next_download = True
        with self.assertRaises(self.module.Refusal) as caught:
            self.module.fetch(self.client, "supplier_cleanup", digest, "lost-response", self.folder / "lost", found)
        self.assertEqual(caught.exception.code, "transport_failed")
        failure = json.loads((self.folder / "lost" / "failure.json").read_text(encoding="utf-8"))
        self.assertEqual((failure["request_id"], failure["usage_commitment"]), ("lost-response", "not_asserted"))
        counted = self.usage_records()
        self.assertEqual(counted, 1, "the service counted the read before the response was lost")
        self.module.fetch(self.client, "supplier_cleanup", digest, "lost-response", self.folder / "again", found)
        self.assertEqual(self.usage_records(), counted)

    def test_a_stale_digest_and_an_undeclared_effect_are_refused_without_usage(self):
        with self.assertRaises(self.module.Refusal) as caught:
            self.client.manifest("supplier_cleanup", "0" * 64)
        self.assertEqual(caught.exception.code, "service_refused:item_unavailable")
        # The runner declares spawns_process, which this configuration does not declare. Search shows it, marked
        # with the effect to declare; the client refuses to fetch it, and the service refuses its body.
        found = self.client.search("supplier runner", 5)
        runner = next(hit for hit in found["hits"] if hit["reference"]["identity"] == "supplier_runner")
        self.assertEqual(runner["effects_to_declare"], ["spawns_process"])
        self.assertEqual(self.client.manifest("supplier_runner", self.runner_digest)["effects_to_declare"],
                         ["spawns_process"])
        with self.assertRaises(self.module.Refusal) as caught:
            self.module.fetch(self.client, "supplier_runner", self.runner_digest, "runner", self.folder / "runner", found)
        self.assertEqual((caught.exception.code, caught.exception.effects), ("step_effects_not_configured",
                                                                            ["spawns_process"]))
        with self.assertRaises(self.module.Refusal) as caught:
            self.client.download("supplier_runner", self.runner_digest, "runner", self.runner_digest, 64,
                                 "scripts/clean.sh")
        self.assertEqual((caught.exception.code, caught.exception.effects),
                         ("service_refused:step_effects_required", ["spawns_process"]))
        self.assertEqual(self.usage_records(), 0)

    def test_a_fetched_skill_is_installed_byte_for_byte_and_verified(self):
        found, digest = self.selection()
        self.module.fetch(self.client, "supplier_cleanup", digest, "install-me", self.folder / "staged", found)
        project = self.folder / "project"
        project.mkdir()
        record = self.module.install(self.folder / "staged", "opencode", "project", project)
        placed = project / ".opencode" / "skills" / record["native_name"]
        self.assertEqual(record["native_name"], "supplier-cleanup")
        skill = (placed / "SKILL.md").read_bytes()
        # The served SKILL.md has no front matter, so a generated name and description come first, then the
        # published bytes unchanged; the record says how long the header is.
        self.assertTrue(skill.endswith(self.FILES[0][1]))
        self.assertEqual(len(skill) - record["files"][[row["path"] for row in record["files"]].index("SKILL.md")]
                         ["header_bytes"], len(self.FILES[0][1]))
        self.assertEqual((placed / "assets" / "example.bin").read_bytes(), self.FILES[1][1])
        self.assertTrue(self.module.verify("opencode", "supplier-cleanup", "project", project)["verified"])
        self.assertEqual(self.usage_records(), 1)


def load_tests(loader, standard_tests, pattern):
    """Add the client's own offline tests, read from the pinned file, to this module's tests."""
    verification = load_module(skill_folder(PACKAGE) / "verification" / "test_client.py",
                               "baltor_library_verification")
    standard_tests.addTests(loader.loadTestsFromModule(verification))
    return standard_tests


if __name__ == "__main__":
    unittest.main()
