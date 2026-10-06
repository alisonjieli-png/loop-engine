"""Check and build the Baltor plugin package for OpenAI's plugin directory (ChatGPT and Codex).

    PYTHONPATH=src:tools python tools/build_chatgpt_app_package.py --check
    PYTHONPATH=src:tools python tools/build_chatgpt_app_package.py --zip OUTPUT.zip

The package lives in `integrations/chatgpt-app/`: `plugin.json` in the Agent Plugins format with OpenAI's settings
under `extensions.com.openai`, `mcp.json` naming the one remote server, and the icons and screenshots under `assets/`.
`--check` applies every rule OpenAI's submission pages state for a remote MCP plugin's final submission (the rules and
their sources are listed in docs/guides/chatgpt-app.md), the website's public wording rules, and two cross-checks with
the service: every tool a review case names is a tool the OpenAI host presentation advertises, and the server address
is this service's `/mcp`. `--zip` writes the archive with sorted entries and a fixed timestamp, so the same package
always gives the same bytes, and prints its SHA-256. Reviewer credentials and the demonstration video address are not
in the package: OpenAI refuses credentials in a ZIP, and both are entered in the dashboard.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import unicodedata
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "integrations" / "chatgpt-app"
sys.path.insert(0, str(ROOT / "src"))

PLUGIN_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MCP_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
CATEGORIES = ("Productivity", "Creativity", "Developer Tools", "Business & Operations", "Data & Analytics",
              "Communication", "Education & Research", "Security", "Finance", "Healthcare", "Travel", "Entertainment",
              "Other")
LISTING_URLS = ("websiteURL", "supportURL", "privacyPolicyURL", "termsOfServiceURL")
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".svg")
SCREENSHOT_WIDTH, SCREENSHOT_HEIGHTS = 706, (400, 860)
#: The files a package may hold: the two manifests and the assets they name. Anything else is refused, so nothing
#: private can ride along.
ALLOWED_TOP = ("plugin.json", "mcp.json")
FIXED_TIME = (1980, 1, 1, 0, 0, 0)


def _supported(text) -> bool:
    """OpenAI's supported text: no control characters except line breaks, no line or paragraph separators, no
    invisible formatting characters."""
    return isinstance(text, str) and not any(
        (unicodedata.category(character) in ("Cc", "Cf", "Zl", "Zp") and character not in "\n")
        for character in text)


def _one_line(text, maximum) -> bool:
    return (isinstance(text, str) and text.strip() == text and bool(text) and "\n" not in text
            and len(text) <= maximum and _supported(text))


def _https(value, maximum=1024) -> bool:
    from loop_engine.core.service_runtime.chatgpt_app import https_address
    return https_address(value, maximum) is not None


def service_mcp_url() -> str:
    """This service's protocol address on its canonical host name, as the site map and the transport name it."""
    from loop_engine.core.service_runtime.http import PROTOCOL_PATH
    from loop_engine.core.service_runtime.model_directory_pages import canonical
    from loop_engine.core.service_runtime.web_site_map import load_site_map
    return canonical(load_site_map(), PROTOCOL_PATH)


def _luminance(color):
    channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(first, second) -> float:
    high, low = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def image_size(path: Path):
    """(width, height, format) of a PNG, JPEG or WebP file, read from its header; None when it is none of them."""
    data = path.read_bytes()
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        width, height = struct.unpack(">II", data[16:24])
        return width, height, "png"
    if data[:2] == b"\xff\xd8":
        index = 2
        while index < len(data) - 9:
            if data[index] != 0xFF:
                return None
            marker, length = data[index + 1], struct.unpack(">H", data[index + 2:index + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2):
                height, width = struct.unpack(">HH", data[index + 5:index + 9])
                return width, height, "jpeg"
            index += 2 + length
        return None
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP" and data[12:16] == b"VP8X":
        width = int.from_bytes(data[24:27], "little") + 1
        height = int.from_bytes(data[27:30], "little") + 1
        return width, height, "webp"
    return None


def _asset(folder, value, name, problems, *, square=True):
    if not isinstance(value, str) or not value.startswith("./") or ".." in value.split("/") or value.strip() != value:
        problems.append(f"{name}: an asset path starts with ./ and stays inside the package")
        return None
    path = (folder / value[2:]).resolve()
    if folder.resolve() not in path.parents or not path.is_file():
        problems.append(f"{name}: {value} is not a file in the package")
        return None
    if path.suffix.lower() not in IMAGE_SUFFIXES:
        problems.append(f"{name}: {value} is not PNG, JPEG, WebP or SVG")
        return None
    if path.stat().st_size > 5 * 1024 * 1024:
        problems.append(f"{name}: {value} is larger than 5 MiB")
    if path.suffix.lower() == ".svg":
        text = path.read_text(encoding="utf-8")
        box = re.search(r'viewBox="\s*0\s+0\s+([0-9.]+)\s+([0-9.]+)\s*"', text)
        if not box or (square and box.group(1) != box.group(2)) or float(box.group(1)) < 48:
            problems.append(f"{name}: {value} needs a square viewBox of at least 48")
        return path
    size = image_size(path)
    if size is None or {".jpg": "jpeg", ".jpeg": "jpeg"}.get(path.suffix.lower(), path.suffix.lower()[1:]) != size[2]:
        problems.append(f"{name}: {value} is not the image its extension names")
        return None
    width, height, _ = size
    if square and (width != height or width < 48 or width > 4096):
        problems.append(f"{name}: {value} must be square, from 48 to 4096 pixels")
    return path


def _wording(texts, problems):
    """The website's public wording rules (tools/public_wording_rules.mjs) and the directory's own words."""
    from loop_engine.core.service_runtime import chatgpt_app
    script = ("import {internalTerms,retiredAccessWords,invitationWords,cardStatusWords} from './tools/public_wording_rules.mjs';"
              "let input='';process.stdin.on('data',d=>input+=d).on('end',()=>{const texts=JSON.parse(input);"
              "const rules=[internalTerms,retiredAccessWords,invitationWords,cardStatusWords];"
              "process.stdout.write(JSON.stringify(texts.flatMap(([n,t])=>rules.filter(r=>r.test(t)).map(r=>n+': '+String(r)))));});")
    answer = subprocess.run(["node", "--input-type=module", "-e", script], input=json.dumps(texts), cwd=ROOT,
                            capture_output=True, text=True, timeout=60)
    if answer.returncode != 0:
        problems.append("the public wording rules could not be read: " + answer.stderr[-200:])
    else:
        problems.extend("wording: " + row for row in json.loads(answer.stdout))
    for name, text in texts:
        found = chatgpt_app.DIRECTORY_REFUSED_WORDS.search(text)
        if found:
            problems.append(f"wording: {name} carries the directory word {found.group(0)!r}")
        if "—" in text or "–" in text:
            problems.append(f"wording: {name} carries a dash")


def check(folder: Path = PACKAGE) -> list:
    """Every reason the package at `folder` would fail OpenAI's final submission or the website's wording rules."""
    from loop_engine.core.service_runtime import chatgpt_app
    problems = []
    try:
        manifest = json.loads((folder / "plugin.json").read_text(encoding="utf-8"))
        servers = json.loads((folder / "mcp.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return [f"the manifests cannot be read: {error}"]
    if manifest.get("$schema") != PLUGIN_SCHEMA:
        problems.append("plugin.json names the Agent Plugins schema")
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?", manifest.get("name", "")) or "--" in manifest.get("name", ""):
        problems.append("name: lowercase letters, digits and single hyphens, at most 64 characters")
    if not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", manifest.get("version", "")):
        problems.append("version: a semantic version such as 1.0.0")
    if not isinstance(manifest.get("description"), str) or not 0 < len(manifest["description"]) <= 1024:
        problems.append("description: required, at most 1,024 characters")
    author = manifest.get("author") or {}
    if not _one_line(author.get("name"), 120) or ("url" in author and not _https(author["url"], 2048)):
        problems.append("author: a name of at most 120 characters and an HTTPS address")
    if "homepage" in manifest and not _https(manifest["homepage"], 2048):
        problems.append("homepage: an HTTPS address")
    openai = (manifest.get("extensions") or {}).get("com.openai")
    if not isinstance(openai, dict):
        return problems + ["extensions.com.openai is required"]
    if set(openai) - {"interface", "review", "publication", "onboardingSkill", "id"}:
        problems.append("extensions.com.openai holds only interface, review, publication, onboardingSkill and id")
    if "apps" in openai or "hooks" in openai or (folder / ".app.json").exists():
        problems.append("a submitted package holds no app references or lifecycle hooks")
    interface = openai.get("interface") or {}
    for name, limit in (("displayName", 30), ("shortDescription", 30), ("developerName", 80)):
        if not _one_line(interface.get(name), limit):
            problems.append(f"interface.{name}: required, one line, at most {limit} characters")
    long_text = interface.get("longDescription")
    if not isinstance(long_text, str) or not long_text.strip() or len(long_text) > 4000 or not _supported(long_text):
        problems.append("interface.longDescription: required, at most 4,000 characters")
    if interface.get("category") not in CATEGORIES:
        problems.append("interface.category: one of the directory's categories")
    capabilities = interface.get("capabilities", [])
    if not isinstance(capabilities, list) or len(capabilities) > 20 or not all(_one_line(row, 120) for row in capabilities):
        problems.append("interface.capabilities: at most 20, each one line of at most 120 characters")
    for name in LISTING_URLS:
        if not _https(interface.get(name)):
            problems.append(f"interface.{name}: required for a remote MCP submission, HTTPS, at most 1,024 characters")
    prompts = interface.get("defaultPrompt", [])
    prompts = [prompts] if isinstance(prompts, str) else prompts
    normalized = [" ".join(unicodedata.normalize("NFKC", row).split()).casefold() for row in prompts if isinstance(row, str)]
    if (not isinstance(prompts, list) or len(prompts) > 3 or not all(_one_line(row, 128) for row in prompts)
            or len(set(normalized)) != len(prompts) or any("@" in row for row in prompts)):
        problems.append("interface.defaultPrompt: at most three unique one-line prompts of at most 128 characters, no @mentions")
    for name, ground in (("brandColor", "#FFFFFF"), ("brandColorDark", "#212121")):
        if name in interface:
            value = interface[name]
            if not re.fullmatch(r"#[0-9A-Fa-f]{6}", value or ""):
                problems.append(f"interface.{name}: a six-digit hex colour")
            elif contrast(value, ground) < 2:
                problems.append(f"interface.{name}: at least 2:1 contrast against {ground}")
    _asset(folder, interface.get("logo"), "interface.logo", problems)
    _asset(folder, interface.get("composerIcon"), "interface.composerIcon", problems)
    for name in ("logoDark", "composerIconDark"):
        if name in interface:
            _asset(folder, interface[name], "interface." + name, problems)
    screenshots = interface.get("screenshots", [])
    if screenshots:
        if len(screenshots) != len(prompts):
            problems.append("interface.screenshots: one screenshot for every starter prompt")
        for value in screenshots:
            path = _asset(folder, value, "interface.screenshots", problems, square=False)
            size = image_size(path) if path is not None and path.suffix.lower() != ".svg" else None
            if size is None or size[2] not in ("png", "jpeg") or size[0] != SCREENSHOT_WIDTH \
                    or not SCREENSHOT_HEIGHTS[0] <= size[1] <= SCREENSHOT_HEIGHTS[1]:
                problems.append(f"interface.screenshots: {value} must be PNG or JPEG, 706 pixels wide and 400 to 860 tall")
    review = openai.get("review") or {}
    text_dump = json.dumps(manifest)
    if "test_credentials" in text_dump or "reviewer_instructions" in text_dump:
        problems.append("credentials and reviewer instructions are entered in the dashboard, never in the package")
    cases = review.get("test_cases") or {}
    positive, negative = cases.get("positive", []), cases.get("negative", [])
    if len(positive) != 5 or len(negative) != 3:
        problems.append("review.test_cases: exactly five positive and three negative cases")
    advertised = {tool.name for tool in chatgpt_app.TOOLS}
    for index, case in enumerate(positive):
        for field in ("description", "prompt", "tools_triggered", "expected_behavior"):
            if not isinstance(case.get(field), str) or not case[field].strip():
                problems.append(f"review.test_cases.positive[{index}].{field}: required")
        named = {part.strip() for part in str(case.get("tools_triggered", "")).split(",") if part.strip()}
        if named - advertised:
            problems.append(f"review.test_cases.positive[{index}]: names tools the server does not advertise: {sorted(named - advertised)}")
        if len(case.get("description", "")) > 4000:
            problems.append(f"review.test_cases.positive[{index}].description: at most 4,000 characters")
    for index, case in enumerate(negative):
        for field in ("description", "prompt"):
            if not isinstance(case.get(field), str) or not case[field].strip():
                problems.append(f"review.test_cases.negative[{index}].{field}: required")
    if "commerce" in review and type(review["commerce"]) is not bool:
        problems.append("review.commerce: true or false")
    if review.get("commerce") is not False:
        problems.append("review.commerce: Baltor sells nothing in ChatGPT (plugin guidelines, Commerce and monetization)")
    publication = openai.get("publication") or {}
    if "countries" in publication and (not isinstance(publication["countries"], list)
                                       or not all(re.fullmatch(r"[A-Z]{2}", row or "") for row in publication["countries"])):
        problems.append("publication.countries: uppercase two-letter country codes")
    if not isinstance(publication.get("release_notes"), str) or not publication["release_notes"].strip():
        problems.append("publication.release_notes: required for submission")
    if servers.get("$schema") != MCP_SCHEMA or not isinstance(servers.get("mcpServers"), dict):
        problems.append("mcp.json names the Agent Plugins MCP schema and its servers")
    else:
        entries = list(servers["mcpServers"].values())
        if len(entries) != 1 or entries[0] != {"type": "streamable-http", "url": service_mcp_url()}:
            problems.append(f"mcp.json: exactly one streamable-http server at {service_mcp_url()}")
    texts = [("interface." + name, interface.get(name) or "") for name in
             ("displayName", "shortDescription", "longDescription", "developerName")]
    texts += [("interface.capabilities", row) for row in capabilities if isinstance(row, str)]
    texts += [("interface.defaultPrompt", row) for row in prompts if isinstance(row, str)]
    texts += [("description", manifest.get("description") or "")]
    texts += [(f"review.{kind}[{index}]", case.get(field, "")) for kind, rows in (("positive", positive), ("negative", negative))
              for index, case in enumerate(rows) for field in ("description", "expected_behavior") if case.get(field)]
    texts += [("publication.release_notes", publication.get("release_notes") or "")]
    _wording(texts, problems)
    for path in folder.rglob("*"):
        relative = path.relative_to(folder).as_posix()
        if path.is_file() and relative not in ALLOWED_TOP and not relative.startswith("assets/") and relative != "README.md":
            problems.append(f"{relative}: the package holds only plugin.json, mcp.json, README.md and assets/")
    return problems


def entries(folder: Path = PACKAGE):
    """The archive's files, sorted: the manifests and every asset the manifest names. The README stays out."""
    manifest = json.loads((folder / "plugin.json").read_text(encoding="utf-8"))
    interface = manifest["extensions"]["com.openai"]["interface"]
    named = [interface[key] for key in ("logo", "composerIcon", "logoDark", "composerIconDark") if key in interface]
    named += list(interface.get("screenshots", []))
    return sorted({"plugin.json", "mcp.json", *(value[2:] for value in named)})


def build(output: Path, folder: Path = PACKAGE) -> str:
    """Write the deterministic archive and return its SHA-256."""
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in entries(folder):
            info = zipfile.ZipInfo(name, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, (folder / name).read_bytes())
    return hashlib.sha256(output.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="check the package and report every problem")
    parser.add_argument("--zip", type=Path, help="write the archive to a new path")
    arguments = parser.parse_args()
    problems = check()
    result = {"record_type": "chatgpt_app_package_check/v1", "package": str(PACKAGE.relative_to(ROOT)),
              "entries": entries(), "problems": problems, "all_passed": not problems}
    if arguments.zip and not problems:
        result["zip"] = str(arguments.zip)
        result["sha256"] = build(arguments.zip)
    print(json.dumps(result, indent=1))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
