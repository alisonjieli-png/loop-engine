"""Text conformance operations: deterministic normalizers with a confidence per correction.

This module is self-contained on purpose. It imports only the standard
library and works on plain dictionaries, so an exported standalone solution
can ship it verbatim and run without Loop Engine. The typed Loop Engine
layer around it is ``loop_engine.code_nodes.text_conformance``.

Every operation returns one correction: the proposed output, a confidence
between 0 and 1, and the named reasons that produced that confidence. The
confidence is not a guess. It is the weakest of the named signals, so a
caller can read exactly why a value was applied, held, or escalated.

Exceptions come from catalogs, plain mappings of lists and dictionaries. The
catalogs may be layered from the packaged file, a task folder, evidence
learned from the column itself, inline rule parameters, or recorded
escalation answers. This module reads whatever merged catalog it is given.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

OPERATIONS = ("whitespace_normalize", "unicode_normalize", "case_normalize",
              "suffix_canonicalize", "phone_normalize", "email_normalize",
              "website_normalize")
OUTCOMES = ("applied", "held", "escalated", "unchanged")
CATALOG_KINDS = ("null_sentinels", "preserved_tokens", "minor_words",
                 "lowercase_particles", "internal_capital_prefixes",
                 "apostrophe_prefixes", "surname_exceptions", "legal_suffixes",
                 "ambiguous_suffixes", "suffix_long_forms", "ascii_fold_map")
SUFFIX_STYLES = ("short_no_period", "short_with_period", "long_form")
ASCII_FOLD_MODES = ("never", "hold", "apply")
DEFAULT_APPLY_AT_OR_ABOVE = 0.9
DEFAULT_ESCALATE_BELOW = 0.6

_SPACE_CHARACTERS = "             \t\r\n\f\v"
_ZERO_WIDTH = "​‌‍﻿⁠"
_QUOTE_MAP = {"‘": "'", "’": "'", "‚": "'", "“": '"',
              "”": '"', "„": '"', "′": "'", "″": '"'}
_EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
_HOST_LABEL = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")
_VOWELS = set("aeiouy")


def correction(output: str, confidence: float, reasons, changed: bool) -> dict:
    """One correction as plain data."""
    return {"output": output, "confidence": round(max(0.0, min(1.0, confidence)), 3),
            "reasons": list(reasons), "changed": bool(changed)}


def _combine(base: float, factors, ambiguous: int) -> float:
    value = min([base, *factors]) if factors else base
    if ambiguous > 1:
        value -= 0.02 * min(ambiguous - 1, 5)
    return value


def is_null_sentinel(value: str, catalogs: dict) -> bool:
    sentinels = {str(item).strip().lower() for item in catalogs.get("null_sentinels", ())}
    return value.strip().lower() in sentinels


# ---------------------------------------------------------------------------
# Whitespace and Unicode
# ---------------------------------------------------------------------------

def whitespace_normalize(value: str, parameters: dict | None = None) -> dict:
    """Trim, replace nonstandard spaces, and collapse internal runs. Lossless."""
    reasons = []
    text = value
    if any(ch in _SPACE_CHARACTERS for ch in text):
        reasons.append("nonstandard_space_character")
        text = "".join(" " if ch in _SPACE_CHARACTERS else ch for ch in text)
    if text != text.strip():
        reasons.append("leading_or_trailing_whitespace")
        text = text.strip()
    if "  " in text:
        reasons.append("internal_whitespace_run")
        text = re.sub(r" {2,}", " ", text)
    return correction(text, 0.99 if reasons else 1.0, reasons, text != value)


def unicode_normalize(value: str, parameters: dict | None = None,
                      catalogs: dict | None = None) -> dict:
    """NFC composition, zero-width removal, quote straightening, optional folding.

    ``ascii_fold`` is ``never`` (default), ``hold`` (propose a folded form at
    low confidence so the policy holds or escalates it), or ``apply``
    (the owner chose folding, so the folded form is confident).
    """
    parameters = parameters or {}
    catalogs = catalogs or {}
    reasons = []
    factors = []
    text = unicodedata.normalize("NFC", value)
    if text != value:
        reasons.append("unicode_nfc_composed")
        factors.append(0.99)
    if any(ch in _ZERO_WIDTH for ch in text):
        reasons.append("zero_width_character_removed")
        factors.append(0.98)
        text = "".join(ch for ch in text if ch not in _ZERO_WIDTH)
    if parameters.get("straighten_quotes", True) and any(ch in _QUOTE_MAP for ch in text):
        reasons.append("typographic_quote_straightened")
        factors.append(0.95)
        text = "".join(_QUOTE_MAP.get(ch, ch) for ch in text)
    mode = parameters.get("ascii_fold", ASCII_FOLD_MODES[0])
    if mode not in ASCII_FOLD_MODES:
        raise ValueError(f"ascii_fold must be one of {ASCII_FOLD_MODES}")
    if any(ord(ch) > 127 for ch in text):
        if mode == ASCII_FOLD_MODES[0]:
            reasons.append("non_ascii_retained")
        else:
            folded = ascii_fold(text, catalogs.get("ascii_fold_map") or {})
            if folded != text:
                reasons.append("ascii_folded_lossy")
                factors.append(0.5 if mode == ASCII_FOLD_MODES[1] else 0.9)
                text = folded
            else:
                reasons.append("non_ascii_without_fold_rule")
    return correction(text, _combine(1.0, factors, 0), reasons, text != value)


def ascii_fold(text: str, fold_map: dict) -> str:
    """Fold letters to ASCII through the catalog map, then by stripping marks."""
    out = []
    for ch in text:
        if ord(ch) <= 127:
            out.append(ch)
            continue
        mapped = fold_map.get(ch)
        if mapped is not None:
            out.append(mapped)
            continue
        stripped = "".join(c for c in unicodedata.normalize("NFKD", ch)
                           if not unicodedata.combining(c))
        out.append(stripped if stripped and all(ord(c) <= 127 for c in stripped) else ch)
    return "".join(out)


# ---------------------------------------------------------------------------
# Case
# ---------------------------------------------------------------------------

def _split_core(token: str) -> tuple[str, str, str]:
    """Leading punctuation, the letter core, trailing punctuation."""
    match = re.match(r"^([^\w]*)(.*?)([^\w]*)$", token, re.UNICODE)
    return match.group(1), match.group(2), match.group(3)


def _capitalize(core: str) -> str:
    return core[:1].upper() + core[1:].lower()


def _case_part(part: str, position: str, case_absent: bool, catalogs: dict,
               evidence: dict | None) -> tuple[str, float, str, bool]:
    """Case one hyphen-free part. Returns (text, factor, reason, ambiguous)."""
    lead, core, trail = _split_core(part)
    if not core:
        return part, 1.0, "", False
    lowered = core.lower()
    if any(ch.isdigit() for ch in core):
        return part, 0.9 if case_absent else 1.0, "token_with_digits_kept", False
    exact = (catalogs.get("surname_exceptions") or {}).get(lowered)
    if exact:
        return lead + exact + trail, 0.98, f"surname_exception:{exact}", False
    learned = (evidence or {}).get(lowered)
    if learned:
        return lead + learned["form"] + trail, 0.95, f"column_evidence:{learned['form']}", False
    suffix = (catalogs.get("legal_suffixes") or {}).get(lowered)
    if suffix and position != "first" and lowered not in (catalogs.get("ambiguous_suffixes") or {}):
        # Case the token like its canonical form; never shorten it here. An
        # ambiguous suffix falls through so the suffix operation decides it.
        cased = suffix if len(suffix) == len(core) else _capitalize(core)
        return lead + cased + trail, 0.95, f"legal_suffix_cased:{cased}", False
    if core.upper() in set(catalogs.get("preserved_tokens") or ()):
        return lead + core.upper() + trail, 0.97, "preserved_token", False
    if not case_absent and len(core) >= 2 and core.isupper():
        return part, 0.97, "existing_uppercase_kept", False
    if not case_absent and core[0].isupper() and any(ch.isupper() for ch in core[1:]) \
            and not core.isupper():
        return part, 0.98, "existing_internal_capital_kept", False
    if len(core) == 1:
        return lead + core.upper() + trail, 0.95, "single_letter_upper", False
    if "'" in core:
        prefix, rest = core.split("'", 1)
        if prefix.upper() in set(catalogs.get("apostrophe_prefixes") or ()) and len(prefix) == 1:
            return lead + prefix.upper() + "'" + _capitalize(rest) + trail, 0.93, "apostrophe_prefix_capital", False
        return lead + _capitalize(prefix) + "'" + rest.lower() + trail, 0.9, "apostrophe_kept_lower", False
    particles = set(catalogs.get("lowercase_particles") or ())
    minor = set(catalogs.get("minor_words") or ())
    if position == "first" and (lowered in particles or lowered in minor):
        return lead + _capitalize(core) + trail, 0.95, "leading_particle_capitalized", False
    if lowered in particles and position != "first":
        factor = float(catalogs.get("particle_confidence", 0.8))
        return lead + lowered + trail, factor, "particle_lowercased_ambiguous", True
    if lowered in minor and position == "inner":
        return lead + lowered + trail, 0.95, "minor_word_lowercased", False
    for prefix, factor in sorted((catalogs.get("internal_capital_prefixes") or {}).items(),
                                 key=lambda item: -len(item[0])):
        size = len(prefix)
        if lowered.startswith(prefix.lower()) and len(core) > size + 1 and core[size].isalpha():
            text = lead + prefix + _capitalize(core[size:]) + trail
            return text, float(factor), f"prefix_capital:{prefix}", float(factor) < 0.9
    if case_absent and lowered.isalpha() and not (set(lowered) & _VOWELS):
        return lead + core.upper() + trail, 0.9, "no_vowel_token_kept_upper", False
    if case_absent and len(core) <= 2:
        factor = float(catalogs.get("short_token_confidence", 0.75))
        return lead + core.upper() + trail, factor, "short_token_kept_upper_unverified", True
    if case_absent and len(core) == 3:
        factor = float(catalogs.get("short_word_confidence", 0.85))
        return lead + _capitalize(core) + trail, factor, "short_word_capitalized_unverified", True
    changed = _capitalize(core) != core
    return lead + _capitalize(core) + trail, (0.97 if case_absent else 0.95) if changed else 1.0, \
        ("first_letter_capitalized" if changed else ""), False


def case_normalize(value: str, parameters: dict | None = None,
                   catalogs: dict | None = None, evidence: dict | None = None) -> dict:
    """Title case with catalog and evidence exceptions.

    Case information present in the input (mixed case) is preserved and only
    first letters are checked. All-upper or all-lower input carries no case
    information, so every token is decided from catalogs, column evidence,
    and named heuristics, and the confidence reports each ambiguity.
    """
    catalogs = catalogs or {}
    letters = [ch for ch in value if ch.isalpha()]
    if not letters or is_null_sentinel(value, catalogs):
        return correction(value, 1.0, ["no_letters_or_null_sentinel"], False)
    case_absent = all(ch.isupper() for ch in letters) or all(ch.islower() for ch in letters)
    base = (float(catalogs.get("case_absent_confidence", 0.92)) if case_absent
            else float(catalogs.get("case_present_confidence", 0.95)))
    tokens = value.split(" ")
    out_tokens, factors, reasons = [], [], []
    ambiguous = 0
    last = len(tokens) - 1
    for index, token in enumerate(tokens):
        position = "first" if index == 0 else ("last" if index == last else "inner")
        parts = token.split("-")
        cased = []
        for part_index, part in enumerate(parts):
            text, factor, reason, is_ambiguous = _case_part(
                part, position if part_index == 0 else "inner", case_absent, catalogs, evidence)
            cased.append(text)
            if factor < 1.0:
                factors.append(factor)
            if reason and reason not in reasons:
                reasons.append(reason)
            ambiguous += int(is_ambiguous)
        out_tokens.append("-".join(cased))
    text = " ".join(out_tokens)
    if case_absent:
        reasons.insert(0, "case_information_absent")
    confidence = _combine(base, factors, ambiguous) if text != value else 1.0
    return correction(text, confidence, reasons, text != value)


# ---------------------------------------------------------------------------
# Legal suffixes
# ---------------------------------------------------------------------------

def _suffix_key(token: str) -> str:
    return re.sub(r"[.,;]", "", token).lower()


def _styled_suffix(canonical: str, style: str, catalogs: dict) -> str:
    if style == SUFFIX_STYLES[1]:
        return canonical if canonical.isupper() else canonical + "."
    if style == SUFFIX_STYLES[2]:
        return (catalogs.get("suffix_long_forms") or {}).get(canonical, canonical)
    return canonical


def suffix_canonicalize(value: str, parameters: dict | None = None,
                        catalogs: dict | None = None) -> dict:
    """Canonicalize up to two trailing legal suffix tokens and the comma before them."""
    parameters = parameters or {}
    catalogs = catalogs or {}
    style = parameters.get("style", SUFFIX_STYLES[0])
    comma = parameters.get("comma_before_suffix", "remove")
    if style not in SUFFIX_STYLES:
        raise ValueError(f"style must be one of {SUFFIX_STYLES}")
    if comma not in ("remove", "keep", "add"):
        raise ValueError("comma_before_suffix must be remove, keep, or add")
    if is_null_sentinel(value, catalogs):
        return correction(value, 1.0, ["null_sentinel"], False)
    suffixes = catalogs.get("legal_suffixes") or {}
    ambiguous = catalogs.get("ambiguous_suffixes") or {}
    tokens = value.split(" ")
    reasons, factors = [], []
    index = len(tokens) - 1
    handled = 0
    while index >= 1 and handled < 2:
        key = _suffix_key(tokens[index])
        canonical = suffixes.get(key)
        if canonical is None:
            break
        styled = _styled_suffix(canonical, style, catalogs)
        if styled != tokens[index]:
            reasons.append(f"suffix_canonicalized:{canonical}")
        if key in ambiguous:
            reasons.append(f"ambiguous_suffix:{key}")
            factors.append(float(ambiguous[key]))
        else:
            factors.append(0.97)
        tokens[index] = styled
        previous = tokens[index - 1]
        if previous.endswith(",") and comma == "remove":
            tokens[index - 1] = previous.rstrip(",")
            reasons.append("comma_before_suffix_removed")
        elif not previous.endswith(",") and comma == "add":
            tokens[index - 1] = previous + ","
            reasons.append("comma_before_suffix_added")
        handled += 1
        index -= 1
    if handled == 0:
        return correction(value, 1.0, ["no_legal_suffix"], False)
    text = " ".join(tokens)
    return correction(text, _combine(1.0, factors, 0) if text != value else 1.0, reasons, text != value)


# ---------------------------------------------------------------------------
# Phones, emails, websites
# ---------------------------------------------------------------------------

def phone_normalize(value: str, parameters: dict | None = None,
                    catalogs: dict | None = None) -> dict:
    """Digits to an international form when the digit count is explainable."""
    parameters = parameters or {}
    catalogs = catalogs or {}
    if is_null_sentinel(value, catalogs):
        return correction(value, 1.0, ["null_sentinel"], False)
    country = str(parameters.get("default_country_code", "")).strip("+ ")
    national = int(parameters.get("national_number_length", 10))
    keep_extension = bool(parameters.get("keep_extension", True))
    text = value.strip()
    extension = ""
    match = re.search(r"(?:ext\.?|extension|x)\s*(\d{1,6})\s*$", text, re.IGNORECASE)
    if match:
        extension = match.group(1)
        text = text[:match.start()].strip()
    international = text.startswith("+")
    digits = re.sub(r"\D", "", text)
    reasons = [f"extension:{extension}"] if extension else []
    if international and 8 <= len(digits) <= 15:
        output, confidence = "+" + digits, 0.93
        reasons.append("international_prefix_kept")
    elif country and len(digits) == national:
        output, confidence = "+" + country + digits, 0.95
        reasons.append("default_country_code_applied")
    elif country and digits.startswith(country) and len(digits) == len(country) + national:
        output, confidence = "+" + digits, 0.95
        reasons.append("country_code_present")
    elif not country and len(digits) == national:
        output, confidence = digits, 0.7
        reasons.append("no_default_country_code")
    else:
        reasons.append(f"digit_count_unexpected:{len(digits)}")
        return correction(value, 0.35, reasons, False)
    if extension and keep_extension:
        output += " ext " + extension
    return correction(output, confidence if output != value else 1.0, reasons, output != value)


def email_normalize(value: str, parameters: dict | None = None,
                    catalogs: dict | None = None) -> dict:
    """Strip wrappers, lowercase, and check the shape of one address."""
    parameters = parameters or {}
    catalogs = catalogs or {}
    if is_null_sentinel(value, catalogs):
        return correction(value, 1.0, ["null_sentinel"], False)
    text = value.strip()
    reasons = []
    if text.lower().startswith("mailto:"):
        text = text[7:]
        reasons.append("mailto_prefix_removed")
    if text.startswith("<") and text.endswith(">"):
        text = text[1:-1]
        reasons.append("angle_brackets_removed")
    if text.count("@") > 1 or any(sep in text for sep in (";", ",")) or " " in text:
        reasons.append("multiple_values_or_spaces")
        return correction(value, 0.5, reasons, False)
    local, _, domain = text.rpartition("@")
    if parameters.get("lowercase_local_part", True):
        local = local.lower()
    text = local + "@" + domain.lower()
    if not _EMAIL.match(text):
        reasons.append("invalid_email_shape")
        return correction(value, 0.3, reasons, False)
    if text != value:
        reasons.append("email_normalized")
    return correction(text, 0.97 if text != value else 1.0, reasons, text != value)


_URL = re.compile(r"^(?P<scheme>[A-Za-z][A-Za-z0-9+.-]*)://(?P<authority>[^/?#]*)"
                  r"(?P<path>[^?#]*)(?P<query>\?[^#]*)?(?P<fragment>#.*)?$")


def _split_url(text: str) -> dict:
    """Scheme, lowercase host, port, path, query, and fragment of one URL text."""
    match = _URL.match(text)
    if match is None:
        return {"scheme": "", "host": "", "port": "", "path": "", "query": "", "fragment": ""}
    authority = match.group("authority")
    if "@" in authority:
        authority = authority.rsplit("@", 1)[1]
    host, _, port = authority.partition(":")
    return {"scheme": match.group("scheme"), "host": host.lower(),
            "port": port if port.isdigit() else "", "path": match.group("path") or "",
            "query": match.group("query") or "", "fragment": match.group("fragment") or ""}


def website_normalize(value: str, parameters: dict | None = None,
                      catalogs: dict | None = None) -> dict:
    """Scheme, host case, optional www and trailing slash; the path keeps its case."""
    parameters = parameters or {}
    catalogs = catalogs or {}
    if is_null_sentinel(value, catalogs):
        return correction(value, 1.0, ["null_sentinel"], False)
    text = value.strip()
    reasons, factors = [], []
    if " " in text:
        return correction(value, 0.3, ["whitespace_inside_url"], False)
    if "://" not in text:
        text = str(parameters.get("default_scheme", "https")) + "://" + text
        reasons.append("scheme_added")
        factors.append(0.9)
    parts = _split_url(text)
    host = parts["host"]
    if parameters.get("strip_www", False) and host.startswith("www."):
        host = host[4:]
        reasons.append("www_removed")
    labels = host.split(".")
    if len(labels) < 2 or not all(_HOST_LABEL.match(label) for label in labels) \
            or not labels[-1].isalpha():
        return correction(value, 0.3, [*reasons, "invalid_host"], False)
    netloc = host + (f":{parts['port']}" if parts["port"] else "")
    path = parts["path"]
    if parameters.get("strip_trailing_slash", True) and path.endswith("/") and len(path) > 1:
        path = path.rstrip("/")
        reasons.append("trailing_slash_removed")
    if path == "/":
        path = ""
        reasons.append("trailing_slash_removed")
    rebuilt = parts["scheme"].lower() + "://" + netloc + path + parts["query"] + parts["fragment"]
    if rebuilt != value and "scheme_added" not in reasons:
        reasons.append("host_or_scheme_case_normalized")
    return correction(rebuilt, _combine(0.95, factors, 0) if rebuilt != value else 1.0,
                      reasons, rebuilt != value)


# ---------------------------------------------------------------------------
# Rule application, thresholds, and row streaming
# ---------------------------------------------------------------------------

_DISPATCH = {
    "whitespace_normalize": lambda value, parameters, catalogs, evidence: whitespace_normalize(value, parameters),
    "unicode_normalize": lambda value, parameters, catalogs, evidence: unicode_normalize(value, parameters, catalogs),
    "case_normalize": case_normalize,
    "suffix_canonicalize": lambda value, parameters, catalogs, evidence: suffix_canonicalize(value, parameters, catalogs),
    "phone_normalize": lambda value, parameters, catalogs, evidence: phone_normalize(value, parameters, catalogs),
    "email_normalize": lambda value, parameters, catalogs, evidence: email_normalize(value, parameters, catalogs),
    "website_normalize": lambda value, parameters, catalogs, evidence: website_normalize(value, parameters, catalogs),
}


def apply_operation(operation: str, value: str, parameters: dict | None,
                    catalogs: dict | None, evidence: dict | None = None) -> dict:
    if operation not in _DISPATCH:
        raise ValueError(f"operation must be one of {OPERATIONS}")
    return _DISPATCH[operation](value, parameters or {}, catalogs or {}, evidence)


def classify(confidence: float, changed: bool, apply_at_or_above: float,
             escalate_below: float) -> str:
    """The outcome of one correction under the thresholds."""
    if not changed and confidence >= escalate_below:
        return OUTCOMES[3]
    if confidence >= apply_at_or_above and changed:
        return OUTCOMES[0]
    if confidence < escalate_below:
        return OUTCOMES[2]
    return OUTCOMES[1]


def apply_rules_to_row(row: dict, rules, catalogs: dict, policy: dict | None = None,
                       column_evidence: dict | None = None) -> tuple[dict, list]:
    """Apply ordered rules to one row. Returns the output row and its corrections.

    A correction is applied to the output row only when its outcome is
    ``applied``; held and escalated corrections keep the input value in the
    row and carry the candidate in the correction record.
    """
    policy = policy or {}
    output = dict(row)
    corrections = []
    for rule in rules:
        apply_at = float(rule.get("apply_at_or_above")
                         or policy.get("apply_at_or_above", DEFAULT_APPLY_AT_OR_ABOVE))
        escalate = float(rule.get("escalate_below")
                         or policy.get("escalate_below", DEFAULT_ESCALATE_BELOW))
        for column in rule.get("columns") or ():
            if column not in output or output[column] is None:
                continue
            value = str(output[column])
            evidence = (column_evidence or {}).get(column)
            result = apply_operation(rule["operation"], value, rule.get("parameters"),
                                     catalogs, evidence)
            outcome = classify(result["confidence"], result["changed"], apply_at, escalate)
            if outcome == OUTCOMES[0]:
                output[column] = result["output"]
            if outcome == OUTCOMES[3] and not result["changed"] and result["confidence"] >= apply_at:
                continue
            corrections.append({"column": column, "rule_id": rule["rule_id"],
                                "operation": rule["operation"], "input": value,
                                "output": result["output"],
                                "confidence": result["confidence"],
                                "reasons": result["reasons"], "outcome": outcome})
    return output, corrections


def learn_column_evidence(rows, columns, *, min_count: int = 2,
                          min_share: float = 0.8) -> dict:
    """Token casings the column itself proves through its mixed-case values.

    Only values that carry case information vote. A token whose dominant
    exact form reaches ``min_share`` of at least ``min_count`` votes becomes
    evidence, so an all-caps row can inherit the casing its neighbors show.
    """
    votes: dict = {column: {} for column in columns}
    for row in rows:
        for column in columns:
            value = str(row.get(column) or "")
            letters = [ch for ch in value if ch.isalpha()]
            if not letters or all(ch.isupper() for ch in letters) or all(ch.islower() for ch in letters):
                continue
            for token in value.split(" "):
                _, core, _ = _split_core(token)
                if len(core) < 2 or not any(ch.isalpha() for ch in core):
                    continue
                votes[column].setdefault(core.lower(), Counter())[core] += 1
    evidence: dict = {}
    for column, counters in votes.items():
        learned = {}
        for key, counter in counters.items():
            form, count = counter.most_common(1)[0]
            total = sum(counter.values())
            if total >= min_count and count / total >= min_share:
                learned[key] = {"form": form, "share": round(count / total, 3), "count": total}
        if learned:
            evidence[column] = learned
    return evidence


# ---------------------------------------------------------------------------
# Profiles and pattern induction
# ---------------------------------------------------------------------------

def induce_pattern(value: str) -> dict:
    """A character-class shape of one value, exact and collapsed."""
    classes = []
    for ch in value:
        if ch.isupper():
            classes.append("A")
        elif ch.islower():
            classes.append("a")
        elif ch.isdigit():
            classes.append("9")
        elif ch == " ":
            classes.append(" ")
        elif ord(ch) > 127:
            classes.append("U")
        else:
            classes.append(ch)
    shape = "".join(classes)
    collapsed = re.sub(r"(.)\1+", lambda match: match.group(1) + "+", shape)
    return {"shape": shape, "collapsed": collapsed}


def profile_column(values, catalogs: dict | None = None, *, top_patterns: int = 5) -> dict:
    """Evidence about one column: case, whitespace, encoding, and shape counts."""
    catalogs = catalogs or {}
    suffixes = catalogs.get("legal_suffixes") or {}
    counts = Counter()
    patterns = Counter()
    total = 0
    for raw in values:
        total += 1
        value = "" if raw is None else str(raw)
        if is_null_sentinel(value, catalogs):
            counts["null_or_sentinel"] += 1
            continue
        letters = [ch for ch in value if ch.isalpha()]
        if letters and all(ch.isupper() for ch in letters):
            counts["all_upper"] += 1
        elif letters and all(ch.islower() for ch in letters):
            counts["all_lower"] += 1
        elif letters:
            counts["mixed_case"] += 1
        if value != value.strip() or "  " in value:
            counts["whitespace_issue"] += 1
        if any(ch in _SPACE_CHARACTERS or ch in _ZERO_WIDTH for ch in value):
            counts["nonstandard_space_or_zero_width"] += 1
        if any(ord(ch) > 127 for ch in value):
            counts["non_ascii"] += 1
        if any(ch.isdigit() for ch in value):
            counts["contains_digits"] += 1
        if _EMAIL.match(value.strip()):
            counts["email_like"] += 1
        if "://" in value or re.match(r"^(www\.)?[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+", value.strip()):
            counts["url_like"] += 1
        if len(re.sub(r"\D", "", value)) >= 7 and len(re.sub(r"[\d\s()+.\-x]", "", value.lower())) <= 3:
            counts["phone_like"] += 1
        tokens = value.strip().split(" ")
        if tokens and _suffix_key(tokens[-1]) in suffixes:
            counts["legal_suffix_like"] += 1
        patterns[induce_pattern(value.strip())["collapsed"]] += 1
    return {"total": total, "counts": dict(sorted(counts.items())),
            "shares": {key: round(count / total, 3) for key, count in sorted(counts.items())} if total else {},
            "top_patterns": [{"pattern": pattern, "count": count, "share": round(count / total, 3)}
                             for pattern, count in patterns.most_common(top_patterns)] if total else []}


def duckdb_profile_sql(table: str, column: str) -> str:
    """The same counts as ``profile_column`` as one DuckDB query over a table."""
    quoted = '"' + column.replace('"', '""') + '"'
    return (
        f"SELECT count(*) AS total, "
        f"sum(CASE WHEN regexp_matches({quoted}, '[A-Za-z]') AND {quoted} = upper({quoted}) THEN 1 ELSE 0 END) AS all_upper, "
        f"sum(CASE WHEN regexp_matches({quoted}, '[A-Za-z]') AND {quoted} = lower({quoted}) THEN 1 ELSE 0 END) AS all_lower, "
        f"sum(CASE WHEN {quoted} <> trim({quoted}) OR {quoted} LIKE '%  %' THEN 1 ELSE 0 END) AS whitespace_issue, "
        f"sum(CASE WHEN regexp_matches({quoted}, '[^\\x00-\\x7F]') THEN 1 ELSE 0 END) AS non_ascii "
        f"FROM {table}")


def summarize(corrections, rules) -> dict:
    """Per-rule and overall outcome counts plus a confidence histogram."""
    per_rule = {rule["rule_id"]: {outcome: 0 for outcome in OUTCOMES} for rule in rules}
    overall = {outcome: 0 for outcome in OUTCOMES}
    histogram = [0] * 10
    reasons = Counter()
    for item in corrections:
        per_rule.setdefault(item["rule_id"], {outcome: 0 for outcome in OUTCOMES})
        per_rule[item["rule_id"]][item["outcome"]] += 1
        overall[item["outcome"]] += 1
        histogram[min(int(item["confidence"] * 10), 9)] += 1
        for reason in item["reasons"]:
            reasons[reason.split(":", 1)[0]] += 1
    return {"per_rule": per_rule, "overall": overall, "confidence_histogram": histogram,
            "reason_counts": dict(sorted(reasons.items()))}
