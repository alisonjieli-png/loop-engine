"""The command risk policy: which effects a shell command has, and whether one is irreversible.

The command safety station asks one typed question of an engine: may this
command run without a person? This module is the written policy behind that
question and the station's own guard. It parses a command without running
it, names every effect it can see (deletes, network access, history
rewrites, publishing, privilege, process control, system changes) and says
whether any effect cannot be undone from inside the workspace.

Owns:
    - EFFECTS, RISK_EFFECTS, WORKSPACE_EFFECTS: the effect vocabulary, the
      effects that need an explicit grant, and the usual workspace grant.
    - CommandRiskAssessment: the effects, the irreversible flag and reasons.
    - assess_command: the parse and classification, pure and offline.
    - safe_under: whether an assessment stays inside the granted effects.

Does not own: running a command, granting authority, or asking a person.
A command this module cannot parse, or whose program is computed at run time
(an unresolved variable, a substitution, ``eval``, a shell reading its
input), is never safe: the policy cannot see what it would do, so a person
decides. When the parse is ambiguous the policy takes the more cautious
reading.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
import re
import shlex

POLICY_VERSION = "command_risk_policy/v1"
ASSESSMENT_VERSION = "command_risk_assessment/v1"
EFFECTS = ("read", "write", "execute", "delete", "network", "history_rewrite", "publish",
           "privilege", "process_control", "system", "dynamic")
(READ, WRITE, EXECUTE, DELETE, NETWORK, HISTORY_REWRITE, PUBLISH,
 PRIVILEGE, PROCESS_CONTROL, SYSTEM, DYNAMIC) = EFFECTS
#: Effects a step may take only when its authority grants them. The last is
#: the policy's own blindness: a computed program can do anything, so it can
#: never be granted in advance.
RISK_EFFECTS = (DELETE, NETWORK, HISTORY_REWRITE, PUBLISH, PRIVILEGE, PROCESS_CONTROL, SYSTEM, DYNAMIC)
#: The effects a step usually holds inside its own confined workspace.
WORKSPACE_EFFECTS = (READ, WRITE, EXECUTE)
MAXIMUM_COMMAND_CHARACTERS = 65_536
MAXIMUM_NESTING = 6

_SEPARATORS = frozenset({";", "&&", "||", "|", "&", "(", ")", "|&", ";;", "{", "}", ";&", ";;&"})
_CONTROL_WORDS = frozenset({"then", "do", "else", "elif", "if", "while", "until", "!", "time", "coproc"})
#: Wrappers run the command after them. Each lists the options that take a
#: separate value, so ``sudo -u root rm`` reaches ``rm`` and ``sudo -i rm``
#: does not swallow it.
_WRAPPER_VALUE_OPTIONS = {
    "sudo": {"-u", "-g", "-h", "-p", "-C", "-D", "-r", "-t", "-U", "-T", "--user", "--group", "--host",
             "--prompt", "--close-from", "--chdir", "--role", "--type", "--other-user", "--command-timeout"},
    "doas": {"-u", "-C"}, "pkexec": {"--user"},
    "env": {"-u", "-C", "--unset", "--chdir"}, "nohup": set(), "setsid": set(), "command": set(),
    "builtin": set(), "noglob": set(), "chronic": set(), "unbuffer": set(), "exec": {"-a"},
    "nice": {"-n", "--adjustment"}, "ionice": {"-c", "-n", "-p", "-P", "-u", "--class", "--classdata"},
    "stdbuf": {"-i", "-o", "-e", "--input", "--output", "--error"},
    "timeout": {"-s", "-k", "--signal", "--kill-after"}, "time": {"-f", "-o", "--format", "--output"},
    "strace": {"-o", "-e", "-p", "-s", "-P", "-a", "-b", "-E", "-I", "-O", "-S", "-U", "-X"},
    "ltrace": {"-o", "-e", "-p", "-s", "-a", "-n", "-u"}, "fakeroot": {"-i", "-s", "-l", "-b"},
    "caffeinate": {"-t", "-w"}, "watch": {"-n", "--interval", "-q"}, "flock": {"-w", "-E", "--timeout"},
}
_PRIVILEGED_WRAPPERS = frozenset({"sudo", "doas", "pkexec"})
_SYSTEM_PATH = re.compile(r"^(?:/(?:etc|usr|bin|sbin|lib|lib32|lib64|boot|dev|sys|proc|var|opt|root|srv|"
                          r"snap|mnt|media)(?:/|$)|/\*?$|~/?\*?$|\$HOME/?\*?$|\$\{HOME\}/?\*?$|/home/?\*?$|"
                          r"/home/[^/]+/?\*?$)")
_VARIABLE = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))")
_ASSIGNMENT = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=(.*)", re.DOTALL)
_HEREDOC = re.compile(r"<<(-?)[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")
_PLACEHOLDER = "__heredoc_{}__"


class CommandRiskPolicyError(ValueError):
    """The input is not a command the policy can assess at all."""


@dataclass(frozen=True)
class CommandRiskAssessment:
    """What the policy sees in one command. It grants and runs nothing."""

    command_digest: str
    effects: tuple[str, ...]
    irreversible: bool
    reasons: tuple[str, ...]
    parse_complete: bool
    policy_version: str = POLICY_VERSION

    @property
    def risk_effects(self) -> tuple[str, ...]:
        return tuple(item for item in self.effects if item in RISK_EFFECTS)

    def to_dict(self) -> dict:
        return {"record_type": ASSESSMENT_VERSION, "policy_version": self.policy_version,
                "command_digest": self.command_digest, "effects": list(self.effects),
                "risk_effects": list(self.risk_effects), "irreversible": self.irreversible,
                "reasons": list(self.reasons), "parse_complete": self.parse_complete}


def validate_grant(granted) -> frozenset:
    """A grant names known effects and never the policy's own blindness."""
    if type(granted) not in (tuple, list, frozenset, set) or any(item not in EFFECTS for item in granted):
        raise CommandRiskPolicyError("a grant is a collection of known effects")
    if DYNAMIC in granted:
        raise CommandRiskPolicyError("a computed program can never be granted in advance")
    return frozenset(granted)


def safe_under(assessment: CommandRiskAssessment, granted=WORKSPACE_EFFECTS) -> bool:
    """Safe to run without a person only when every effect is granted, the
    command parsed completely, and nothing it does is irreversible."""
    if not isinstance(assessment, CommandRiskAssessment):
        raise CommandRiskPolicyError("an assessment is required")
    granted = validate_grant(granted)
    return (assessment.parse_complete and not assessment.irreversible
            and set(assessment.effects) <= granted)


class _Findings:
    def __init__(self):
        self.effects: set[str] = set()
        self.irreversible = False
        self.reasons: list[str] = []
        self.complete = True

    def add(self, effect: str, reason: str, *, irreversible: bool = False):
        self.effects.add(effect)
        if reason not in self.reasons:
            self.reasons.append(reason)
        self.irreversible = self.irreversible or irreversible

    def blind(self, reason: str):
        self.complete = False
        self.add(DYNAMIC, reason)


class _Context:
    """What one assessment carries across nested commands."""

    def __init__(self, reversible_deletes: bool):
        self.reversible_deletes = reversible_deletes
        self.variables: dict[str, str] = {}
        self.heredocs: dict[str, str] = {}


def assess_command(command: str, *, reversible_deletes: bool = False) -> CommandRiskAssessment:
    """Assess one shell command string without running it.

    ``reversible_deletes`` is the workspace's own declaration that it can undo
    a delete, such as a snapshot before every command. Without it every
    delete is irreversible, because the policy cannot see whether a file was
    tracked anywhere."""
    if not isinstance(command, str) or not command.strip() or len(command) > MAXIMUM_COMMAND_CHARACTERS:
        raise CommandRiskPolicyError("a nonempty command of at most 65,536 characters is required")
    if type(reversible_deletes) is not bool:
        raise CommandRiskPolicyError("reversible_deletes must be an explicit Boolean")
    findings, context = _Findings(), _Context(reversible_deletes)
    _assess_text(command, findings, context, 0)
    if not findings.effects:
        findings.add(READ, "no effect beyond reading was found")
    return CommandRiskAssessment(hashlib.sha256(command.encode("utf-8")).hexdigest(),
                                 tuple(item for item in EFFECTS if item in findings.effects),
                                 findings.irreversible, tuple(findings.reasons), findings.complete)


def _extract_heredocs(text, context):
    """Move every here-document body out of the text, leaving a placeholder word."""
    output, position = [], 0
    while True:
        match = _HEREDOC.search(text, position)
        if match is None:
            output.append(text[position:])
            return "".join(output)
        line_end = text.find("\n", match.end())
        if line_end < 0:
            output.append(text[position:])
            return "".join(output)
        delimiter = match.group(3)
        terminator = re.compile(r"^[ \t]*" + re.escape(delimiter) + r"[ \t]*$", re.MULTILINE)
        end = terminator.search(text, line_end + 1)
        body_end = end.start() if end else len(text)
        resume = end.end() if end else len(text)
        name = _PLACEHOLDER.format(len(context.heredocs))
        context.heredocs[name] = text[line_end + 1:body_end]
        output.append(text[position:match.start()] + "<< " + name + text[match.end():line_end + 1])
        position = resume


def _substitutions(text):
    """The inner text of every ``$(...)`` in the text, quoted or not."""
    found, start = [], 0
    while True:
        index = text.find("$(", start)
        if index < 0:
            return found
        if text.startswith("$((", index):
            start = index + 3
            continue
        depth, cursor = 1, index + 2
        while cursor < len(text) and depth:
            depth += {"(": 1, ")": -1}.get(text[cursor], 0)
            cursor += 1
        found.append(text[index + 2:cursor - 1])
        start = cursor


def _assess_text(text, findings, context, depth):
    if depth > MAXIMUM_NESTING:
        findings.blind("commands are nested too deeply to read")
        return
    text = text.replace("\\\n", " ")
    text = _extract_heredocs(text, context)
    for inner in re.findall(r"`([^`]*)`", text):
        if inner.strip():
            _assess_text(inner, findings, context, depth + 1)
    for inner in _substitutions(text):
        if inner.strip():
            _assess_text(inner, findings, context, depth + 1)
    try:
        lexer = shlex.shlex(text, posix=True, punctuation_chars="();<>|&")
        lexer.whitespace_split = True
        lexer.commenters = "#"
        tokens = list(lexer)
    except ValueError:
        findings.blind("the command does not parse: unbalanced quotes or escapes")
        return
    for words, redirects in _simple_commands(tokens):
        _assess_simple(words, redirects, findings, context, depth)


def _simple_commands(tokens):
    words, redirects, pending = [], [], None
    for token in tokens:
        if pending is not None:
            redirects.append((pending, token))
            pending = None
            continue
        if token in _SEPARATORS or (token and set(token) <= set(";&|()")):
            if words or redirects:
                yield words, redirects
            words, redirects = [], []
            continue
        if re.fullmatch(r"\d*(?:>>?|&>>?|>\||<>?|<<<?|>&|<&)", token):
            pending = token
            continue
        words.append(token)
    if words or redirects:
        yield words, redirects


def _expand(word, context):
    """Resolve variables assigned earlier in the same command; None when a
    variable is unknown."""
    def value(match):
        name = match.group(1) or match.group(2)
        if name not in context.variables:
            raise KeyError(name)
        return context.variables[name]
    try:
        return _VARIABLE.sub(value, word)
    except KeyError:
        return None


def _program(words, findings, context):
    """Strip assignments and wrappers: (program, arguments, privileged), or None
    when the program itself is computed at run time."""
    privileged, index = False, 0
    while index < len(words):
        word = words[index]
        assignment = _ASSIGNMENT.fullmatch(word)
        if assignment:
            resolved = _expand(assignment.group(2), context)
            if resolved is not None:
                context.variables[assignment.group(1)] = resolved
            else:
                context.variables.pop(assignment.group(1), None)
            index += 1
            continue
        if word in _CONTROL_WORDS:
            index += 1
            continue
        resolved = _expand(word, context)
        if resolved is None:
            base = os.path.basename(word)
            if "$" in base or not base:
                findings.blind("the program is computed at run time")
                return None
            resolved = base
        name = os.path.basename(resolved)
        if name in _WRAPPER_VALUE_OPTIONS:
            privileged = privileged or name in _PRIVILEGED_WRAPPERS
            index = _skip_wrapper(name, words, index + 1, findings, context)
            if index is None:
                return None
            continue
        if name == "su":
            return "su", words[index + 1:], True
        return name, words[index + 1:], privileged
    return "", [], privileged


def _skip_wrapper(name, words, index, findings, context):
    """The index of the wrapped command, after the wrapper's own options."""
    takes_value = _WRAPPER_VALUE_OPTIONS[name]
    while index < len(words) and words[index].startswith("-") and words[index] != "-":
        option = words[index]
        if name == "env" and option in ("-S", "--split-string") and index + 1 < len(words):
            _assess_text(words[index + 1], findings, context, 1)
            return len(words)
        if name == "flock" and option in ("-c", "--command") and index + 1 < len(words):
            _assess_text(words[index + 1], findings, context, 1)
            return len(words)
        index += 2 if option in takes_value else 1
    if name == "timeout" and index < len(words):
        index += 1          # the duration
    if name == "flock" and index < len(words):
        index += 1          # the lock file
    if name == "watch" and index == len(words) - 1:
        # One word: watch passes it to a shell.
        _assess_text(words[index], findings, context, 1)
        return len(words)
    return index


def _assess_simple(words, redirects, findings, context, depth):
    heredoc = ""
    for operator, target in redirects:
        if operator == "<<" and target in context.heredocs:
            heredoc = context.heredocs[target]
            continue
        if operator == "<<<":
            heredoc = target
            continue
        if operator.startswith("<"):
            continue
        if target in ("/dev/null", "/dev/stdout", "/dev/stderr", "&1", "&2", "1", "2", "-") \
                or target.startswith("&"):
            continue
        if _SYSTEM_PATH.match(target) or target.startswith("/dev/"):
            findings.add(SYSTEM, "output is redirected into a system path", irreversible=True)
        elif not words or words[0] in (":", "true"):
            findings.add(DELETE, "an empty redirection discards a file's contents",
                         irreversible=not context.reversible_deletes)
        else:
            findings.add(WRITE, "output is redirected into a file")
    if not words:
        return
    resolved = _program(words, findings, context)
    if resolved is None:
        return
    program, args, privileged = resolved
    if privileged:
        findings.add(PRIVILEGE, "the command runs with raised privilege")
    if not program:
        return
    if re.fullmatch(r"mkfs(?:\.\w+)?", program):
        program = "mkfs"
    if re.fullmatch(r"python[23]?(?:\.\d+)?", program):
        program = "python3"
    _programs().read_program(program, args, findings, context, depth, heredoc)


def _programs():
    """The per-program readers, imported at first use so neither module
    imports the other while it is still loading."""
    from . import command_risk_programs
    return command_risk_programs
