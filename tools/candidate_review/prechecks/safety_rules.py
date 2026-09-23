"""Safety pre-check engine ``builtin_static_rules``: high-precision static rules that can only refuse.

Each rule names one shape of attack that has no place in a harness file a
customer loads unchanged. The rules are narrow on purpose: a false refusal
blocks a good item, so a rule is added only when it matches no body of the
real catalogue (a named check scans every committed body). Scanner output is
triage for the reviewers, never approval: passing these rules approves nothing.

Rules:

- ``hidden_character``: a bidirectional control, a zero-width character, a
  tag character or another invisible format character;
- ``control_character``: a control character other than a line break or a tab;
- ``hidden_comment``: an HTML comment, which a renderer hides from a person but
  a model reads;
- ``instruction_override``: text that tells the reader to ignore, disregard or
  forget earlier instructions, or to approve the item;
- ``pipe_to_shell``: a download piped straight into a shell;
- ``encoded_execution``: decoded or fetched text handed to a shell or ``eval``;
- ``destructive_command``: a recursive removal of the root or home folder, a
  file system format, or a raw write to a disk device;
- ``credential_access``: a read of a private key, a cloud credential file or
  the system password file.
"""
from __future__ import annotations

import re
import unicodedata

from ..records import refuse
from . import result_of

VERSION = "1"
INVISIBLE_RANGES = ((0x200B, 0x200F), (0x202A, 0x202E), (0x2060, 0x2064), (0x2066, 0x2069), (0xFEFF, 0xFEFF),
                    (0xE0000, 0xE007F))
ALLOWED_CONTROLS = ("\n", "\t")
RULES = (
    ("hidden_comment", re.compile(r"<!--")),
    ("instruction_override", re.compile(
        r"(?i)\b(?:ignore|disregard|forget|override)\b[^.\n]{0,40}\b(?:previous|prior|above|earlier|all|any)\b"
        r"[^.\n]{0,20}\b(?:instructions?|prompts?|rules?|guidelines?)\b")),
    ("instruction_override", re.compile(
        r"(?i)\b(?:approve this (?:item|skill|file)|mark (?:it|this) (?:as )?approved|you are now in)\b")),
    ("pipe_to_shell", re.compile(r"(?i)\b(?:curl|wget|fetch|iwr|invoke-webrequest)\b[^\n|]*\|\s*(?:sudo\s+)?"
                                 r"(?:ba|z|k|c|da|fi)?sh\b")),
    ("encoded_execution", re.compile(r"(?i)(?:base64\s+(?:-d|--decode)[^\n]*\|\s*(?:sudo\s+)?(?:ba|z)?sh\b"
                                     r"|\beval\s+[\"']?\$\((?:curl|wget)\b)")),
    ("destructive_command", re.compile(r"(?i)(?:\brm\s+-[a-z]*r[a-z]*\s+(?:/|~|\$HOME)(?:\s|$|\*)"
                                       r"|\bmkfs(?:\.[a-z0-9]+)?\s+/dev/|\bdd\s+if=[^\n]*\bof=/dev/(?:sd|nvme|hd))")),
    ("credential_access", re.compile(r"(?i)(?:~/\.ssh/|\bid_(?:rsa|ed25519|ecdsa)\b|\.aws/credentials\b"
                                     r"|\.netrc\b|/etc/shadow\b|\.docker/config\.json\b|\.kube/config\b)")),
)


def _invisible(character: str) -> bool:
    code = ord(character)
    return (any(low <= code <= high for low, high in INVISIBLE_RANGES)
            or (unicodedata.category(character) == "Cf" and character not in ALLOWED_CONTROLS))


class StaticSafetyRules:
    kind = "safety"
    engine_id = "builtin_static_rules"

    def __init__(self, settings: dict, policy) -> None:
        if settings:
            refuse("invalid_precheck_settings", "builtin_static_rules takes no settings")

    def availability(self):
        return True, "", VERSION

    def check(self, request, context):
        text = request.body_text_lenient
        purpose = str(request.item.get("reference", {}).get("purpose", ""))
        findings, seen = [], set()
        for place, value in (("body", text), ("purpose", purpose)):
            hidden = sorted({f"U+{ord(character):04X}" for character in value if _invisible(character)})
            if hidden:
                findings.append(("hidden_character", f"the {place} holds invisible characters {hidden[:8]}"))
            controls = sorted({f"U+{ord(character):04X}" for character in value
                               if unicodedata.category(character) == "Cc" and character not in ALLOWED_CONTROLS})
            if controls:
                findings.append(("control_character", f"the {place} holds control characters {controls[:8]}"))
            for code, pattern in RULES:
                match = pattern.search(value)
                if match and (code, place) not in seen:
                    seen.add((code, place))
                    line = value.count("\n", 0, match.start()) + 1
                    findings.append((code, f"the {place} matches the {code} rule on line {line}"))
        return result_of(self.kind, self.engine_id, VERSION, findings)
