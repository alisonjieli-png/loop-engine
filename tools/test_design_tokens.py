"""The website's colour tokens hold the orange design's values, readable text and a fallback for every browser.

Kind: development check over one packaged file, `web_assets/service.css`. It starts no server and opens no
connection.

On September 26, 2026 the owner asked for the orange design of his archive (the ember primary on warm neutrals,
oklch(0.55 0.18 42)) with "a hex fallback for browsers without oklch" and text contrast of at least 4.5 to 1. The
token block at the top of service.css writes every colour twice: a hex value that every browser reads, then the
design's oklch value inside `@supports (color:oklch(0 0 0))`. Each rule below refuses one way to lose that:

- a colour token whose hex fallback is not the sRGB colour of its oklch value (brought into gamut by lowering the
  chroma, as the tokens were written), so the two kinds of browser would show different colours;
- a token that the light theme defines and the dark theme does not, or the reverse, so one theme would fall back
  to the other theme's colour;
- a system dark block that differs from the chosen dark block, so "system" and "dark" would disagree;
- a text colour below 4.5 to 1, or a field edge below 3 to 1, on the ground it is used on, in either theme.

Every rule has a known-wrong token set beside it and a removed-rule control that must fail its named check.

    PYTHONPATH=src:tools python -m unittest tools/test_design_tokens.py
"""
from __future__ import annotations

import math
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
STYLESHEET = ROOT / "src/loop_engine/core/service_runtime/web_assets/service.css"
#: A channel may differ by this much between the written hex value and the computed one, for rounding.
CHANNEL_TOLERANCE = 2
TEXT_CONTRAST = 4.5
EDGE_CONTRAST = 3.0
#: Text tokens and the grounds each is written on, in both themes.
TEXT_PAIRS = (
    ("ink", ("bg", "paper", "band", "soft", "tint")), ("muted", ("bg", "paper", "band", "soft", "tint")),
    ("subtle", ("bg", "paper", "band")), ("accent", ("bg", "paper", "band", "soft")),
    ("button-ink", ("button", "button-hover")), ("ink-button-ink", ("ink-button", "ink-button-hover")),
    ("verified-ink", ("verified-bg",)), ("community-ink", ("community-bg",)), ("ok", ("ok-soft", "paper")),
    ("info", ("info-soft",)), ("planned", ("planned-soft",)), ("warn", ("warn-soft",)), ("error", ("paper", "bg")),
    ("night-ink", ("night", "night-card")), ("night-muted", ("night",)), ("night-accent", ("night",)),
    ("night-button-ink", ("night-button", "night-button-hover")), ("code-ink", ("code-bg",)),
)
EDGE_PAIRS = (("field-edge", ("paper", "bg")),)
_BLOCK = re.compile(r"(:root(?:\[data-theme=dark\]|:not\(\[data-theme\]\))?)\{([^{}]*)\}")
_OKLCH = re.compile(r"^oklch\(([0-9.]+) ([0-9.]+) ([0-9.]+)\)$")
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _srgb(lightness, chroma, hue):
    a, b = chroma * math.cos(math.radians(hue)), chroma * math.sin(math.radians(hue))
    l_ = (lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (lightness - 0.0894841775 * a - 1.2914855480 * b) ** 3
    linear = (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
              -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
              -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)
    return linear, all(-1e-4 <= value <= 1 + 1e-4 for value in linear)


def oklch_hex(lightness, chroma, hue):
    """The sRGB hex colour of an oklch value, its chroma lowered until it fits the sRGB gamut."""
    linear, inside = _srgb(lightness, chroma, hue)
    if not inside:
        low, high = 0.0, chroma
        for _ in range(40):
            middle = (low + high) / 2
            if _srgb(lightness, middle, hue)[1]:
                low = middle
            else:
                high = middle
        linear = _srgb(lightness, low, hue)[0]
    encode = lambda value: 12.92 * value if value <= 0.0031308 else 1.055 * value ** (1 / 2.4) - 0.055
    return "#" + "".join(f"{round(min(1, max(0, encode(value))) * 255):02X}" for value in linear)


def contrast(first, second):
    def luminance(colour):
        values = [int(colour[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        values = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in values]
        return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2]
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _declarations(body):
    found = {}
    for part in body.split(";"):
        name, _, value = part.partition(":")
        if name.strip().startswith("--"):
            found[name.strip()[2:]] = value.strip()
    return found


def token_sets(css):
    """The four colour token sets of the stylesheet: hex light and dark, oklch light and dark, and the system dark set."""
    supports = css.index("@supports (color:oklch(0 0 0))")
    sets = {"hex": {}, "oklch": {}, "system": {}}
    for match in _BLOCK.finditer(css):
        selector, values = match.group(1), _declarations(match.group(2))
        kind = "oklch" if match.start() > supports else "hex"
        if selector == ":root:not([data-theme])":
            if kind == "hex":
                sets["system"] = values
            continue
        sets[kind]["dark" if "dark" in selector else "light"] = sets[kind].get(
            "dark" if "dark" in selector else "light", {}) | values
    return sets


def colours(values):
    return {name: value for name, value in values.items() if _HEX.match(value) or _OKLCH.match(value) or value.startswith("oklch(")}


def fallbacks_match(sets):
    problems = []
    for theme in ("light", "dark"):
        hexes, oklchs = sets["hex"].get(theme, {}), sets["oklch"].get(theme, {})
        for name, value in colours(oklchs).items():
            match = _OKLCH.match(value)
            if not match:
                continue
            written = hexes.get(name, "")
            if not _HEX.match(written):
                problems.append(f"{theme} --{name}: no hex fallback for {value}")
                continue
            wanted = oklch_hex(*(float(part) for part in match.groups()))
            drift = max(abs(int(written[index:index + 2], 16) - int(wanted[index:index + 2], 16)) for index in (1, 3, 5))
            if drift > CHANNEL_TOLERANCE:
                problems.append(f"{theme} --{name}: hex {written} is not {value}, which is {wanted}")
    return problems


def themes_match(sets):
    problems = []
    light, dark = set(colours(sets["hex"].get("light", {}))), set(colours(sets["hex"].get("dark", {})))
    problems.extend(f"--{name} is light only" for name in sorted(light - dark))
    problems.extend(f"--{name} is dark only" for name in sorted(dark - light))
    if sets["system"] != sets["hex"].get("dark"):
        problems.append("the system dark block differs from the chosen dark block")
    return problems


def text_is_readable(sets):
    problems = []
    for kind in ("hex", "oklch"):
        for theme, values in sets[kind].items():
            def colour(name):
                value = values.get(name, "")
                match = _OKLCH.match(value)
                return oklch_hex(*(float(part) for part in match.groups())) if match else (
                    "#FFFFFF" if value == "oklch(1 0 0)" else value)
            for pairs, floor in ((TEXT_PAIRS, TEXT_CONTRAST), (EDGE_PAIRS, EDGE_CONTRAST)):
                for text, grounds in pairs:
                    for ground in grounds:
                        first, second = colour(text), colour(ground)
                        if not (_HEX.match(first) and _HEX.match(second)):
                            problems.append(f"{kind} {theme}: --{text} or --{ground} is missing")
                        elif contrast(first, second) < floor:
                            problems.append(f"{kind} {theme}: --{text} on --{ground} is {contrast(first, second):.2f} to 1")
    return problems


RULES = {"fallbacks_match": fallbacks_match, "themes_match": themes_match, "text_is_readable": text_is_readable}


def _changed(css, find, replacement, count=1):
    assert css.count(find) >= count, find
    return css.replace(find, replacement, count)


def known_wrong(css):
    """Known-wrong stylesheets, each refused by one named rule."""
    return {
        "fallbacks_match": (
            ("the ember fallback drifts from its oklch value", _changed(css, "--accent:#BD4600", "--accent:#2E5BFF")),
            ("a token loses its hex fallback", _changed(css, "--accent:#BD4600;", ""))),
        "themes_match": (
            ("a dark theme without the ember", _changed(css, ":root[data-theme=dark]{color-scheme:dark;--bg:", ":root[data-theme=dark]{color-scheme:dark;--x:#000000;--bg:")),
            ("the system dark block drifts", _changed(css, "@media(prefers-color-scheme:dark){:root:not([data-theme]){color-scheme:dark;--bg:#16100D",
                                                       "@media(prefers-color-scheme:dark){:root:not([data-theme]){color-scheme:dark;--bg:#000000"))),
        "text_is_readable": (
            ("grey 8a8a8a text on white", _changed(css, "--muted:#544B45", "--muted:#8A8A8A")),
            # The same light ember in both notations, so only the contrast rule can refuse it.
            ("an ember too light to read, written the same in both notations", _changed(_changed(
                css, "--accent:#BD4600", "--accent:" + oklch_hex(0.7, 0.18, 42)),
                "--accent:oklch(0.55 0.18 42)", "--accent:oklch(0.7 0.18 42)"))),
    }


class DesignTokens(unittest.TestCase):
    def setUp(self):
        self.css = STYLESHEET.read_text(encoding="utf-8")

    def test_the_served_tokens_pass_every_rule(self):
        sets = token_sets(self.css)
        self.assertTrue(sets["hex"].get("light") and sets["oklch"].get("dark"), "the stylesheet holds no token blocks")
        self.assertEqual(sets["oklch"]["light"]["button"], "oklch(0.55 0.18 42)", "the ember primary is the design's")
        for name, rule in RULES.items():
            with self.subTest(rule=name):
                self.assertEqual(rule(sets), [])

    def test_every_rule_refuses_its_known_wrong_tokens(self):
        for name, cases in known_wrong(self.css).items():
            for label, css in cases:
                with self.subTest(rule=name, case=label):
                    self.assertTrue(RULES[name](token_sets(css)), f"{name} accepted: {label}")

    def test_a_removed_rule_fails_its_named_check(self):
        """Without one rule, the other rules let at least one of its known-wrong token sets through."""
        for name, cases in known_wrong(self.css).items():
            others = [rule for other, rule in RULES.items() if other != name]
            passed = [label for label, css in cases if not any(rule(token_sets(css)) for rule in others)]
            with self.subTest(rule=name):
                self.assertTrue(passed, f"{name} refuses nothing that the other rules do not already refuse")

if __name__ == "__main__":
    unittest.main()
