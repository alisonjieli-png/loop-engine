"""Checks of the container image card format: the library reader, the registry reader, the OCI documents, the
documentation facts, the contract and README writer with its shipped helper, the registry check and the smoke run.

The registry is a fake that answers the way Docker Hub does (a bearer challenge, a token realm, HEAD for a tag,
documents by digest through the blob endpoint), so nothing here reads the network or runs an engine.

Known-wrong controls: two entries with one build context fall back to their tags; a tag named twice, an entry with
no commit and a line outside a field are refused; a document whose bytes differ from its digest, a redirect to an
undeclared host and a counted manifest read below the allowance reserve are refused; a token never reaches the
request log; an attestation manifest is not a platform; an example value of the documentation is never taken; a
README that lost or gained a row disagrees with its contract; inputs that break the contract are refused and a
credential's value is never rendered; a tag rebuilt since, or a config that says something else, fails the
registry check; stale and failed evidence is refused by name.
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
import tempfile
import unittest
import unittest.mock
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tools", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from container_image_cards import cards, docs, library, oci, registry, smoke, verify  # noqa: E402

COMMIT = "a" * 40
LIBRARY_TEXT = f"""# this file is generated for the tests
Maintainers: Example Maintainers <maintainers@example.invalid> (@example),
             Second Maintainer (@second)
GitRepo: https://github.com/example/docker-demo.git

Tags: 2.4.1, 2.4, 2, latest
SharedTags: stable
Architectures: amd64, arm64v8
GitCommit: {COMMIT}
Directory: 2/debian

# an alpine family
Tags: 2.4.1-alpine, 2-alpine, alpine
Architectures: amd64
GitCommit: {"b" * 40}
Directory: 2/alpine

Tags: 1.9.9, 1.9, 1
Architectures: amd64, arm32v7
GitCommit: {"c" * 40}
Directory: 1/debian
arm32v7-Directory: 1/debian-arm
"""
DOCS_CONTENT = """# What is demo?

Demo serves pages.

# How to use this image

```console
$ docker run --name some-demo -e DEMO_PASSWORD=mysecretpassword -e DEMO_MODE=fast -d demo
```

## Environment Variables

### `DEMO_USER`

The user.

### `DEMO_PASSWORD`

Required. Never shown here: the example's value is not a fact a card takes.
"""
DOCS_FILES = {docs.SUMMARY_FILE: b"Demo serves pages over HTTP.\n",
              docs.METADATA_FILE: b'{"hub": {"categories": ["web-servers"]}}\n',
              docs.CONTENT_FILE: DOCS_CONTENT.encode(),
              docs.LICENCE_FILE: b"View [license information](https://example.invalid/LICENSE) for the software.\n",
              docs.REPOSITORY_FILE: b"https://github.com/example/docker-demo\n"}
SECRET_VALUE = "ghp_" + "Q" * 30


def digest_of(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def document(value) -> bytes:
    return json.dumps(value, indent=2).encode()


def config(architecture: str, *, variant=None, env_extra=(), label_extra=None, user="", cmd=("demo", "serve"),
           entrypoint=("docker-entrypoint.sh",)):
    labels = {"maintainer": "Example Maintainers"}
    labels.update(label_extra or {})
    value = {"architecture": architecture, "os": "linux",
             "config": {"Env": ["PATH=/usr/local/bin:/usr/bin:/bin", "DEMO_VERSION=2.4.1", "DEMO_ADMIN_PASSWORD=x1",
                                f"DEMO_ARCH={architecture}", *env_extra],
                        "Entrypoint": list(entrypoint) if entrypoint else None, "Cmd": list(cmd) if cmd else None,
                        "WorkingDir": "/srv",
                        "User": user, "ExposedPorts": {"8080/tcp": {}, "53/udp": {}},
                        "Volumes": {"/var/lib/demo": {}}, "StopSignal": "SIGQUIT", "Labels": labels,
                        "Healthcheck": {"Test": ["CMD", "demo", "health"], "Interval": 30000000000,
                                        "Retries": 3}},
             "history": [{"created_by": "RUN curl https://example.invalid/install.sh | sh"}],
             "rootfs": {"type": "layers", "diff_ids": ["sha256:" + "1" * 64]}}
    if variant:
        value["variant"] = variant
    return document(value)


class FakeHub:
    """A registry answering like Docker Hub: a bearer challenge without a token, a token from the realm, tags by
    HEAD, documents by digest through the blob endpoint (and the manifest endpoint), the pull allowance header."""

    HOST, REALM = registry.DOCKER_HUB.host, registry.DOCKER_HUB.token_hosts[0]
    TOKEN = "fake-token-" + "z" * 24

    def __init__(self):
        self.blobs, self.tags, self.requests, self.served_by_blob = {}, {}, [], True
        self.remaining = 100
        self.tampered = set()
        self.redirect_to = None

    def add(self, data: bytes) -> str:
        digest = digest_of(data)
        self.blobs[digest] = data
        return digest

    def image(self, name: str, tag: str, platforms: list, *, attestation: bool = True) -> str:
        """Push an index for platforms [(os, architecture, variant, config bytes, annotations)]; returns its digest."""
        descriptors = []
        for os_name, architecture, variant, config_bytes, annotations in platforms:
            config_digest = self.add(config_bytes)
            layer = "sha256:" + hashlib.sha256(f"{name}{architecture}".encode()).hexdigest()
            manifest = document({"schemaVersion": 2, "mediaType": registry.OCI_MANIFEST,
                                 "config": {"mediaType": registry.OCI_CONFIG, "digest": config_digest,
                                            "size": len(config_bytes)},
                                 "layers": [{"mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                                             "digest": layer, "size": 1000 + len(architecture)}],
                                 "annotations": annotations})
            platform = {"os": os_name, "architecture": architecture}
            if variant:
                platform["variant"] = variant
            descriptors.append({"mediaType": registry.OCI_MANIFEST, "digest": self.add(manifest),
                                "size": len(manifest), "platform": platform, "annotations": annotations})
            if attestation:
                statement = document({"schemaVersion": 2, "mediaType": registry.OCI_MANIFEST, "layers": []})
                descriptors.append({"mediaType": registry.OCI_MANIFEST, "digest": self.add(statement),
                                    "size": len(statement), "platform": {"os": "unknown", "architecture": "unknown"},
                                    "annotations": {"vnd.docker.reference.type": "attestation-manifest"}})
        index = document({"schemaVersion": 2, "mediaType": registry.OCI_INDEX, "manifests": descriptors})
        digest = self.add(index)
        self.tags[(name, tag)] = digest
        return digest

    def __call__(self, method, url, headers, credential, maximum_bytes):
        self.requests.append((method, url, credential))
        parts = registry.urllib.parse.urlsplit(url)
        if parts.hostname == self.REALM:
            return registry.Answer(200, {}, json.dumps({"token": self.TOKEN, "expires_in": 300}).encode())
        if credential != self.TOKEN:
            challenge = f'Bearer realm="https://{self.REALM}/token",service="registry.docker.io"'
            return registry.Answer(401, {registry.CHALLENGE_HEADER: challenge}, b"")
        segments = parts.path.split("/")
        name, kind, reference = segments[3], segments[4], segments[5]
        allowance = {registry.LIMIT_HEADER: "100;w=3600", registry.REMAINING_HEADER: f"{self.remaining};w=3600"}
        if kind == "manifests" and not reference.startswith("sha256:"):
            digest = self.tags.get((name, reference))
            if digest is None:
                return registry.Answer(404, allowance, b"")
            return registry.Answer(200, dict(allowance, **{registry.DIGEST_HEADER: digest,
                                                           registry.CONTENT_TYPE_HEADER: registry.OCI_INDEX,
                                                           registry.LENGTH_HEADER: str(len(self.blobs[digest]))}),
                                   b"")
        data = self.blobs.get(reference)
        if data is None or (kind == "blobs" and not self.served_by_blob and b"schemaVersion" in data):
            return registry.Answer(404, allowance, b"")
        if self.redirect_to and kind == "blobs" and method == registry.GET:
            return registry.Answer(307, {}, b"", "", registry.REDIRECT_UNDECLARED)
        if kind == "manifests" and method == registry.GET:
            self.remaining -= 1
        body = b"" if method == registry.HEAD else (data + b" " if reference in self.tampered else data)
        return registry.Answer(200, dict(allowance, **{registry.DIGEST_HEADER: reference,
                                                       registry.LENGTH_HEADER: str(len(data))}), body,
                               "production.cloudfront.docker.com" if kind == "blobs" else self.HOST)


def reader(hub, folder: Path, *, maximum_requests: int = 500, **settings) -> registry.RegistryReader:
    return registry.RegistryReader(registry.DOCKER_HUB, folder, registry.RequestBudget(maximum_requests, 60.0),
                                   pause_seconds=0, transport=hub, sleep=lambda seconds: None, **settings)


ANNOTATIONS = {"org.opencontainers.image.base.name": "debian:trixie-slim",
               "org.opencontainers.image.base.digest": "sha256:" + "d" * 64,
               "org.opencontainers.image.version": "2.4.1", "org.opencontainers.image.revision": COMMIT,
               "org.opencontainers.image.created": "2026-10-01T00:00:00Z"}


def demo_hub() -> FakeHub:
    """Docker Hub holding the demo repository's three families."""
    hub = FakeHub()
    hub.image("demo", "2.4.1", [("linux", "amd64", None, config("amd64"),
                                 dict(ANNOTATIONS, **{"com.docker.official-images.bashbrew.arch": "amd64"})),
                                ("linux", "arm64", "v8", config("arm64", variant="v8"),
                                 dict(ANNOTATIONS, **{"com.docker.official-images.bashbrew.arch": "arm64v8"}))])
    hub.image("demo", "2.4.1-alpine", [("linux", "amd64", None, config("amd64", user="demo"),
                                        {"com.docker.official-images.bashbrew.arch": "amd64"})])
    hub.image("demo", "1.9.9", [("linux", "amd64", None, config("amd64", cmd=("demo", "legacy")),
                                 {"com.docker.official-images.bashbrew.arch": "amd64"})])
    return hub


class LibraryTests(unittest.TestCase):
    def test_entries_their_defaults_overrides_and_families(self):
        entries = library.read_library("demo", LIBRARY_TEXT)
        self.assertEqual([entry.tags[0] for entry in entries], ["2.4.1", "2.4.1-alpine", "1.9.9"])
        first, _alpine, old = entries
        self.assertEqual((first.shared_tags, first.architectures, first.git_fetch, first.file),
                         (("stable",), ("amd64", "arm64v8"), library.DEFAULTS[library.GIT_FETCH], "Dockerfile"))
        self.assertEqual(first.git_repository, "https://github.com/example/docker-demo.git")
        self.assertEqual(first.family, "context:directory=2/debian")
        self.assertEqual(old.overrides, {"arm32v7": {"Directory": "1/debian-arm"}})
        self.assertEqual(old.family, "context:directory=1/debian;directories=arm32v7=1/debian-arm")

    def test_entries_sharing_a_build_context_are_named_by_a_tag(self):
        text = (f"GitRepo: https://github.com/example/x.git\n\nTags: 6.4.5, 6.4, latest\nGitCommit: {COMMIT}\n\n"
                f"Tags: 6.3.7, 6.3\nGitCommit: {COMMIT}\n")
        entries = library.read_library("crate", text)
        self.assertEqual([entry.family for entry in entries], ["tag:6.4", "tag:6.3"])
        self.assertEqual(entries[0].architectures, ("amd64",))

    def test_known_wrong_entries_are_refused(self):
        for text in (f"GitRepo: g\n\nTags: 1, 1\nGitCommit: {COMMIT}\n",
                     f"GitRepo: g\n\nTags: 1\nGitCommit: {COMMIT}\n\nTags: 1\nGitCommit: {COMMIT}\n",
                     "GitRepo: g\n\nTags: 1\nGitCommit: abc\n",
                     f"GitRepo: g\n\nTags: 1\nno field here\nGitCommit: {COMMIT}\n",
                     f"Tags: 1\nGitCommit: {COMMIT}\n",
                     f"GitRepo: g\n\nTags: bad tag!\nGitCommit: {COMMIT}\n"):
            with self.assertRaises(library.LibraryError):
                library.read_library("demo", text)
        with self.assertRaises(library.LibraryError):
            library.read_library("Not_A_Name", LIBRARY_TEXT)


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.hub = demo_hub()

    def test_a_tag_resolves_by_head_and_documents_read_by_digest_through_blobs(self):
        source = reader(self.hub, self.folder)
        tag = source.read_tag("demo", "2.4.1")
        self.assertEqual(tag.digest, self.hub.tags[("demo", "2.4.1")])
        index = source.read_document("demo", tag.digest, manifest=True)
        self.assertEqual(index.data, self.hub.blobs[tag.digest])
        self.assertIn("/blobs/", index.url)
        self.assertEqual(source.counted_reads, 0)
        again = source.read_document("demo", tag.digest, manifest=True)
        self.assertTrue(again.cached)
        log = (self.folder / "requests-registry.jsonl").read_text()
        self.assertNotIn(FakeHub.TOKEN, log)
        self.assertNotIn("token\":", log)
        # One challenge, one token, then the token is reused.
        self.assertEqual([method for method, _url, _credential in self.hub.requests].count(registry.GET), 2)

    def test_known_wrong_bytes_that_differ_from_the_digest_are_refused(self):
        digest = self.hub.tags[("demo", "2.4.1")]
        self.hub.tampered.add(digest)
        with self.assertRaises(registry.RegistryError) as raised:
            reader(self.hub, self.folder).read_document("demo", digest, manifest=True)
        self.assertEqual(raised.exception.reason, "document_digest_mismatch")
        self.assertFalse(any(self.folder.rglob("sha256/*/*")))

    def test_known_wrong_a_redirect_to_an_undeclared_host_is_refused(self):
        self.hub.redirect_to = "elsewhere.example.invalid"
        with self.assertRaises(registry.RegistryError) as raised:
            reader(self.hub, self.folder).read_document("demo", self.hub.tags[("demo", "2.4.1")], manifest=True)
        self.assertEqual(raised.exception.reason, "registry_redirect_undeclared")

    def test_a_manifest_the_blob_endpoint_lacks_is_read_as_a_counted_pull_only_above_the_reserve(self):
        self.hub.served_by_blob = False
        source = reader(self.hub, self.folder, reserve_pulls=20)
        digest = source.read_tag("demo", "2.4.1").digest
        self.assertEqual(source.read_document("demo", digest, manifest=True).data, self.hub.blobs[digest])
        self.assertEqual(source.counted_reads, 1)
        # Known wrong: with the allowance at the reserve, the counted read is refused before it is sent.
        self.hub.remaining = 20
        other = reader(self.hub, Path(tempfile.mkdtemp()), reserve_pulls=20)
        other.read_tag("demo", "1.9.9")
        with self.assertRaises(registry.RegistryError) as raised:
            other.read_document("demo", self.hub.tags[("demo", "1.9.9")], manifest=True)
        self.assertEqual(raised.exception.reason, "registry_rate_limited")

    def test_an_unknown_tag_and_the_request_ceiling(self):
        with self.assertRaises(registry.RegistryError) as raised:
            reader(self.hub, self.folder).read_tag("demo", "0.0.0")
        self.assertEqual(raised.exception.reason, "tag_not_found")
        with self.assertRaises(registry.RequestCeilingReached):
            source = reader(self.hub, Path(tempfile.mkdtemp()), maximum_requests=2)
            source.read_tag("demo", "2.4.1")
            source.read_tag("demo", "1.9.9")

    def test_challenges_allowance_and_references(self):
        self.assertEqual(registry.challenge('Bearer realm="https://auth.docker.io/token",service="registry.docker.io"'),
                         {"realm": "https://auth.docker.io/token", "service": "registry.docker.io"})
        self.assertEqual(registry.challenge("Basic realm=x"), {})
        self.assertEqual(registry.remaining_pulls({"remaining": "97;w=3600"}), 97)
        self.assertEqual(registry.canonical_reference("demo", "sha256:" + "e" * 64),
                         "docker.io/library/demo@sha256:" + "e" * 64)
        with self.assertRaises(registry.RegistryError):
            registry.digest_hex("md5:abc")


class DocumentTests(unittest.TestCase):
    def test_an_index_lists_its_platforms_and_leaves_attestations_out(self):
        hub = demo_hub()
        index = json.loads(hub.blobs[hub.tags[("demo", "2.4.1")]])
        entries = oci.read_index(index, registry.OCI_INDEX)
        self.assertEqual([entry.platform for entry in entries], ["linux/amd64", "linux/arm64/v8"])
        self.assertEqual(entries[1].annotations["bashbrew_arch"], "arm64v8")
        self.assertTrue(all(oci.is_attestation(row) == (row["platform"]["os"] == "unknown")
                            for row in index["manifests"]))
        with self.assertRaises(oci.DocumentError):
            oci.read_index(dict(index, mediaType="application/vnd.docker.distribution.manifest.v1+prettyjws"), "")
        with self.assertRaises(oci.DocumentError):
            oci.read_index(dict(index, manifests=[row for row in index["manifests"]
                                                  if row["platform"]["os"] == "unknown"]), registry.OCI_INDEX)

    def test_a_config_reads_into_the_runtime_a_card_states(self):
        runtime = oci.runtime(json.loads(config("amd64", env_extra=("DEMO_VERSION=2.4.2",))))
        self.assertEqual(runtime["entrypoint"], ["docker-entrypoint.sh"])
        self.assertEqual(runtime["ports"], [{"port": 53, "protocol": "udp"}, {"port": 8080, "protocol": "tcp"}])
        self.assertEqual(runtime["volumes"], ["/var/lib/demo"])
        self.assertEqual(runtime["healthcheck"]["interval_ns"], 30000000000)
        # A repeated variable keeps its last value, as a container does.
        self.assertEqual({row["name"]: row["value"] for row in runtime["environment"]}["DEMO_VERSION"], "2.4.2")
        self.assertEqual(oci.ports({"6000-6002/tcp": {}}), [{"port": 6000, "protocol": "tcp"},
                                                             {"port": 6001, "protocol": "tcp"},
                                                             {"port": 6002, "protocol": "tcp"}])
        for wrong in ({"80/xtp": {}}, {"0/tcp": {}}, {"1-5000/tcp": {}}):
            with self.assertRaises(oci.DocumentError):
                oci.ports(wrong)
        with self.assertRaises(oci.DocumentError):
            oci.runtime({"os": "linux", "architecture": "amd64", "config": {"Cmd": "not a list"}})


class DocumentationTests(unittest.TestCase):
    def test_facts_come_from_headings_and_example_flags_never_from_example_values(self):
        facts = docs.facts(DOCS_FILES)
        self.assertEqual(facts["summary"], "Demo serves pages over HTTP.")
        self.assertEqual(facts["categories"], ["web-servers"])
        self.assertEqual([row["name"] for row in facts["environment"]], ["DEMO_MODE", "DEMO_PASSWORD", "DEMO_USER"])
        self.assertEqual(facts["environment"][1]["evidence"], [docs.EXAMPLE_EVIDENCE, docs.HEADING_EVIDENCE])
        self.assertNotIn("mysecretpassword", json.dumps(facts))
        self.assertEqual(facts["software_licence_links"], ["https://example.invalid/LICENSE"])
        self.assertEqual(facts["source_repository"], "https://github.com/example/docker-demo")
        self.assertIsNone(docs.summary(b"x" * 300))
        self.assertEqual(docs.categories(b"not json"), [])


def demo_family(hub: FakeHub, tag: str = "2.4.1", *, withheld=frozenset(), folder=None) -> cards.ImageFamily:
    """The family of one demo tag as the line assembles it, from the fake hub."""
    entry = next(row for row in library.read_library("demo", LIBRARY_TEXT) if row.resolved_tag == tag)
    source = reader(hub, Path(folder or tempfile.mkdtemp()))
    answer = source.read_tag("demo", tag)
    index_document = source.read_document("demo", answer.digest, manifest=True)
    images = []
    for platform in oci.read_index(index_document.json(), registry.OCI_INDEX):
        manifest = oci.read_manifest(source.read_document("demo", platform.manifest["digest"], manifest=True).json(),
                                     platform.manifest["media_type"])
        value = source.read_document("demo", manifest["config"]["digest"], manifest=False).json()
        images.append(cards.PlatformImage(platform, manifest, oci.runtime(value), oci.config_platform(value)))
    return cards.ImageFamily(entry=entry, tag=answer, index={"digest": answer.digest, "media_type": registry.OCI_INDEX,
                                                             "size": index_document.size},
                             platforms=tuple(images), documentation=docs.facts(DOCS_FILES),
                             library_location={"repository": cards.LIBRARY_REPOSITORY, "path": "library/demo",
                                               "commit": COMMIT},
                             docs_location={"repository": cards.DOCS_REPOSITORY, "path": "demo", "commit": COMMIT},
                             withheld_values=withheld)


MIT = (ROOT / "LICENSE").read_bytes()


class CardTests(unittest.TestCase):
    def setUp(self):
        self.hub = demo_hub()
        self.record = cards.contract(demo_family(self.hub))
        self.module = cards.card_module()
        self.files = cards.card_files(self.record, licence_text=MIT, upstream_licence=MIT,
                                      copyright_line="Copyright (c) 2014 Docker, Inc.")
        self.readme = self.files[cards.README_NAME].decode()

    def test_the_contract_states_inputs_outputs_platforms_and_what_varies(self):
        record = self.record
        self.assertEqual(record["image"]["reference"], "docker.io/library/demo@" + self.hub.tags[("demo", "2.4.1")])
        self.assertEqual(record["family"]["identity"], "context:directory=2/debian")
        environment = {row["name"]: row for row in record["inputs"]["environment"]}
        self.assertTrue(environment["DEMO_ARCH"]["varies_by_platform"])
        self.assertIsNone(environment["DEMO_ARCH"]["value"])
        self.assertEqual(record["platforms"][1]["differences"], {"environment": {"DEMO_ARCH": "arm64"}})
        # A credential's name keeps the variable and withholds its value.
        self.assertEqual((environment["DEMO_ADMIN_PASSWORD"]["withheld"], environment["DEMO_ADMIN_PASSWORD"]["value"]),
                         (True, None))
        self.assertNotIn("x1", json.dumps(environment["DEMO_ADMIN_PASSWORD"]))
        self.assertEqual((environment["DEMO_USER"]["set_by_image"], environment["DEMO_USER"]["documented"]),
                         (False, True))
        self.assertEqual(record["outputs"]["health"], self.module.HEALTH_DECLARED)
        self.assertEqual(record["compatibility"]["notes"], ["runs_as_root", "declares_volumes",
                                                            "healthcheck_declared"])
        self.assertEqual(record["platforms"][0]["base"], {"name": "debian:trixie-slim", "digest": "sha256:" + "d" * 64})
        schema = json.loads(self.files[cards.SCHEMA_NAME])
        from supply_lines import schema_check
        self.assertEqual(schema_check.errors(record, schema), [])

    def test_the_readme_agrees_and_a_changed_contract_or_readme_disagrees(self):
        self.assertEqual(self.module.disagreements(self.record, self.readme), [])
        self.assertIn("docker run --rm --publish-all docker.io/library/demo@", self.readme)
        self.assertNotIn("mysecretpassword", self.readme)
        changed = json.loads(json.dumps(self.record))
        changed["inputs"]["ports"].pop()
        self.assertTrue(self.module.disagreements(changed, self.readme))
        extra = self.readme.replace("| `8080/tcp` | exposed |", "| `8080/tcp` | exposed |\n| `9090/tcp` | exposed |")
        self.assertTrue(any("not in contract.json" in problem
                            for problem in self.module.disagreements(self.record, extra)))
        lost = self.readme.replace("Stop signal: `SIGQUIT`\n", "")
        self.assertTrue(self.module.disagreements(self.record, lost))

    def test_the_helper_renders_and_refuses(self):
        module, record = self.module, self.record
        argv = module.render_run(record, platform="linux/arm64", environment={"DEMO_PASSWORD": None,
                                                                               "DEMO_MODE": "fast"},
                                 publish=["127.0.0.1::8080", "9053:53/udp"], volumes=["data:/var/lib/demo:ro"],
                                 name="demo-1", detach=True, engine="podman", user="1000:1000")
        self.assertEqual(argv[:2], ["podman", "run"])
        self.assertEqual(argv[argv.index("--platform") + 1], "linux/arm64/v8")
        self.assertIn("DEMO_PASSWORD", argv)
        self.assertIn("127.0.0.1::8080/tcp", argv)
        self.assertIn("9053:53/udp", argv)
        self.assertIn("data:/var/lib/demo:ro", argv)
        self.assertEqual(argv[-1], record["image"]["reference"])
        self.assertEqual(module.notices(record, volumes=["data:/var/lib/demo"]), [])
        self.assertTrue(module.notices(record, environment={"UNKNOWN_SETTING": "1"}))
        for wrong in ({"environment": {"DEMO_PASSWORD": "hunter2"}}, {"platform": "linux/s390x"},
                      {"publish": ["0:8080"]}, {"volumes": ["data:var/lib"]}, {"engine": "rkt"}):
            with self.assertRaises(module.InputError):
                module.render_run(record, **wrong)
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(io.StringIO()):
            folder = Path(tempfile.mkdtemp())
            (folder / "contract.json").write_bytes(self.files[cards.CONTRACT_NAME])
            self.assertEqual(module.main(["--contract", str(folder / "contract.json"), "--env", "DEMO_PASSWORD",
                                          "--", "demo", "--version"]), 0)
        self.assertTrue(output.getvalue().strip().endswith("demo --version"))

    def test_an_image_with_no_command_needs_one_and_windows_images_are_named(self):
        record = json.loads(json.dumps(self.record))
        record["runtime"].update(entrypoint=None, command=None)
        self.assertTrue(self.module.problems(record))
        self.assertEqual(self.module.problems(record, command=["demo"]), [])


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.hub = demo_hub()
        self.folder = Path(tempfile.mkdtemp())
        self.record = cards.contract(demo_family(self.hub, folder=self.folder))
        self.module = cards.card_module()

    def test_the_registry_check_passes_on_the_card_and_binds_its_digest(self):
        record = verify.verify(self.record, "f" * 64, reader(self.hub, self.folder), self.module)
        self.assertEqual(record["state"], verify.PASSED, record["checks"])
        self.assertEqual({check["name"] for check in record["checks"]}, set(verify.CHECK_NAMES))
        data = verify.evidence_bytes(record)
        self.assertEqual(verify.read_evidence(data, "f" * 64, self.record["image"]["index"]["digest"]), record)
        # Known wrong: evidence for other bytes, and evidence that is not a record.
        for wrong, reason in ((("e" * 64, self.record["image"]["index"]["digest"]), verify.EVIDENCE_STALE),):
            with self.assertRaises(verify.NativeError) as raised:
                verify.read_evidence(data, *wrong)
            self.assertEqual(raised.exception.reason, reason)
        with self.assertRaises(verify.NativeError):
            verify.read_evidence(b"[]", "f" * 64, self.record["image"]["index"]["digest"])

    def test_known_wrong_a_moved_tag_or_another_config_fails_the_check(self):
        self.hub.image("demo", "2.4.1", [("linux", "amd64", None, config("amd64", cmd=("demo", "moved")), {})])
        record = verify.verify(self.record, "f" * 64, reader(self.hub, self.folder), self.module)
        failed = {check["name"] for check in record["checks"] if not check["passed"]}
        self.assertEqual(failed, {verify.TAG_CHECK})
        with self.assertRaises(verify.NativeError) as raised:
            verify.read_evidence(verify.evidence_bytes(record), "f" * 64, self.record["image"]["index"]["digest"])
        self.assertEqual(raised.exception.reason, verify.CHECK_FAILED)
        changed = json.loads(json.dumps(self.record))
        changed["runtime"]["stop_signal"] = "SIGTERM"
        record = verify.verify(changed, "f" * 64, reader(demo_hub(), self.folder), self.module)
        self.assertIn(verify.MATCH_CHECK, {check["name"] for check in record["checks"] if not check["passed"]})

    def test_a_withheld_value_is_compared_by_name_only(self):
        differences = verify.runtime_differences({"environment": {"A_PASSWORD": None}},
                                                 {"environment": {"A_PASSWORD": "x"}}, {"A_PASSWORD"})
        self.assertEqual(differences, [])
        self.assertTrue(verify.runtime_differences({"environment": {"A": None}}, {"environment": {"A": "x"}}, set()))


class SmokeTests(unittest.TestCase):
    def test_a_smoke_run_pulls_compares_runs_and_removes_what_it_pulled(self):
        hub = demo_hub()
        record = cards.contract(demo_family(hub, "2.4.1-alpine"))
        calls = []
        config_text = json.dumps(json.loads(config("amd64", user="demo"))["config"])

        def run(argv, **settings):
            calls.append(argv)
            if argv[1:2] == ["version"]:
                return SimpleNamespace(returncode=0, stdout="29.5.2\n", stderr="")
            if argv[1:3] == ["image", "inspect"] and "--platform" not in argv:
                present = any(call[1:2] == ["pull"] for call in calls)
                return SimpleNamespace(returncode=0 if present else 1, stdout="sha256:" + "9" * 64, stderr="")
            if argv[1:3] == ["image", "inspect"]:
                return SimpleNamespace(returncode=0, stdout=config_text, stderr="")
            if argv[1:3] == ["container", "inspect"]:
                return SimpleNamespace(returncode=0, stdout='{"Running": true}', stderr="")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        module = cards.card_module()
        with unittest.mock.patch.object(smoke.shutil, "which", return_value="/usr/bin/docker"):
            result = smoke.smoke(record, "f" * 64, module, run=run, sleep=lambda seconds: None)
        self.assertEqual(result["state"], smoke.PASSED, result["checks"])
        started = next(call for call in calls if call[1:2] == ["run"])
        self.assertEqual(started[2:4], ["--network", "none"])
        self.assertTrue(any(call[1:3] == ["image", "rm"] for call in calls))
        # Known wrong: an engine that reads another config fails the comparison.
        config_text = json.dumps(json.loads(config("amd64", user="root"))["config"])
        with unittest.mock.patch.object(smoke.shutil, "which", return_value="/usr/bin/docker"):
            result = smoke.smoke(record, "f" * 64, module, run=run, sleep=lambda seconds: None)
        self.assertEqual(result["state"], smoke.FAILED)


if __name__ == "__main__":
    unittest.main()
