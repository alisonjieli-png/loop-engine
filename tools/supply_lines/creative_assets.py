"""Line creative_assets: pinned CC0 3D assets and editable Godot projects that a customer's harness can load.

```text
creative_assets (one package per asset or project: resolutions and formats are variants inside it)
├── sources, each with its own line state
│   ├── polyhaven: HDRIs, textures and models of api.polyhaven.com
│   │   ├── terms: the API's terms of service (GitHub Poly-Haven/Public-API ToS.md at its head commit) permit
│   │   │   any use including commercial and building on the data, ask for a unique user agent and, for live
│   │   │   API use, a visible credit; the licence page states every asset is CC0
│   │   └── facts per asset: its info and files records (names, sizes, MD5); prose is never copied
│   ├── ambientcg: materials, HDRIs and models of ambientcg.com's API v3 (its licence page: every asset CC0;
│   │   its API page invites downloading by code; downloads redirect to its content delivery host)
│   └── godot_demo_projects: godot_demos.py (each project of godotengine/godot-demo-projects, MIT, with its
│       per-asset notices decided)
├── each source's terms and licence statement pinned by digest and checked for the clauses the line relies on;
│   a statement that no longer holds them holds the whole source (terms_not_confirmed)
└── one asset package (form reference_image for an HDRI, a texture or a material, three_d_model for a model)
    ├── creative.json: creative_asset_manifest/v1 with every variant's files, each with its exact address, size
    │   and SHA-256; the generator downloads each file once, streaming, to learn its SHA-256 and to check the
    │   publisher's size and MD5, and keeps none of it (nothing is re-hosted)
    ├── creative_fetch.py, blender_load.py, godot_load.gd: the same files in every package (creative_files/)
    ├── test_creative_fetch.py, test_creative_loaders.py: offline tests (a loopback server, a recording bpy)
    └── README.md with a three.js snippet that node --check parses, LICENSE (MIT, the generated code),
        UPSTREAM-LICENSE (the CC0 1.0 legal code), ATTRIBUTION.md
```

Every run is deterministic and makes no model call. A package is a candidate until an independent review.
"""
from __future__ import annotations

import hashlib
import html
import importlib.util
import io
import json
import re
import shutil
import socket
import subprocess
import sys
import unittest
import urllib.parse
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath

from loop_engine.core.library_ingestion.licences import match_licence
from loop_engine.core.library_ingestion.record_rules import canonical_digest

from .packaging import LICENCE_NAME, PACKAGE_PATH_INVALID, UPSTREAM_LICENCE_NAME, PackageFile, SupplyPackage, build
from .reading import github_blob_address, https_address
from .records import (
    BLOCKED_BY_STATIC_CHECK, CREATIVE_ASSETS, GENERATED_CODE_LICENCE, GENERATED_TEST_FAILED, LICENCE_TEXT,
    PACKAGE_ABOVE_REVIEW_BOUND, TERMS_OF_USE, SupplyRecordError, fact_source, provenance, refusal, upstream_key)

GENERATOR_VERSION = "1.0.0"
SHIPPED = Path(__file__).with_name("creative_files")
MANIFEST_NAME = "creative.json"
MANIFEST_RECORD_TYPE = "creative_asset_manifest/v1"
FETCHER, BLENDER_LOADER, GODOT_LOADER = "creative_fetch.py", "blender_load.py", "godot_load.gd"
FETCH_TESTS, LOADER_TESTS = "test_creative_fetch.py", "test_creative_loaders.py"
#: The media type of a Godot script, which the shared suffix table does not know.
GDSCRIPT_MEDIA = "text/x-gdscript"
POLYHAVEN, AMBIENTCG, GODOT_DEMO_PROJECTS = SOURCES = ("polyhaven", "ambientcg", "godot_demo_projects")
NATIVE_FORMAT = "creative_asset_recipe"
DEFAULT_RESOLUTIONS = ("1k", "2k")
RESOLUTIONS = ("1k", "2k", "4k", "8k")
#: The largest file a recipe pins and the largest variant: every pinned byte is downloaded once by the generator
#: (neither source publishes a SHA-256), so these bound a run's reads; larger variants are counted, not pinned.
MAXIMUM_PINNED_FILE_BYTES = 64 * 1024 * 1024
MAXIMUM_VARIANT_BYTES = 160 * 1024 * 1024
#: The form a harness is served for each asset type, and what it does with the bytes (component_form/v1's
#: reference forms and asset roles).
TYPE_FORMS = {"hdri": "reference_image", "texture": "reference_image", "material": "reference_image",
              "model": "three_d_model", "godot_project": "template"}
ASSET_ROLES = {"hdri": "generation_input", "texture": "generation_input", "material": "generation_input",
               "model": "editable_source", "godot_project": "editable_source"}
TYPE_LABELS = {"hdri": "HDRI environment map", "texture": "PBR texture set", "material": "PBR material",
               "model": "3D model", "godot_project": "editable Godot project"}
EFFECTS = (("network", "creative_fetch.py downloads the pinned files from the origin creative.json names"),
           ("writes_fs", "creative_fetch.py writes the verified files into the folder it is given"),
           ("reads_fs", "the fetcher and the loaders read creative.json and the fetched files"))
#: The licence texts the line carries, each read from its publisher and recognized before it is carried.
LICENCE_TEXT_ADDRESSES = {
    "CC0-1.0": https_address("creativecommons.org", "publicdomain/zero/1.0/legalcode.txt"),
    "CC-BY-4.0": https_address("creativecommons.org", "licenses/by/4.0/legalcode.txt"),
    "Apache-2.0": https_address("www.apache.org", "licenses/LICENSE-2.0.txt")}
LICENCE_HOSTS = ("creativecommons.org", "www.apache.org")
#: The name every read and streamed download of the line carries. Poly Haven's API terms (2.4) ask that all API
#: calls carry a unique user agent that matches the software's name, so its requests can be tracked together.
USER_AGENT = "Baltor-creative-assets/1.0 (+https://baltor.ai; read-only reader for pinned CC0 asset recipes)"

# -- Poly Haven -------------------------------------------------------------------------------------------------
POLYHAVEN_API = "api.polyhaven.com"
POLYHAVEN_SITE = "polyhaven.com"
POLYHAVEN_DOWNLOADS = "dl.polyhaven.org"
POLYHAVEN_HOSTS = (POLYHAVEN_API, POLYHAVEN_SITE, POLYHAVEN_DOWNLOADS)
POLYHAVEN_TERMS_REPOSITORY, POLYHAVEN_TERMS_PATH = "Poly-Haven/Public-API", "ToS.md"
POLYHAVEN_LICENCE_PAGE = https_address(POLYHAVEN_SITE, "license")
POLYHAVEN_TYPES = {0: "hdri", 1: "texture", 2: "model"}
#: The clauses the line relies on, each a phrase its document must still hold (case and spacing folded).
POLYHAVEN_TERMS = ("published under the cc0 license", "including commercial use", "build on that data",
                   "user-agent")
POLYHAVEN_LICENCE = ("all assets", "licensed as cc0", "you can use our assets for any purpose",
                     "you can redistribute them")
#: The formats each asset type offers, and the map files of a texture's plain maps variant.
POLYHAVEN_FORMATS = {"texture": ("gltf", "blend", "mtlx"), "model": ("gltf", "blend", "fbx", "usd")}
POLYHAVEN_MAPS = ("Diffuse", "nor_gl", "Rough", "AO", "Displacement", "Metal")

# -- ambientCG --------------------------------------------------------------------------------------------------
AMBIENTCG_SITE = "ambientcg.com"
AMBIENTCG_DOCS = "docs.ambientcg.com"
AMBIENTCG_DOWNLOADS = "acg-download.struffelproductions.com"
AMBIENTCG_HOSTS = (AMBIENTCG_SITE, AMBIENTCG_DOCS, AMBIENTCG_DOWNLOADS)
AMBIENTCG_LICENCE_PAGE = https_address(AMBIENTCG_DOCS, "license/")
AMBIENTCG_API_PAGE = https_address(AMBIENTCG_DOCS, "api/")
AMBIENTCG_LICENCE = ("all ambientcg assets are provided under the creative commons cc0 1.0 universal license",
                     "this applies to the downloadable asset files")
AMBIENTCG_API_TERMS = ("search and download assets using code",)
AMBIENTCG_TYPES = {"material": "material", "hdri": "hdri", "3d-model": "model"}
AMBIENTCG_INCLUDE = "type,title,url,tags,dimensions,downloads,maps,technique,releaseDate"
#: The quality levels of a model's downloads the line pins (low and standard; high quality is opt-in by hand).
AMBIENTCG_MODEL_LEVELS = ("LQ", "SQ")
AMBIENTCG_PAGE_LIMIT = 500

_SLUG = re.compile(r"[^a-z0-9]+")
_MAP_ROLES = (("_diff_", "diffuse"), ("_col_", "diffuse"), ("_nor_gl_", "normal_gl"), ("_nor_dx_", "normal_dx"),
              ("_rough_", "roughness"), ("_ao_", "ao"), ("_disp_", "displacement"), ("_arm_", "arm"),
              ("_metal_", "metalness"), ("_spec_", "specular"), ("_bump_", "bump"), ("_mask_", "mask"),
              ("_alpha_", "opacity"), ("_opacity_", "opacity"), ("_emission_", "emission"))
_ACG_ROLES = (("_color.", "diffuse"), ("_normalgl.", "normal_gl"), ("_normaldx.", "normal_dx"),
              ("_roughness.", "roughness"), ("_ambientocclusion.", "ao"), ("_displacement.", "displacement"),
              ("_metalness.", "metalness"), ("_opacity.", "opacity"), ("_emission.", "emission"))
_SUFFIX_ROLES = {".blend": "blend", ".tres": "godot_material", ".mtlx": "materialx", ".usdc": "usd",
                 ".usda": "usd", ".usd": "usd", ".mtl": "material_library", ".bin": "gltf_buffer"}
_MODEL_SUFFIXES = (".gltf", ".glb", ".fbx", ".obj", ".usd", ".usdc", ".usda", ".usdz")


class AssetRefused(ValueError):
    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason, self.detail = reason, detail


def shipped(name: str) -> bytes:
    """The bytes of a file every package of the line carries (tools/supply_lines/creative_files)."""
    return (SHIPPED / name).read_bytes()


def slug(value: str) -> str:
    return _SLUG.sub("-", str(value).lower()).strip("-")[:60] or "asset"


def folded(text: str) -> str:
    """Text with tags removed, entities decoded, spacing folded and letters lowered, for clause matching."""
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", text, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip().lower()


def missing_clauses(text: str, clauses) -> list:
    body = folded(text)
    return [clause for clause in clauses if clause not in body]


# -- terms and licence texts --------------------------------------------------------------------------------------
class LicenceTexts:
    """The licence texts a run carries, read once from their publishers and recognized by the library's matcher."""

    def __init__(self, reader) -> None:
        self.reader, self.found = reader, {}

    def get(self, spdx: str) -> dict:
        if spdx not in self.found:
            address = LICENCE_TEXT_ADDRESSES.get(spdx)
            if address is None:
                raise AssetRefused("licence_unknown", f"no licence text address for {spdx}")
            answer = self.reader.get(address)
            if answer.status != 200:
                raise AssetRefused("licence_unknown", f"{address} answered {answer.status}")
            matched = match_licence(answer.body.decode("utf-8", "replace"))
            if matched.spdx != spdx:
                raise AssetRefused("licence_signals_disagree", f"{address} reads as {matched.spdx}, not {spdx}")
            self.found[spdx] = {"spdx": spdx, "url": address, "bytes": answer.body, "sha256": answer.sha256,
                                "retrieved_at": answer.retrieved_at}
        return self.found[spdx]

    def fact(self, spdx: str) -> dict:
        text = self.get(spdx)
        return fact_source(text["url"], text["retrieved_at"], text["sha256"], len(text["bytes"]), "licence_text",
                           spdx=spdx, basis="licence_legal_code_from_its_publisher")


def terms_document(answer, clauses, label: str, basis: str) -> dict:
    """A pinned terms or licence statement, refused when unreadable or when it no longer holds the clauses."""
    if answer.status != 200:
        raise AssetRefused("terms_unreadable", f"{label}: {answer.url} answered {answer.status}")
    missing = missing_clauses(answer.body.decode("utf-8", "replace"), clauses)
    if missing:
        raise AssetRefused("terms_not_confirmed", f"{label} no longer says {missing[0]!r}")
    return {"url": answer.url, "sha256": answer.sha256, "size_bytes": len(answer.body),
            "retrieved_at": answer.retrieved_at, "clauses": list(clauses), "label": label,
            "fact": fact_source(answer.url, answer.retrieved_at, answer.sha256, len(answer.body), TERMS_OF_USE,
                                spdx="NOASSERTION", basis=basis)}


# -- the package tests ------------------------------------------------------------------------------------------
LOOPBACK = ("127.0.0.1", "::1", "localhost")


def run_package_tests(folder: Path, modules) -> tuple:
    """(passed, tests run, skipped, tail) of a package's own test modules, in this process, with every connection
    refused except to the loopback address (the fetcher's tests serve their fixtures there)."""
    saved_path, saved_modules, saved_bytecode = list(sys.path), set(sys.modules), sys.dont_write_bytecode
    connect, connect_ex = socket.socket.connect, socket.socket.connect_ex
    sys.dont_write_bytecode = True

    def guarded(original):
        def call(self, address):
            host = address[0] if isinstance(address, tuple) else address
            if host not in LOOPBACK:
                raise OSError("the network is closed while generated tests run (loopback only)")
            return original(self, address)
        return call

    socket.socket.connect, socket.socket.connect_ex = guarded(connect), guarded(connect_ex)
    stream = io.StringIO()
    try:
        suite = unittest.TestSuite()
        for module in modules:
            specification = importlib.util.spec_from_file_location(module, folder / f"{module}.py")
            loaded = importlib.util.module_from_spec(specification)
            specification.loader.exec_module(loaded)
            suite.addTests(unittest.TestLoader().loadTestsFromModule(loaded))
        result = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)
        return (result.wasSuccessful() and result.testsRun > len(result.skipped), result.testsRun,
                len(result.skipped), stream.getvalue()[-800:])
    except Exception as error:  # noqa: BLE001 - a package whose tests cannot even load is refused, never stored
        return False, 0, 0, f"{type(error).__name__}: {error}"[:800]
    finally:
        socket.socket.connect, socket.socket.connect_ex = connect, connect_ex
        sys.dont_write_bytecode = saved_bytecode
        sys.path[:] = saved_path
        for name in set(sys.modules) - saved_modules:
            del sys.modules[name]


def node_check(snippet: str, staging: Path) -> str:
    """'passed' when node parses the three.js snippet as an ES module, a skip note when node is missing; refuse a
    snippet node rejects."""
    node = shutil.which("node")
    if node is None:
        return "skipped: node is not installed on the generating machine"
    staging.mkdir(parents=True, exist_ok=True)
    path = staging / f"snippet-{hashlib.sha256(snippet.encode()).hexdigest()[:16]}.mjs"
    path.write_text(snippet, encoding="utf-8")
    try:
        done = subprocess.run([node, "--check", str(path)], capture_output=True, text=True, timeout=60, check=False)
    finally:
        path.unlink(missing_ok=True)
    if done.returncode != 0:
        raise SupplyRecordError(GENERATED_TEST_FAILED, f"node --check refused the three.js snippet: "
                                                       f"{done.stderr.strip()[-200:]}")
    return "passed"


# -- pinning files ----------------------------------------------------------------------------------------------
class Pinner:
    """Digests of the files a run pins: each address downloaded once (streamed, never kept) and checked against
    the size (and MD5, when published) its publisher states."""

    def __init__(self, reader) -> None:
        self.reader = reader
        self.found = {}
        self.dropped = Counter()

    def pin(self, url: str, size: int, md5: "str | None" = None, inspect=None):
        """The digest, or None when the address does not answer with the file; AssetRefused when the bytes are
        not the ones the publisher describes."""
        key = (url, size, md5)
        if key not in self.found:
            published = {"size": size, **({"md5": md5} if md5 else {})}
            answer = self.reader.digest(url, published=published, maximum_bytes=MAXIMUM_PINNED_FILE_BYTES,
                                        inspect=inspect)
            if not answer.ok:
                self.dropped["download_failed"] += 1
                self.found[key] = None
            elif answer.size_bytes != size or (md5 and answer.md5 != md5):
                raise AssetRefused("published_checksum_mismatch",
                                   f"{url}: {answer.size_bytes} bytes MD5 {answer.md5}, published {size} {md5}")
            else:
                self.found[key] = answer
        return self.found[key]


def file_row(path: str, url: str, answer, role: str, *, md5: "str | None" = None, **extra) -> dict:
    row = {"path": path, "url": url, "size_bytes": answer.size_bytes, "sha256": answer.sha256, "role": role}
    if md5:
        row["md5"] = md5
    row.update(extra)
    return row


def unique_roles(rows) -> list:
    """Each role once per variant: a second file of one role keeps its role with its format appended."""
    seen = set()
    for row in rows:
        role = row["role"]
        if role in seen:
            row["role"] = f"{role}_{PurePosixPath(row['path']).suffix.lstrip('.').lower() or 'file'}"
        seen.add(row["role"])
    return rows


def finished_variant(identifier: str, rows, **facts) -> dict:
    rows = unique_roles(rows)
    main = next((row["path"] for row in rows if row["role"] in ("environment", "model", "scene", "blend",
                                                                "materialx", "archive")), rows[0]["path"])
    return {"id": identifier, **facts, "main": main, "total_bytes": sum(row["size_bytes"] for row in rows),
            "files": rows}


# -- one asset package ------------------------------------------------------------------------------------------
THREE_HEADER = 'import * as THREE from "three";\n'


def threejs_snippet(manifest: dict, folder: str) -> str:
    """A three.js ES module that loads the default variant from ``folder`` (the fetch folder)."""
    variant = next(row for row in manifest["variants"] if row["id"] == manifest["default_variant"])
    files = {}
    for item in variant["files"]:
        for row in (item.get("members") or []) if item.get("unpack") else [item]:
            files.setdefault(row["role"], row["path"])
    kind = manifest["asset"]["type"]
    base = folder.rstrip("/") + "/"
    if kind == "hdri":
        path = files["environment"]
        loader = "EXRLoader" if path.lower().endswith(".exr") else "HDRLoader"
        return (THREE_HEADER + f'import {{ {loader} }} from "three/addons/loaders/{loader}.js";\n\n'
                "const scene = new THREE.Scene();\n"
                f"new {loader}().load({json.dumps(base + path)}, (texture) => {{\n"
                "  texture.mapping = THREE.EquirectangularReflectionMapping;\n"
                "  scene.background = texture;\n  scene.environment = texture;\n});\n")
    if kind == "model":
        path = files["model"]
        if path.lower().endswith((".gltf", ".glb")):
            return (THREE_HEADER + 'import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";\n\n'
                    "const scene = new THREE.Scene();\n"
                    f"new GLTFLoader().load({json.dumps(base + path)}, (gltf) => scene.add(gltf.scene));\n")
        if path.lower().endswith(".obj") and "material_library" in files:
            return (THREE_HEADER + 'import { MTLLoader } from "three/addons/loaders/MTLLoader.js";\n'
                    'import { OBJLoader } from "three/addons/loaders/OBJLoader.js";\n\n'
                    "const scene = new THREE.Scene();\n"
                    f"new MTLLoader().setPath({json.dumps(base)}).load({json.dumps(files['material_library'])}, "
                    "(materials) => {\n  materials.preload();\n"
                    f"  new OBJLoader().setMaterials(materials).setPath({json.dumps(base)})\n"
                    f"    .load({json.dumps(path)}, (object) => scene.add(object));\n}});\n")
        return (THREE_HEADER + 'import { FBXLoader } from "three/addons/loaders/FBXLoader.js";\n\n'
                "const scene = new THREE.Scene();\n"
                f"new FBXLoader().load({json.dumps(base + path)}, (object) => scene.add(object));\n")
    width = (manifest["asset"].get("dimensions_mm") or [2000])[0] or 2000
    lines = [THREE_HEADER, "const loader = new THREE.TextureLoader();",
             f"const folder = {json.dumps(base)};"]
    properties = []
    for role, name, colour in (("diffuse", "map", True), ("normal_gl", "normalMap", False),
                               ("roughness", "roughnessMap", False), ("metalness", "metalnessMap", False),
                               ("ao", "aoMap", False), ("displacement", "displacementMap", False)):
        if role in files:
            lines.append(f"const {name} = loader.load(folder + {json.dumps(files[role])});")
            if colour:
                lines.append(f"{name}.colorSpace = THREE.SRGBColorSpace;")
            properties.append(name)
    lines += [f"const material = new THREE.MeshStandardMaterial({{ {', '.join(properties)} }});",
              f"const plane = new THREE.Mesh(new THREE.PlaneGeometry({width / 1000:g}, {width / 1000:g}), material);",
              "const scene = new THREE.Scene();", "scene.add(plane);", ""]
    return "\n".join(lines)


def variants_table(manifest: dict) -> str:
    rows = ["| Variant | Format | Resolution | Files | Bytes | Main file |", "|---|---|---|---|---|---|"]
    for variant in manifest["variants"]:
        mark = " (default)" if variant["id"] == manifest["default_variant"] else ""
        rows.append(f"| `{variant['id']}`{mark} | {variant.get('format', '')} | {variant.get('resolution', '')} | "
                    f"{len(variant['files'])} | {variant['total_bytes']:,} | `{variant['main']}` |")
    return "\n".join(rows)


BLENDER_LINES = {"hdri": "the HDRI becomes the world's environment light",
                 "model": "the model is imported, or appended from its .blend file",
                 "texture": "the material lands on a plane of the texture's real size",
                 "material": "the material lands on a plane of the material's real size"}
GODOT_LINES = {"hdri": "the HDRI becomes the sky and its light",
               "model": "the glTF variant loads at run time; OBJ, FBX and .blend need the editor's import",
               "texture": "a StandardMaterial3D from the maps on a plane",
               "material": "a StandardMaterial3D from the maps on a plane"}


def asset_readme(manifest: dict, source_label: str, credit: str, snippet: str, not_pinned: str) -> str:
    asset, default = manifest["asset"], manifest["default_variant"]
    identity = manifest["job"]["identity"]
    folder = f"assets/{identity}"
    facts = []
    if asset.get("category"):
        facts.append(f"Category: {asset['category']}.")
    if asset.get("tags"):
        facts.append("Tags: " + ", ".join(asset["tags"][:16]) + ".")
    if asset.get("authors"):
        facts.append("Authors: " + ", ".join(f"{name} ({role})" if role else name
                                             for name, role in asset["authors"].items()) + ".")
    if asset.get("dimensions_mm"):
        facts.append("Real-world size: " + " x ".join(f"{value / 1000:g}" for value in asset["dimensions_mm"])
                     + " m.")
    if asset.get("polycount"):
        facts.append(f"Polygons: {asset['polycount']:,}.")
    hosts = ", ".join(f"`{host}`" for host in manifest["hosts"])
    return f"""# {asset['name']}: {TYPE_LABELS[asset['type']]} from {source_label} (CC0)

A pinned download recipe for the {TYPE_LABELS[asset['type']]} **{asset['name']}** from {source_label}
({asset['source_page']}), with a fetcher that keeps only the exact recorded bytes and loaders for Blender,
Godot 4 and three.js. {' '.join(facts)}

The asset is licensed CC0 1.0 (a public domain dedication): {credit} Credit is not required by the licence;
this package names {source_label} as the source. Baltor is not affiliated with or endorsed by {source_label}.

## Variants

{variants_table(manifest)}

`creative.json` pins every file by its exact address on {hosts}, its size and its SHA-256. Baltor re-hosts
none of them; the files come from the origin when you fetch. {not_pinned}

## Fetch

```bash
python creative_fetch.py list
python creative_fetch.py fetch {default} {folder}
```

The fetcher refuses an address that is not HTTPS on a listed host, a redirect anywhere else, a path that
leaves the folder, and any file whose size or SHA-256 is not the recorded one; nothing refused is left behind.
A file already in place with the recorded digest is not downloaded again.

## Load

Blender 4 ({BLENDER_LINES[asset['type']]}):

```bash
blender --background --python blender_load.py -- {folder} {default}
```

Godot 4 ({GODOT_LINES[asset['type']]}): copy `creative.json` and `godot_load.gd` into the project, fetch into
`res://{folder}`, attach the script to a Node3D and set `asset_folder` to `res://{folder}`.

three.js r180 or later (older releases name the HDR loader RGBELoader):

```js
{snippet.rstrip()}
```

## Tests

```bash
python -m unittest test_creative_fetch test_creative_loaders
```

The tests run offline: the fetcher against a server on the loopback address (with known-wrong bytes, sizes,
paths, addresses and archives that must be refused) and the Blender loader against a recording stand-in for
`bpy`. When Godot 4 is installed, its own parser checks `godot_load.gd`.
"""


def asset_package(manifest: dict, *, line_identity: str, origin: str, repository: str, path: str, revision: str,
                  facts, generator: dict, licence_text: bytes, cc0: dict, generated_on: str, staging: Path,
                  source_label: str, credit: str, not_pinned: str, extra_repository: dict) -> tuple:
    """Build, test and check one asset package; (payload, bodies) or SupplyRecordError."""
    asset = manifest["asset"]
    identity = manifest["job"]["identity"]
    name = f"{manifest['job']['source']}-{slug(identity)}-{asset['type']}"
    snippet = threejs_snippet(manifest, f"assets/{identity}")
    folder = staging / name
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    manifest_text = json.dumps(manifest, indent=1, ensure_ascii=False) + "\n"
    shipped_rows = [(FETCHER, "executable_tool", None), (BLENDER_LOADER, "executable_tool", None),
                    (GODOT_LOADER, "other", GDSCRIPT_MEDIA), (FETCH_TESTS, "executable_tool", None),
                    (LOADER_TESTS, "executable_tool", None)]
    for file_name, _role, _media in shipped_rows:
        (folder / file_name).write_bytes(shipped(file_name))
    (folder / MANIFEST_NAME).write_text(manifest_text, encoding="utf-8")
    try:
        syntax = node_check(snippet, staging)
        passed, count, skipped, output = run_package_tests(folder, ("test_creative_fetch", "test_creative_loaders"))
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    if not passed:
        raise SupplyRecordError(GENERATED_TEST_FAILED, output[-280:])
    text = asset_readme(manifest, source_label, credit, snippet, not_pinned)
    files = [PackageFile(file_name, shipped(file_name), role, media_type=media)
             for file_name, role, media in shipped_rows]
    files += [PackageFile(MANIFEST_NAME, manifest_text.encode("utf-8"), "other"),
              PackageFile("README.md", text.encode("utf-8"), "other"),
              PackageFile(LICENCE_NAME, licence_text, "other", LICENCE_TEXT),
              PackageFile(UPSTREAM_LICENCE_NAME, cc0["bytes"], "other", LICENCE_TEXT,
                          {"url": cc0["url"], "sha256": cc0["sha256"]})]
    godot = shutil.which("godot") or shutil.which("godot4")
    supply = SupplyPackage(
        line=CREATIVE_ASSETS, identity=line_identity, key=upstream_key(CREATIVE_ASSETS, line_identity),
        kind=TYPE_FORMS[asset["type"]], native_format=NATIVE_FORMAT, form=TYPE_FORMS[asset["type"]], name=name,
        description=(f"{asset['name']}, a CC0 {TYPE_LABELS[asset['type']]} from {source_label}: a pinned download "
                     f"recipe ({', '.join(variant['id'] for variant in manifest['variants'])}) with a fetcher that "
                     "verifies every byte and loaders for Blender, Godot 4 and three.js."),
        files=files, licence_expression=f"{GENERATED_CODE_LICENCE} AND CC0-1.0",
        provenance=provenance(origin, repository, path, revision, facts, generator),
        placements=[{"harness": "reference", "path": f"assets/{name}/", "basis": "documented_layout",
                     "scope": "project", "support": "unverified"}],
        effects=list(EFFECTS), credentials=[],
        tests={"files": [FETCH_TESTS, LOADER_TESTS],
               "command": "python -m unittest test_creative_fetch test_creative_loaders", "result": "passed",
               "tests_run": count, "skipped": skipped, "network": "loopback_only", "threejs_snippet": syntax,
               "godot_parse": "ran" if godot else "skipped: godot is not installed on the generating machine",
               "blender": "recording stand-in for bpy; Blender itself not run"},
        repository={"name": source_label, "source": manifest["job"]["source"], "asset": identity,
                    "asset_type": asset["type"], "asset_role": asset["asset_role"],
                    "variants": len(manifest["variants"]),
                    "pinned_bytes": sum({row["sha256"]: row["size_bytes"] for variant in manifest["variants"]
                                         for row in variant["files"]}.values()),
                    "stars": 0, **extra_repository},
        generated_on=generated_on, comparison_text=line_identity)
    return build(supply)


def refusal_for(error: SupplyRecordError) -> str:
    """The line's reason for a package that failed to build."""
    if error.code in (BLOCKED_BY_STATIC_CHECK, PACKAGE_ABOVE_REVIEW_BOUND, PACKAGE_PATH_INVALID):
        return error.code
    return GENERATED_TEST_FAILED


def manifest_record(source: str, identity: str, asset: dict, licence: dict, variants: list, default: str,
                    hosts) -> dict:
    return {"record_type": MANIFEST_RECORD_TYPE, "job": {"source": source, "identity": identity}, "asset": asset,
            "licence": licence, "hosts": sorted(set(hosts)), "default_variant": default, "variants": variants}


def default_variant(variants: list, preferences) -> str:
    """The first variant whose id starts with a preferred prefix, at the highest resolution offered."""
    for prefix in preferences:
        found = [row for row in variants if row["id"].startswith(prefix)]
        if found:
            return sorted(found, key=lambda row: RESOLUTIONS.index(row["resolution"])
                          if row.get("resolution") in RESOLUTIONS else -1)[-1]["id"]
    return variants[0]["id"]


def round_robin(groups: dict, maximum: int) -> list:
    """Items taken one per group in turn, each group in its own order, at most ``maximum`` (0: every item)."""
    queues = {name: list(items) for name, items in groups.items()}
    chosen = []
    while any(queues.values()) and (not maximum or len(chosen) < maximum):
        for name in list(queues):
            if queues[name] and (not maximum or len(chosen) < maximum):
                chosen.append(queues[name].pop(0))
    return chosen


# -- Poly Haven -------------------------------------------------------------------------------------------------
def polyhaven_role(path: str, asset_type: str) -> str:
    name = PurePosixPath(path).name.lower()
    suffix = PurePosixPath(name).suffix
    if suffix in _MODEL_SUFFIXES:
        return "model" if asset_type == "model" else "scene"
    if suffix in (".hdr", ".exr") and asset_type == "hdri":
        return "environment"
    if suffix in _SUFFIX_ROLES:
        return _SUFFIX_ROLES[suffix]
    for token, role in _MAP_ROLES:
        if token in name:
            return role
    return "file"


def polyhaven_candidates(asset_type: str, files: dict, resolutions) -> list:
    """(id, format, resolution, [(path, entry, role)]) of every variant the files record offers."""
    found = []
    if asset_type == "hdri":
        for resolution in resolutions:
            for file_format in ("hdr", "exr"):
                entry = ((files.get("hdri") or {}).get(resolution) or {}).get(file_format)
                if entry:
                    found.append((f"{file_format}-{resolution}", file_format, resolution,
                                  [(PurePosixPath(urllib.parse.urlsplit(entry["url"]).path).name, entry,
                                    "environment")]))
        return found
    for file_format in POLYHAVEN_FORMATS[asset_type]:
        for resolution in resolutions:
            entry = ((files.get(file_format) or {}).get(resolution) or {}).get(file_format)
            if not entry:
                continue
            main = PurePosixPath(urllib.parse.urlsplit(entry["url"]).path).name
            # A model's main file is the model whatever its format (a .blend file included); a texture's is the
            # scene, Blender file or MaterialX document that holds the material.
            parts = [(main, entry, "model" if asset_type == "model" else polyhaven_role(main, asset_type))]
            parts += [(include, value, polyhaven_role(include, asset_type))
                      for include, value in sorted((entry.get("include") or {}).items())]
            found.append((f"{file_format}-{resolution}", file_format, resolution, parts))
    if asset_type == "texture":
        for resolution in resolutions:
            parts = []
            for key in POLYHAVEN_MAPS:
                entry = ((files.get(key) or {}).get(resolution) or {}).get("jpg")
                if entry:
                    name = PurePosixPath(urllib.parse.urlsplit(entry["url"]).path).name
                    parts.append((f"textures/{name}", entry, polyhaven_role(name, asset_type)))
            if parts:
                found.append((f"jpg-{resolution}", "jpg", resolution, parts))
    return found


def polyhaven_resolutions(asset_type: str, files: dict) -> set:
    """Every resolution the files record offers for the asset type's formats."""
    keys = ("hdri",) if asset_type == "hdri" else POLYHAVEN_FORMATS[asset_type]
    return {resolution for key in keys for resolution in (files.get(key) or {})}


def pinned_variants(pinner: Pinner, candidates, counts: Counter) -> list:
    """The candidates within the pin bounds whose every file was downloaded and checked."""
    variants = []
    for identifier, file_format, resolution, parts in candidates:
        if any(int(entry["size"]) > MAXIMUM_PINNED_FILE_BYTES for _path, entry, _role in parts) or \
                sum(int(entry["size"]) for _path, entry, _role in parts) > MAXIMUM_VARIANT_BYTES:
            counts["variant_above_the_pin_bound"] += 1
            continue
        rows = []
        for path, entry, role in parts:
            answer = pinner.pin(entry["url"], int(entry["size"]), entry.get("md5"))
            if answer is None:
                rows = None
                break
            rows.append(file_row(path, entry["url"], answer, role, md5=entry.get("md5")))
        if rows is None:
            counts["variant_download_failed"] += 1
            continue
        variants.append(finished_variant(identifier, rows, format=file_format, resolution=resolution))
    return variants


def polyhaven_asset(info: dict, asset_type: str, identity: str) -> dict:
    tags = sorted({str(tag).strip() for tag in info.get("tags") or () if str(tag).strip()})
    dimensions = [value for value in info.get("dimensions") or () if isinstance(value, (int, float))]
    asset = {"name": str(info.get("name") or identity), "type": asset_type,
             "source_page": https_address(POLYHAVEN_SITE, f"a/{identity}"), "category": info.get("category"),
             "categories": list(info.get("categories") or ()), "tags": tags,
             "authors": {str(name): str(role) for name, role in (info.get("authors") or {}).items()},
             "asset_role": ASSET_ROLES[asset_type], "credit": "Poly Haven (polyhaven.com)",
             "files_hash": info.get("files_hash"), "max_resolution": info.get("max_resolution")}
    if dimensions and asset_type != "hdri":
        asset["dimensions_mm"] = [round(value, 3) for value in dimensions]
    if info.get("polycount"):
        asset["polycount"] = int(info["polycount"])
    if info.get("date_published"):
        asset["published_epoch_seconds"] = int(info["date_published"])
    return {key: value for key, value in asset.items() if value not in (None, [], {})}


def polyhaven_terms(reader) -> tuple:
    """(licence page, API terms) pinned and checked, or AssetRefused for the whole source."""
    page = terms_document(reader.get(POLYHAVEN_LICENCE_PAGE), POLYHAVEN_LICENCE, "Poly Haven's licence page",
                          "poly_haven_licence_page_states_every_asset_cc0")
    try:
        pinned = reader.pinned_file(POLYHAVEN_TERMS_REPOSITORY, "master", POLYHAVEN_TERMS_PATH)
    except LookupError as error:
        raise AssetRefused("terms_unreadable", f"Poly Haven's API terms: {error}") from None
    missing = missing_clauses(pinned["bytes"].decode("utf-8", "replace"), POLYHAVEN_TERMS)
    if missing:
        raise AssetRefused("terms_not_confirmed", f"Poly Haven's API terms no longer say {missing[0]!r}")
    address = github_blob_address(POLYHAVEN_TERMS_REPOSITORY, pinned["commit"], POLYHAVEN_TERMS_PATH)
    terms = {"url": address, "sha256": pinned["sha256"], "size_bytes": len(pinned["bytes"]),
             "retrieved_at": pinned["retrieved_at"], "clauses": list(POLYHAVEN_TERMS), "label": "Poly Haven API terms",
             "fact": fact_source(address, pinned["retrieved_at"], pinned["sha256"], len(pinned["bytes"]),
                                 TERMS_OF_USE, spdx="NOASSERTION",
                                 basis="poly_haven_api_terms_at_the_pinned_commit")}
    return page, terms, pinned["bytes"]


def generate_polyhaven(reader, *, code_revision: str, licence_text: bytes, generated_on: str, staging: Path,
                       resolutions=DEFAULT_RESOLUTIONS, only=(), maximum_assets: int = 0) -> tuple:
    """(built, refusals, facts, summary) of Poly Haven's assets: every asset, or the chosen ones."""
    built, refused, facts, counts = [], [], {}, Counter()
    generator = {"identity": "tools/supply_lines/creative_assets.py", "version": GENERATOR_VERSION,
                 "code_revision": code_revision}
    texts = LicenceTexts(reader)
    try:
        page, terms, terms_bytes = polyhaven_terms(reader)
        cc0 = texts.get("CC0-1.0")
    except AssetRefused as error:
        return [], [refusal(CREATIVE_ASSETS, error.reason, POLYHAVEN, error.detail)], {}, {"held": error.reason}
    facts[cc0["sha256"]] = cc0["bytes"]
    facts[terms["sha256"]] = terms_bytes
    listing = reader.get(https_address(POLYHAVEN_API, "assets"))
    if listing.status != 200:
        return [], [refusal(CREATIVE_ASSETS, "source_unreadable", POLYHAVEN, f"assets answered {listing.status}")], \
            facts, {}
    facts[listing.sha256] = listing.body
    catalogue = json.loads(listing.body)
    groups = {}
    for identity, entry in sorted(catalogue.items(), key=lambda item: (-int(item[1].get("download_count") or 0),
                                                                        item[0])):
        if only and identity not in only:
            continue
        asset_type = POLYHAVEN_TYPES.get(entry.get("type"))
        if asset_type is None:
            refused.append(refusal(CREATIVE_ASSETS, "asset_type_not_supplied", identity, str(entry.get("type"))))
            continue
        groups.setdefault(asset_type, []).append(identity)
    chosen = round_robin(groups, maximum_assets)
    summary = {"catalogue_assets": len(catalogue), "chosen": len(chosen),
               "chosen_by_type": dict(Counter(POLYHAVEN_TYPES[catalogue[identity]["type"]] for identity in chosen))}
    pinner = Pinner(reader)
    seen = set()
    for identity in chosen:
        if identity in seen:
            refused.append(refusal(CREATIVE_ASSETS, "duplicate_asset", identity))
            continue
        seen.add(identity)
        asset_type = POLYHAVEN_TYPES[catalogue[identity]["type"]]
        info = reader.get(https_address(POLYHAVEN_API, f"info/{identity}"))
        record = reader.get(https_address(POLYHAVEN_API, f"files/{identity}"))
        if info.status != 200 or record.status != 200:
            refused.append(refusal(CREATIVE_ASSETS, "asset_unreadable", identity,
                                   f"info {info.status}, files {record.status}"))
            continue
        facts[info.sha256], facts[record.sha256] = info.body, record.body
        try:
            details = json.loads(info.body)
            candidates = polyhaven_candidates(asset_type, json.loads(record.body), resolutions)
            variants = pinned_variants(pinner, candidates, counts)
        except AssetRefused as error:
            refused.append(refusal(CREATIVE_ASSETS, error.reason, identity, error.detail))
            continue
        except (ValueError, KeyError, TypeError) as error:
            refused.append(refusal(CREATIVE_ASSETS, "asset_unreadable", identity, f"{type(error).__name__}: {error}"))
            continue
        if not variants:
            refused.append(refusal(CREATIVE_ASSETS, "no_variant_pinned", identity,
                                   f"{len(candidates)} offered at {','.join(resolutions)}, none pinned"))
            continue
        asset = polyhaven_asset(details, asset_type, identity)
        default = default_variant(variants, {"hdri": ("hdr-",), "texture": ("jpg-", "gltf-"),
                                             "model": ("gltf-", "fbx-")}[asset_type])
        licence = {"spdx": "CC0-1.0", "binding": (
            "The asset is listed by api.polyhaven.com (its files record is pinned below), the catalogue of the "
            "site whose licence page states that all its assets are licensed CC0, and the API terms say the assets "
            "are published under CC0."),
            "evidence": [{"url": page["url"], "sha256": page["sha256"], "statement": "all assets ... licensed as CC0"},
                         {"url": terms["url"], "sha256": terms["sha256"],
                          "statement": "our 3D assets themselves are published under the CC0 license"}],
            "files_record": {"url": record.url, "sha256": record.sha256}}
        manifest = manifest_record(POLYHAVEN, identity, asset, licence, variants, default, (POLYHAVEN_DOWNLOADS,))
        offered = sorted(polyhaven_resolutions(asset_type, json.loads(record.body)) - set(resolutions),
                         key=lambda value: (len(value), value))
        not_pinned = (f"Poly Haven also publishes {', '.join(offered)}; this recipe pins "
                      f"{' and '.join(resolutions)} to bound what its generator downloads." if offered else "")
        package_facts = [fact_source(info.url, info.retrieved_at, info.sha256, len(info.body), "registry_entry",
                                     spdx="NOASSERTION", basis="poly_haven_api_record_read_under_its_terms"),
                         fact_source(record.url, record.retrieved_at, record.sha256, len(record.body),
                                     "registry_entry", spdx="NOASSERTION",
                                     basis="poly_haven_api_record_read_under_its_terms"),
                         page["fact"], terms["fact"], texts.fact("CC0-1.0")]
        package_facts += pinned_facts(variants, pinner, page["sha256"],
                                      "listed_by_the_poly_haven_api_whose_licence_page_states_every_asset_cc0")
        try:
            built.append(asset_package(
                manifest, line_identity=f"{POLYHAVEN}:{identity}", origin="poly_haven_api", repository=POLYHAVEN,
                path=f"files/{identity}", revision=f"files_hash:{details.get('files_hash') or record.sha256}",
                facts=package_facts, generator=generator, licence_text=licence_text, cc0=cc0,
                generated_on=generated_on, staging=staging, source_label="Poly Haven",
                credit="Poly Haven's licence page states that all its assets are CC0, and its API terms say the "
                       "assets are published under CC0.",
                not_pinned=not_pinned, extra_repository={"files_hash": details.get("files_hash")}))
        except SupplyRecordError as error:
            refused.append(refusal(CREATIVE_ASSETS, refusal_for(error), identity, str(error)[:280]))
    summary.update({"variant_counts": dict(counts), "downloads_dropped": dict(pinner.dropped),
                    "pinned_files": sum(1 for value in pinner.found.values() if value),
                    "pinned_bytes": sum(value.size_bytes for value in pinner.found.values() if value)})
    return built, refused, facts, summary


def pinned_facts(variants, pinner: Pinner, evidence_sha256: str, basis: str) -> list:
    """One data_source fact per distinct pinned file: its address, retrieval time, digest and CC0 licence."""
    found = {}
    for variant in variants:
        for row in variant["files"]:
            answer = pinner.found.get((row["url"], row["size_bytes"], row.get("md5")))
            if row["sha256"] not in found and answer is not None:
                found[row["sha256"]] = fact_source(row["url"], answer.retrieved_at, row["sha256"], row["size_bytes"],
                                                   "data_source", spdx="CC0-1.0", basis=basis,
                                                   evidence_sha256=evidence_sha256)
    return list(found.values())


# -- ambientCG --------------------------------------------------------------------------------------------------
def ambientcg_role(path: str, asset_type: str) -> str:
    name = PurePosixPath(path).name.lower()
    suffix = PurePosixPath(name).suffix
    for token, role in _ACG_ROLES:
        if token in name:
            return role
    if suffix in (".hdr", ".exr"):
        return "environment"
    if suffix == ".obj" or (suffix in _MODEL_SUFFIXES and asset_type == "model" and suffix not in (".usdc", ".usda")):
        return "model"
    if suffix in _SUFFIX_ROLES:
        return _SUFFIX_ROLES[suffix]
    if suffix in (".jpg", ".jpeg", ".png", ".webp"):
        return "tonemapped" if asset_type == "hdri" else "preview"
    return "file"


def zip_members(path: Path) -> dict:
    """The members of a downloaded archive, each with its size and SHA-256, or the unsafe member that refuses it."""
    members = []
    try:
        with zipfile.ZipFile(path) as archive:
            for entry in archive.infolist():
                if entry.is_dir():
                    continue
                name = entry.filename
                parts = PurePosixPath(name).parts
                if (name.startswith("/") or "\\" in name or any(part in ("..", ".", "") for part in parts)
                        or (entry.external_attr >> 16) & 0o170000 == 0o120000):
                    return {"unsafe": name[:200]}
                digest = hashlib.sha256()
                with archive.open(entry) as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
                members.append({"path": name, "size_bytes": entry.file_size, "sha256": digest.hexdigest()})
    except (zipfile.BadZipFile, OSError) as error:
        return {"unsafe": f"not a readable archive: {type(error).__name__}"}
    return {"members": sorted(members, key=lambda row: row["path"])}


def ambientcg_wanted(asset_type: str, resolutions) -> list:
    """The download attributes the line pins, in the order offered: JPG maps for materials, the HDRI archives,
    and low and standard quality models with JPG maps."""
    upper = [resolution.upper() for resolution in resolutions]
    if asset_type == "material":
        return [f"{value}-JPG" for value in upper]
    if asset_type == "hdri":
        return upper
    return [f"{level}-{value}-JPG" for level in AMBIENTCG_MODEL_LEVELS for value in upper]


def ambientcg_variants(pinner: Pinner, asset_type: str, downloads, resolutions, counts: Counter) -> list:
    variants = []
    by_attributes = {row.get("attributes"): row for row in downloads or () if row.get("extension") == "zip"}
    for attributes in ambientcg_wanted(asset_type, resolutions):
        row = by_attributes.get(attributes)
        if row is None:
            continue
        size = int(row.get("size") or 0)
        if size <= 0 or size > MAXIMUM_PINNED_FILE_BYTES:
            counts["variant_above_the_pin_bound"] += 1
            continue
        url = str(row["url"])
        name = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get("file", [""])[0]
        if not name.endswith(".zip"):
            counts["variant_unnamed"] += 1
            continue
        answer = pinner.pin(url, size, None, inspect=zip_members)
        if answer is None:
            counts["variant_download_failed"] += 1
            continue
        listing = answer.inspected or {}
        if "members" not in listing:
            counts["variant_archive_unsafe"] += 1
            continue
        members = unique_roles([{**member, "role": ambientcg_role(member["path"], asset_type)}
                                for member in listing["members"]])
        resolution = next((value for value in RESOLUTIONS if value.upper() in attributes.split("-")), None)
        variants.append(finished_variant(attributes.lower(), [file_row(name, url, answer, "archive", unpack=True,
                                                                        members=members)],
                                         format=attributes.split("-")[-1].lower() if "-" in attributes else "zip",
                                         resolution=resolution))
    return variants


def ambientcg_terms(reader) -> tuple:
    page = terms_document(reader.get(AMBIENTCG_LICENCE_PAGE), AMBIENTCG_LICENCE, "ambientCG's licence page",
                          "ambientcg_licence_page_states_every_asset_cc0")
    api = terms_document(reader.get(AMBIENTCG_API_PAGE), AMBIENTCG_API_TERMS, "ambientCG's API page",
                         "ambientcg_api_page_invites_downloading_by_code")
    return page, api


def ambientcg_asset_address(identity: str) -> str:
    return https_address(AMBIENTCG_SITE, "api/v3/assets") + "?" + urllib.parse.urlencode(
        {"id": identity, "include": AMBIENTCG_INCLUDE})


def generate_ambientcg(reader, *, code_revision: str, licence_text: bytes, generated_on: str, staging: Path,
                       resolutions=DEFAULT_RESOLUTIONS, only=(), maximum_assets: int = 0) -> tuple:
    """(built, refusals, facts, summary) of ambientCG's materials, HDRIs and models."""
    built, refused, facts, counts = [], [], {}, Counter()
    generator = {"identity": "tools/supply_lines/creative_assets.py", "version": GENERATOR_VERSION,
                 "code_revision": code_revision}
    texts = LicenceTexts(reader)
    try:
        page, api = ambientcg_terms(reader)
        cc0 = texts.get("CC0-1.0")
    except AssetRefused as error:
        return [], [refusal(CREATIVE_ASSETS, error.reason, AMBIENTCG, error.detail)], {}, {"held": error.reason}
    facts[cc0["sha256"]] = cc0["bytes"]
    groups, total = {}, 0
    for api_type, asset_type in AMBIENTCG_TYPES.items():
        identities, offset = [], 0
        while True:
            address = https_address(AMBIENTCG_SITE, "api/v3/assets") + "?" + urllib.parse.urlencode(
                {"type": api_type, "sort": "popular", "limit": AMBIENTCG_PAGE_LIMIT, "offset": offset,
                 "include": "type"})
            answer = reader.get(address)
            if answer.status != 200:
                return [], [refusal(CREATIVE_ASSETS, "source_unreadable", AMBIENTCG,
                                    f"{api_type} listing answered {answer.status}")], facts, {}
            document = json.loads(answer.body)
            identities += [row["id"] for row in document.get("assets") or () if row.get("id")]
            total = max(total, len(identities))
            offset += AMBIENTCG_PAGE_LIMIT
            if (maximum_assets and not only) or offset >= int(document.get("totalResults") or 0):
                break
        groups[asset_type] = [identity for identity in identities if not only or identity in only]
    chosen = round_robin(groups, maximum_assets)
    types = {identity: asset_type for asset_type, identities in groups.items() for identity in identities}
    summary = {"chosen": len(chosen), "chosen_by_type": dict(Counter(types[identity] for identity in chosen))}
    pinner = Pinner(reader)
    seen = set()
    for identity in chosen:
        if identity in seen:
            refused.append(refusal(CREATIVE_ASSETS, "duplicate_asset", identity))
            continue
        seen.add(identity)
        asset_type = types[identity]
        answer = reader.get(ambientcg_asset_address(identity))
        rows = (json.loads(answer.body).get("assets") or []) if answer.status == 200 else []
        entry = next((row for row in rows if row.get("id") == identity), None)
        if entry is None:
            refused.append(refusal(CREATIVE_ASSETS, "asset_unreadable", identity, f"answered {answer.status}"))
            continue
        facts[answer.sha256] = answer.body
        try:
            variants = ambientcg_variants(pinner, asset_type, entry.get("downloads"), resolutions, counts)
        except AssetRefused as error:
            refused.append(refusal(CREATIVE_ASSETS, error.reason, identity, error.detail))
            continue
        if not variants:
            refused.append(refusal(CREATIVE_ASSETS, "no_variant_pinned", identity,
                                   f"none of {ambientcg_wanted(asset_type, resolutions)} pinned"))
            continue
        dimensions = entry.get("dimensions") or {}
        asset = {"name": str(entry.get("title") or identity), "type": asset_type,
                 "source_page": https_address(AMBIENTCG_SITE, f"a/{identity}"),
                 "tags": sorted({str(tag) for tag in entry.get("tags") or () if str(tag).strip()}),
                 "asset_role": ASSET_ROLES[asset_type], "credit": "ambientCG (ambientcg.com)",
                 "technique": entry.get("technique"), "maps": list(entry.get("maps") or ()),
                 "released": entry.get("releaseDate")}
        sides = [dimensions.get(key) for key in ("width", "height", "depth")]
        if any(isinstance(value, (int, float)) and value > 0 for value in sides):
            asset["dimensions_mm"] = [round(float(value or 0) * 10, 3) for value in sides if value is not None][:3]
        asset = {key: value for key, value in asset.items() if value not in (None, [], {}, "")}
        default = default_variant(variants, {"material": ("2k-", "1k-"), "hdri": ("2k", "1k"),
                                             "model": ("sq-", "lq-")}[asset_type])
        licence = {"spdx": "CC0-1.0", "binding": (
            "The asset is listed by ambientcg.com's API (its record is pinned below), whose licence page states "
            "that all ambientCG assets, the downloadable files and the preview renders, are provided under CC0 1.0."),
            "evidence": [{"url": page["url"], "sha256": page["sha256"],
                          "statement": "all ambientcg assets are provided under the creative commons cc0 1.0 "
                                       "universal license"}],
            "asset_record": {"url": answer.url, "sha256": answer.sha256}}
        manifest = manifest_record(AMBIENTCG, identity, asset, licence, variants, default,
                                   (AMBIENTCG_SITE, AMBIENTCG_DOWNLOADS))
        offered = sorted({row.get("attributes") for row in entry.get("downloads") or ()}
                         - {variant["id"].upper() for variant in variants})
        not_pinned = (f"ambientCG also publishes {', '.join(offered[:12])}; this recipe pins "
                      f"{', '.join(variant['id'] for variant in variants)}." if offered else "")
        package_facts = [fact_source(answer.url, answer.retrieved_at, answer.sha256, len(answer.body),
                                     "registry_entry", spdx="NOASSERTION",
                                     basis="ambientcg_api_record_read_as_its_api_page_invites"),
                         page["fact"], api["fact"], texts.fact("CC0-1.0")]
        package_facts += pinned_facts(variants, pinner, page["sha256"],
                                      "listed_by_the_ambientcg_api_whose_licence_page_states_every_asset_cc0")
        revision = canonical_digest([[variant["id"], variant["files"][0]["sha256"]] for variant in variants])
        try:
            built.append(asset_package(
                manifest, line_identity=f"{AMBIENTCG}:{identity}", origin="ambientcg_api", repository=AMBIENTCG,
                path=f"assets/{identity}", revision=f"archives:{revision[:32]}", facts=package_facts,
                generator=generator, licence_text=licence_text, cc0=cc0, generated_on=generated_on, staging=staging,
                source_label="ambientCG",
                credit="ambientCG's licence page states that all its assets, the files and the preview renders, are "
                       "provided under CC0 1.0.",
                not_pinned=not_pinned, extra_repository={}))
        except SupplyRecordError as error:
            refused.append(refusal(CREATIVE_ASSETS, refusal_for(error), identity, str(error)[:280]))
    summary.update({"variant_counts": dict(counts), "downloads_dropped": dict(pinner.dropped),
                    "pinned_files": sum(1 for value in pinner.found.values() if value),
                    "pinned_bytes": sum(value.size_bytes for value in pinner.found.values() if value)})
    return built, refused, facts, summary
