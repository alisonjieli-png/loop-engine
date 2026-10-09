"""Write the files of one container image contract card from a tag family's registry and documentation facts.

```text
one tag family (a library entry, its tag's index, every platform's manifest and config, the documentation facts)
├── contract.json      container_image_contract/v1, written here: the image and its tags, the common runtime and
│                      what differs per platform, inputs, outputs, platforms with their digests, documentation
│                      facts and compatibility notes
├── schema.json        its JSON Schema (card_files/schema.json, the same bytes in every card)
├── README.md          the card a harness reads first; every checked line comes from image_contract.card_lines()
├── image_contract.py  the shared helper (card_files/image_contract.py): problems, notices, render_run, card_lines
├── schema_check.py    the small JSON Schema validator every schema package carries (supply_lines/schema_check.py)
├── test_image_contract.py  the shared test (card_files/test_image_contract.py), with known-wrong controls
└── component.json     container_image_card/v1, the small contract card a harness reads first, written after the
                       registry check (it names the evidence), so the card digest the evidence binds leaves it out
```

The checked lines are written by the shipped image_contract.py itself (loaded from card_files), so a card and its
checker cannot disagree about a format. Nothing here reads the network.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path

from supply_lines.reading import https_address

from . import docs, oci
from .library import LibraryEntry
from .registry import CANONICAL_NAMESPACE, CANONICAL_REGISTRY, TagAnswer, canonical_reference

CARD_FILES = Path(__file__).resolve().parent / "card_files"
VALIDATOR = Path(__file__).resolve().parents[1] / "supply_lines" / "schema_check.py"
MODULE_NAME, TEST_NAME, SCHEMA_NAME, VALIDATOR_NAME = ("image_contract.py", "test_image_contract.py", "schema.json",
                                                       "schema_check.py")
CONTRACT_NAME, COMPONENT_NAME, README_NAME = "contract.json", "component.json", "README.md"
EVIDENCE_PATH, SMOKE_PATH = "verification/registry.json", "verification/smoke.json"
CARD_RECORD = "container_image_card/v1"
#: The form and harness kind a card is served as (component_form/v1): the contract of an image's interface.
FORM, KIND = "schema", "contract_schema"
COLLECTION = "docker_official_images"
#: The operating system of a Windows container image, as a platform names it.
WINDOWS_OS = "windows"
#: The platform the README's helper example names when the image has it (else its last platform).
EXAMPLE_PLATFORM = "linux/arm64/v8"
HUB_HOST = "hub.docker.com"
DOCS_REPOSITORY, LIBRARY_REPOSITORY = "docker-library/docs", "docker-library/official-images"
#: Where a variable's presence was read.
IMAGE_EVIDENCE = "image_config"
#: The value a card writes for a withheld environment value: none at all.
WITHHELD = None
AUTHORING = "generated_from_registry_facts_and_library_definitions"
#: What every card says it does not establish.
LIMITS = ("The facts are the registry's for the digests named here: a tag moves when its image is rebuilt, so this "
          "card describes these digests, not the tag's later images. An environment variable the entrypoint reads "
          "that the config does not set and the documentation names in no heading or example command is not "
          "listed, and whether a documented variable is required is not stated. The outputs are what every "
          "container gives (its logs, exit status, exposed ports and volumes); what the program itself writes is "
          "not described. No layer was read, so the files and packages inside the image and its uncompressed "
          "size are not known. Nothing here was loaded by a harness.")
_MODULE = None


def card_module():
    """The shipped helper, loaded from card_files once: the writer and the package test use the same code."""
    global _MODULE
    if _MODULE is None:
        specification = importlib.util.spec_from_file_location("container_image_contract_module",
                                                               CARD_FILES / MODULE_NAME)
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
        _MODULE = module
    return _MODULE


def shared_files() -> dict:
    """{path: bytes} of the files every card carries byte for byte."""
    return {MODULE_NAME: (CARD_FILES / MODULE_NAME).read_bytes(), TEST_NAME: (CARD_FILES / TEST_NAME).read_bytes(),
            SCHEMA_NAME: (CARD_FILES / SCHEMA_NAME).read_bytes(), VALIDATOR_NAME: VALIDATOR.read_bytes()}


def json_bytes(value) -> bytes:
    """A record as card files hold it: indented, sorted as written, ASCII only, so no invisible character is
    written raw."""
    return (json.dumps(value, indent=1, ensure_ascii=True) + "\n").encode("utf-8")


@dataclass(frozen=True)
class PlatformImage:
    """One platform image of a family: what the index says of it, its manifest facts and its config's runtime."""

    entry: oci.PlatformEntry
    manifest: dict  # oci.read_manifest
    runtime: dict  # oci.runtime
    config_platform: dict  # oci.config_platform

    @property
    def platform(self) -> str:
        return self.entry.platform


@dataclass(frozen=True)
class ImageFamily:
    """Everything one card is written from."""

    entry: LibraryEntry
    tag: TagAnswer
    index: dict  # {digest, media_type, size}
    platforms: tuple  # PlatformImage, in platform order
    documentation: dict  # docs.facts
    library_location: dict  # {repository, path, commit}
    docs_location: dict  # {repository, path, commit}
    #: Environment variable names whose values are withheld because the value has a credential's shape.
    withheld_values: frozenset = frozenset()
    collection: str = COLLECTION


def _common(values: list):
    """(common value, varies): the one value every platform has, or (None, True)."""
    first = values[0]
    return (first, False) if all(value == first for value in values[1:]) else (None, True)


def _environment(family: ImageFamily, module) -> tuple:
    """(inputs.environment rows, {platform: {name: value}} of the values that vary) for the contract."""
    per_platform = [{row["name"]: row["value"] for row in image.runtime["environment"]} for image in family.platforms]
    documented = {row["name"]: row["evidence"] for row in family.documentation.get("environment", [])}
    names = sorted(set().union(*per_platform) | set(documented))
    rows, differences = [], {}
    for name in names:
        present = [values for values in per_platform if name in values]
        set_by_image = bool(present)
        withheld = set_by_image and (module.is_credential_name(name) or name in family.withheld_values)
        value, varies = (None, False)
        if set_by_image:
            value, varies = _common([values.get(name) for values in per_platform]) \
                if len(present) == len(per_platform) else (None, True)
        if varies:
            for image, values in zip(family.platforms, per_platform):
                if name in values:
                    differences.setdefault(image.platform, {})[name] = WITHHELD if withheld else values[name]
        evidence = ([IMAGE_EVIDENCE] if set_by_image else []) + list(documented.get(name, []))
        rows.append({"name": name, "set_by_image": set_by_image, "value": WITHHELD if withheld else value,
                     "withheld": withheld, "varies_by_platform": varies, "documented": name in documented,
                     "evidence": evidence})
    return rows, differences


def _platform_record(image: PlatformImage, differences: dict) -> dict:
    annotations = dict(image.manifest["annotations"], **image.entry.annotations)
    base = None
    if annotations.get("base_name") or annotations.get("base_digest"):
        base = {"name": annotations.get("base_name"), "digest": annotations.get("base_digest")}
    return {"platform": image.platform, "os": image.entry.os, "architecture": image.entry.architecture,
            "variant": image.entry.variant, "os_version": image.entry.os_version,
            "os_features": list(image.entry.os_features), "bashbrew_arch": annotations.get("bashbrew_arch"),
            "manifest": dict(image.entry.manifest), "config": dict(image.manifest["config"]),
            "layers": image.manifest["layers"], "foreign_layers": image.manifest["foreign_layers"],
            "compressed_bytes": image.manifest["compressed_bytes"], "created": annotations.get("created"),
            "version": annotations.get("version"), "revision": annotations.get("revision"),
            "source": annotations.get("source"), "base": base, "differences": differences}


def contract(family: ImageFamily) -> dict:
    """contract.json (container_image_contract/v1) of one tag family."""
    module = card_module()
    entry, images = family.entry, family.platforms
    runtime, varies = {}, []
    for name in module.RUNTIME_FIELDS:
        value, differs = _common([image.runtime[name] for image in images])
        runtime[name] = value
        if differs:
            varies.append(name)
    runtime["varies_by_platform"] = varies
    environment, environment_differences = _environment(family, module)
    port_value, ports_vary = _common([image.runtime["ports"] for image in images])
    volume_value, volumes_vary = _common([image.runtime["volumes"] for image in images])
    ports = port_value if not ports_vary else sorted(
        {(row["port"], row["protocol"]) for image in images for row in image.runtime["ports"]})
    if ports_vary:
        ports = [{"port": port, "protocol": protocol} for port, protocol in ports]
    volumes = volume_value if not volumes_vary else sorted({path for image in images
                                                            for path in image.runtime["volumes"]})
    records = []
    for image in images:
        differences = {}
        own = {name: image.runtime[name] for name in varies}
        if own:
            differences["runtime"] = own
        if image.platform in environment_differences:
            differences["environment"] = environment_differences[image.platform]
        if ports_vary:
            differences["ports"] = image.runtime["ports"]
        if volumes_vary:
            differences["volumes"] = image.runtime["volumes"]
        records.append(_platform_record(image, differences))
    published = {record["bashbrew_arch"] for record in records if record["bashbrew_arch"]}
    missing = [architecture for architecture in entry.architectures if published and architecture not in published]
    systems = sorted({image.entry.os for image in images})
    healthy = any(image.runtime["healthcheck"] and image.runtime["healthcheck"]["test"][:1] != [oci.HEALTH_NONE]
                  for image in images)
    notes = []
    users = {image.runtime["user"] for image in images}
    if systems != [WINDOWS_OS]:
        notes.append("runs_as_root" if users & ({None} | set(module.ROOT_USERS)) else "runs_as_user")
    if volumes:
        notes.append("declares_volumes")
    if not any(image.runtime["entrypoint"] or image.runtime["command"] for image in images):
        notes.append("no_default_command")
    if healthy:
        notes.append("healthcheck_declared")
    if any(image.runtime["on_build"] for image in images):
        notes.append("on_build_triggers")
    if WINDOWS_OS in systems:
        notes.append("windows_containers")
    if missing:
        notes.append("architectures_declared_not_published")
    documentation = family.documentation
    name = entry.repository
    return {
        "record_type": module.CONTRACT_RECORD,
        "image": {"registry": CANONICAL_REGISTRY, "repository": f"{CANONICAL_NAMESPACE}/{name}", "name": name,
                  "collection": family.collection, "reference": canonical_reference(name, family.index["digest"]),
                  "tags": list(entry.tags), "shared_tags": list(entry.shared_tags), "resolved_tag": family.tag.tag,
                  "index": dict(family.index), "page": https_address(HUB_HOST, f"_/{name}")},
        "family": {"identity": entry.family, "declared_architectures": list(entry.architectures),
                   "library": dict(family.library_location), "source": entry.source()},
        "runtime": runtime,
        "inputs": {"environment": environment, "ports": ports, "volumes": volumes},
        "outputs": {"logs": module.LOGS, "exit_status": module.EXIT_STATUS, "listening_ports": ports,
                    "state_volumes": volumes,
                    "health": module.HEALTH_DECLARED if healthy else module.HEALTH_NOT_DECLARED},
        "platforms": records,
        "documentation": {"summary": documentation.get("summary"),
                          "summary_source": (f"{DOCS_REPOSITORY} {name}/{docs.SUMMARY_FILE}"
                                             if documentation.get("summary") else None),
                          "categories": list(documentation.get("categories") or []),
                          "software_licence_links": list(documentation.get("software_licence_links") or []),
                          "source_repository": documentation.get("source_repository"),
                          "docs": dict(family.docs_location)},
        "compatibility": {"operating_systems": systems, "declared_not_published": missing, "notes": notes}}


def purpose(record: dict) -> str:
    """The "Use this card when" line."""
    image = record["image"]
    count = len(record["platforms"])
    digests = "the exact digest of its one platform image" if count == 1 else \
        f"the exact digest of each of its {count} platform images"
    return (f"Use this card when a step runs the `{image['name']}` container image, tag `{image['resolved_tag']}`: "
            f"what it runs, the environment variables, ports, volumes and arguments it takes, what it gives back, "
            f"and {digests}, without reading its Dockerfile or pulling it.")


def _table(header: str, rows: list, empty: str) -> list:
    if not rows:
        return [empty]
    columns = header.count("|") - 1
    return [header, "|" + "---|" * columns] + rows


def readme(record: dict, *, copyright_line: str) -> str:
    """README.md: the card a harness reads first."""
    module = card_module()
    image, documentation = record["image"], record["documentation"]
    lines = module.card_lines(record)
    title, reference, tags, shared, platforms, run = lines[:6]
    blocks = [title, purpose(record), reference, tags, shared, platforms]
    if documentation["summary"]:
        blocks.append(f"> Docker's one-line summary of the image (`{image['name']}/{docs.SUMMARY_FILE}` of "
                      f"{DOCS_REPOSITORY}, MIT): {documentation['summary']}")
    example = ["python image_contract.py"]
    names = module.platforms(record)
    if len(names) > 1:
        example.append(f"--platform {EXAMPLE_PLATFORM if EXAMPLE_PLATFORM in names else names[-1]}")
    if record["inputs"]["ports"]:
        port = record["inputs"]["ports"][0]
        example.append(f"--publish 8080:{port['port']}/{port['protocol']}")
    if record["inputs"]["volumes"]:
        example.append(f"--volume {image['name']}-data:{record['inputs']['volumes'][0]}")
    blocks += [module.SECTION_PREFIX + "Run it", "```sh\n" + run + "\n```",
               "`image_contract.py` writes the command for other inputs and refuses inputs the contract rules out "
               "(an unknown platform, a port out of range, a relative volume target, a credential given as a "
               "value):",
               "```sh\n" + " ".join(example) + "\n```",
               "Add `--engine podman` for Podman. A credential is passed by its name alone (`--env DB_PASSWORD`), so "
               "the engine copies it from your environment and it never appears in the command."]
    documented = [row["name"] for row in record["inputs"]["environment"] if row["documented"] and
                  not row["set_by_image"]]
    if documented:
        blocks.append(f"Its documentation names {len(documented)} variable{'s' if len(documented) != 1 else ''} the "
                      "image does not set (under Inputs), which the entrypoint may read; this card does not say "
                      "which a start requires. Add each one your use needs with `--env NAME=VALUE`.")
    blocks += [module.SECTION_PREFIX + "What runs", "\n\n".join(module.runtime_lines(record))]
    labels = record["runtime"]["labels"]
    if labels:
        blocks.append("Labels: " + ", ".join(f"{module.code(key)} = {module.code(value)}"
                                             for key, value in sorted(labels.items())))
    blocks.append(module.SECTION_PREFIX + "Inputs")
    blocks += ["### Environment variables", "\n".join(_table(
        "| Name | Value in the image | Named by |", module.environment_rows(record),
        "The image sets no environment variable and its documentation names none."))]
    blocks += ["### Ports", "\n".join(_table("| Port | |", module.port_rows(record), "The image exposes no port."))]
    blocks += ["### Volumes", "\n".join(_table("| Path | |", module.volume_rows(record),
                                               "The image declares no volume."))]
    blocks += ["### Arguments", "Arguments after the image reference replace the default command; `--entrypoint` "
                                "replaces the entrypoint (`image_contract.py --entrypoint PATH -- ARGUMENT ...`)."]
    ports = ", ".join(module.code(f"{row['port']}/{row['protocol']}") for row in record["outputs"]["listening_ports"])
    volumes = ", ".join(module.code(path) for path in record["outputs"]["state_volumes"])
    blocks += [module.SECTION_PREFIX + "Outputs", "\n".join([
        "- Logs: what the main process writes to standard output and standard error (`docker logs`).",
        "- Exit status: the main process's exit status is the container's.",
        f"- Ports while it runs: {ports or 'none exposed'}.",
        f"- State: files under {volumes}." if volumes else "- State: the image declares no volume, so nothing "
                                                            "outlives the container unless a caller mounts one.",
        "- Health: " + ("the healthcheck's status (`docker inspect`)." if record["outputs"]["health"]
                        == module.HEALTH_DECLARED else "no healthcheck is declared.")])]
    blocks += [module.SECTION_PREFIX + "Platforms", "\n".join(_table(
        "| Platform | Manifest digest | Config digest | Compressed size | Layers |", module.platform_rows(record),
        "No platform."))]
    differences = module.difference_rows(record)
    if differences:
        blocks += ["### Platform differences", "\n".join(_table("| Platform | Field | Value |", differences, ""))]
    blocks.append(module.SECTION_PREFIX + "Compatibility")
    compatibility = []
    bases = [row["base"] for row in record["platforms"] if row["base"]]
    names = sorted({base["name"] or "" for base in bases})
    digests = sorted({base["digest"] or "" for base in bases})
    if len(names) == 1 and len(digests) == 1 and len(bases) == len(record["platforms"]):
        compatibility.append(f"Base image: {module.code(names[0] or 'not named')}" +
                             (f" ({module.code(digests[0])})" if digests[0] else "") + ".")
    elif bases:
        compatibility.append(("Base image: " if len(names) == 1 else "Base images: ") +
                             ", ".join(module.code(name or "not named") for name in names) +
                             " (each platform's base digest is in `contract.json`).")
    else:
        compatibility.append("Base image: not stated by the image's annotations.")
    compatibility.append("Operating systems: " + ", ".join(record["compatibility"]["operating_systems"]) + ".")
    if record["compatibility"]["declared_not_published"]:
        compatibility.append("Declared in the library but not in the index: " + ", ".join(
            module.code(name) for name in record["compatibility"]["declared_not_published"]) + ".")
    blocks.append("\n\n".join(compatibility))
    note_lines = [f"- {module.NOTES[note]}" for note in record["compatibility"]["notes"]]
    if note_lines:
        blocks.append("\n".join(note_lines))
    links = documentation["software_licence_links"]
    blocks += [module.SECTION_PREFIX + "Software licence",
               "The software inside the image is under its own licences, which this card does not change: the card "
               "is Baltor's description of the image (MIT, see `LICENSE`) and grants no licence to the image. "
               + ("Docker's documentation names where they are stated: " + ", ".join(f"<{link}>" for link in links)
                  + "." if links else "Docker's documentation names no licence address for it.")]
    library, source_docs = record["family"]["library"], documentation["docs"]
    blocks += [module.SECTION_PREFIX + "Source", "\n".join([
        f"- Tags and build: `{library['path']}` of {library['repository']} at commit `{library['commit']}` "
        "(Apache-2.0; tags, architectures and build context read as facts, no text copied).",
        f"- Image: Docker Hub. The tag `{image['resolved_tag']}` resolved by HEAD to the index "
        f"`{image['index']['digest']}`; the index, every platform manifest and every config were read by digest "
        "and checked against it. No layer was read.",
        f"- Summary, categories, documented variable names and licence addresses: `{source_docs['path']}/` of "
        f"{source_docs['repository']} at commit `{source_docs['commit']}` (MIT, {copyright_line} The licence "
        "text is `UPSTREAM-LICENSE`.)",
        f"- `{TEST_NAME}` checks `{CONTRACT_NAME}` against `{SCHEMA_NAME}`, this README against "
        f"`{CONTRACT_NAME}`, and `{EVIDENCE_PATH}` against these files."])]
    return "\n\n".join(block for block in blocks if block) + "\n"


def card_files(record: dict, *, licence_text: bytes, upstream_licence: bytes, copyright_line: str) -> dict:
    """{path: bytes} of every card file the registry evidence binds."""
    files = {README_NAME: readme(record, copyright_line=copyright_line).encode("utf-8"),
             CONTRACT_NAME: json_bytes(record), "LICENSE": licence_text, "UPSTREAM-LICENSE": upstream_licence}
    files.update(shared_files())
    return files


def card_digest(files: dict) -> str:
    return card_module().card_digest(files)


def search_tags(record: dict) -> list:
    image = record["image"]
    words = ["docker", "container image", "docker official image", image["name"], f"{image['name']}:"
             f"{image['resolved_tag']}"]
    words += [category.replace("-", " ") for category in record["documentation"]["categories"]]
    words += [row["base"]["name"].split(":")[0] for row in record["platforms"] if row["base"] and row["base"]["name"]]
    words += record["compatibility"]["operating_systems"]
    unique = []
    for word in words:
        word = word.strip().lower()
        if word and len(word) <= 40 and word not in unique:
            unique.append(word)
    return unique[:16]


def component_card(record: dict, files: dict, evidence: dict, *, smoke: "dict | None", generator: dict,
                   limits: str = LIMITS) -> dict:
    """component.json (container_image_card/v1): the small contract card a harness reads first."""
    module = card_module()
    image = record["image"]
    return {"record_type": CARD_RECORD,
            "job": {"registry": image["registry"], "repository": image["repository"],
                    "family": record["family"]["identity"]},
            "title": module.title_line(record)[len(module.TITLE_PREFIX):], "purpose": purpose(record),
            "form": FORM, "kind": KIND,
            "image": {"reference": image["reference"], "resolved_tag": image["resolved_tag"], "tags": image["tags"],
                      "index_digest": image["index"]["digest"]},
            "platforms": module.platforms(record),
            "inputs": {"environment": [row["name"] for row in record["inputs"]["environment"]],
                       "ports": [f"{row['port']}/{row['protocol']}" for row in record["inputs"]["ports"]],
                       "volumes": list(record["inputs"]["volumes"])},
            "summary": record["documentation"]["summary"], "categories": record["documentation"]["categories"],
            "documents": [README_NAME],
            "files": [{"path": path, "sha256": hashlib.sha256(data).hexdigest()}
                      for path, data in sorted(files.items())],
            "verification": {"registry": {"state": evidence["state"], "record": EVIDENCE_PATH,
                                          "checks": sorted({check["name"] for check in evidence["checks"]}),
                                          "card_digest": evidence["card_digest"]},
                             "smoke": ({"state": smoke["state"], "record": SMOKE_PATH, "engine": smoke["engine"],
                                        "platform": smoke["platform"]} if smoke else None),
                             "tests": TEST_NAME},
            "tags": search_tags(record), "limits": limits, "generator": dict(generator), "authoring": AUTHORING}


__all__ = ["ImageFamily", "PlatformImage", "card_module", "shared_files", "contract", "readme", "card_files",
           "card_digest", "component_card", "json_bytes", "purpose", "search_tags", "FORM", "KIND", "CONTRACT_NAME",
           "COMPONENT_NAME", "README_NAME", "MODULE_NAME", "TEST_NAME", "SCHEMA_NAME", "VALIDATOR_NAME",
           "EVIDENCE_PATH", "SMOKE_PATH", "LIMITS", "COLLECTION", "DOCS_REPOSITORY", "LIBRARY_REPOSITORY"]
