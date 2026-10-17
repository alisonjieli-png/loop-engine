"""Read, and later check, a Python library's public surface inside the sandbox: standard library only.

```text
python3.14 -I -S -B python_introspect.py read SPEC RESULT     (run by python_native.py in bubblewrap)
├── an audit hook first: a network event, a started process or a write outside the output folder is recorded
│   against the module being imported or read (the caller refuses that module's surface by name)
├── sys.path: the interpreter's standard library and the unpacked wheels only (no site, no user folders)
├── the public modules: each seed, then (when the spec asks) the submodules a module's own __all__ names;
│   a module's public names are its __all__, else its attributes without a leading underscore
├── a class or a function becomes a candidate at the first public path it is found at (later paths are aliases)
└── per candidate: where it is defined (file and line, or the compiled module), its own docstring, its
    signature as inspect reports it (annotations as written), a class's method resolution order and every public
    member with its owner, kind, signature, type or value

python3.14 -I -S -B python_introspect.py verify SPEC RESULT
└── per card: the object at its public path is resolved again and every listed item is read the same way and
    compared; the listed ancestors must be in the class's method resolution order, in the listed order
```

The functions below are the only code that turns an object into a surface, so the read and the check cannot
disagree about a format. Values are written deterministically: memory addresses are removed, long values are cut,
and the caller runs the interpreter with a fixed hash seed. Nothing here reads the network or writes anywhere but
the result file.
"""
from __future__ import annotations

import functools
import importlib
import inspect
import json
import os
import re
import sys
import types
import warnings

try:  # Python 3.14: annotations exactly as the source writes them, never evaluated.
    import annotationlib
    SIGNATURE_OPTIONS = {"annotation_format": annotationlib.Format.STRING}
    ANNOTATION_OPTIONS = {"format": annotationlib.Format.STRING}
except ImportError:  # an older interpreter evaluates nothing new either: string annotations stay strings
    SIGNATURE_OPTIONS, ANNOTATION_OPTIONS = {}, {}

RESULTS_RECORD = "python_api_introspection/v1"
CHECK_RECORD = "python_api_check_results/v1"
SPEC_RECORD = "python_api_introspection_spec/v1"
#: Audit events that reach the network, start a process, or change files: any of them during an import or a read
#: is recorded. A file opened for writing outside the output folder is a write; reading is never recorded. A socket
#: event whose address is this machine's own (a loopback address, a local socket file, a bind such as urllib3's
#: probe for IPv6 support, which binds ::1 when requests is imported) is recorded as local and reaches no network.
ADDRESS_EVENTS = frozenset(("socket.connect", "socket.sendto", "socket.sendmsg"))
NAME_EVENTS = frozenset(("socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyname_ex",
                         "socket.gethostbyaddr", "socket.getnameinfo"))
LOCAL_EVENTS = frozenset(("socket.bind",))
NETWORK_EVENTS = frozenset(("http.client.connect", "urllib.Request", "ftplib.connect", "smtplib.connect",
                            "poplib.connect", "imaplib.open", "nntplib.connect", "webbrowser.open"))
LOOPBACK_NAMES = frozenset(("localhost", "", "::1", "0.0.0.0", "::"))
PROCESS_EVENTS = frozenset(("subprocess.Popen", "os.system", "os.posix_spawn", "os.fork", "os.forkpty",
                            "pty.spawn", "os.startfile"))
PROCESS_PREFIXES = ("os.exec", "os.spawn")
WRITE_EVENTS = frozenset(("os.remove", "os.rename", "os.rmdir", "os.mkdir", "os.truncate", "os.symlink", "os.link",
                          "shutil.rmtree", "shutil.move", "shutil.copyfile", "os.chmod", "os.chown"))
NETWORK, PROCESS, WRITE, LOCAL = EVENT_KINDS = ("network", "process", "write", "local")
#: The audit event of a file being opened, whose mode and flags say whether it is opened for writing.
OPEN_EVENT = "open"
#: Module path parts that are never a public surface (a test suite shipped in the wheel).
TEST_PARTS = frozenset(("tests", "test", "conftest"))
#: The kinds of a candidate and of a class member, and the qualifiers a signature carries.
CLASS, FUNCTION = "class", "function"
METHOD, PROPERTY, FIELD, CONSTANT = MEMBER_KINDS = ("method", "property", "field", "constant")
ASYNC, CLASSMETHOD, STATICMETHOD, READONLY, ABSTRACT = "async", "classmethod", "staticmethod", "readonly", "abstract"
QUALIFIER_ORDER = (ABSTRACT, ASYNC, CLASSMETHOD, STATICMETHOD, READONLY)
KIND_NAMES = {inspect.Parameter.POSITIONAL_ONLY: "positional_only",
              inspect.Parameter.POSITIONAL_OR_KEYWORD: "positional_or_keyword",
              inspect.Parameter.VAR_POSITIONAL: "var_positional", inspect.Parameter.KEYWORD_ONLY: "keyword_only",
              inspect.Parameter.VAR_KEYWORD: "var_keyword"}
#: The longest value text kept (a default, a constant); a longer one is cut and ends with an ellipsis.
MAXIMUM_VALUE = 200
ELLIPSIS = "…"
UNREPRESENTABLE = "<unrepresentable>"
_ADDRESS = re.compile(r" at 0x[0-9A-Fa-f]+")
#: Type modules whose callable objects are typing constructs, never functions of the library.
TYPING_MODULES = frozenset(("typing", "types", "typing_extensions", "abc"))
COMPILED_SUFFIXES = (".so", ".pyd")


class Guard:
    """The audit hook: what the library did besides reading files, attributed to the module being imported."""

    def __init__(self, writable: str) -> None:
        self.writable = os.path.abspath(writable) + os.sep
        self.context = "<startup>"
        self.events = []
        self.busy = False

    def _outside(self, path) -> bool:
        if isinstance(path, bytes):
            path = os.fsdecode(path)
        if not isinstance(path, str):
            return False  # a file descriptor: its opening was already seen
        return not os.path.abspath(path).startswith(self.writable)

    def __call__(self, event: str, args) -> None:
        if self.busy:
            return
        self.busy = True
        try:
            kind = None
            if event in NETWORK_EVENTS:
                kind = NETWORK
            elif event in ADDRESS_EVENTS:
                address = args[1] if len(args) > 1 else None
                kind = LOCAL if _local_address(address) else NETWORK
            elif event in NAME_EVENTS:
                kind = LOCAL if _local_host(args[0] if args else None) else NETWORK
            elif event in LOCAL_EVENTS:
                kind = LOCAL
            elif event in PROCESS_EVENTS or event.startswith(PROCESS_PREFIXES):
                kind = PROCESS
            elif event == OPEN_EVENT and len(args) >= 3:
                path, mode, flags = args[0], args[1], args[2]
                writing = (isinstance(mode, str) and any(letter in mode for letter in "wax+")) or (
                    isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT |
                                                        os.O_TRUNC))
                kind = WRITE if writing and self._outside(path) else None
            elif event in WRITE_EVENTS and args and self._outside(args[0]):
                kind = WRITE
            if kind is not None and len(self.events) < 200:
                self.events.append({"module": self.context, "kind": kind, "event": event,
                                    "detail": stable(_safe_repr(args))[:160]})
        finally:
            self.busy = False


def _local_host(host) -> bool:
    """Whether a host names this machine: a loopback name or address (127.0.0.0/8, ::1), or none."""
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    if host is None:
        return True
    host = str(host).strip("[]").lower()
    return host in LOOPBACK_NAMES or host.startswith("127.") or host.startswith("::ffff:127.")


def _local_address(address) -> bool:
    """Whether a socket address is this machine's: a local socket file, or a loopback host."""
    if isinstance(address, (str, bytes)):
        return True  # an AF_UNIX socket file (the sandbox shows no host socket)
    if isinstance(address, tuple) and address:
        return _local_host(address[0])
    return False


def _safe_repr(value) -> str:
    try:
        return repr(value)
    except Exception:  # noqa: BLE001 - a library's repr may raise anything; the record says so
        return UNREPRESENTABLE


def stable(text: str) -> str:
    """Text without memory addresses (``<object object at 0x7f...>`` becomes ``<object object>``)."""
    return _ADDRESS.sub("", str(text))


def value_text(value) -> str:
    """A value as the surface writes it: its repr, without addresses, cut at MAXIMUM_VALUE characters."""
    text = stable(_safe_repr(value))
    return text if len(text) <= MAXIMUM_VALUE else text[:MAXIMUM_VALUE - 1] + ELLIPSIS


def annotation_text(annotation) -> str:
    if isinstance(annotation, str):
        return stable(annotation)
    try:
        return stable(inspect.formatannotation(annotation))
    except Exception:  # noqa: BLE001
        return value_text(annotation)


def signature_of(target, *, drop_first: bool = False) -> "dict | None":
    """{"params": [...], "returns": text or None} as inspect reports the signature, or None when it cannot."""
    try:
        signature = inspect.signature(target, **SIGNATURE_OPTIONS)
    except Exception:  # noqa: BLE001 - no signature the interpreter can report
        return None
    parameters = list(signature.parameters.values())
    if drop_first and parameters and parameters[0].kind in (inspect.Parameter.POSITIONAL_ONLY,
                                                            inspect.Parameter.POSITIONAL_OR_KEYWORD):
        parameters = parameters[1:]
    rows = []
    for parameter in parameters:
        row = {"name": parameter.name, "kind": KIND_NAMES[parameter.kind]}
        if parameter.annotation is not inspect.Parameter.empty:
            row["type"] = annotation_text(parameter.annotation)
        if parameter.default is not inspect.Parameter.empty:
            row["default"] = value_text(parameter.default)
        rows.append(row)
    returned = signature.return_annotation
    return {"params": rows, "returns": None if returned is inspect.Signature.empty else annotation_text(returned)}


def own_doc(value) -> "str | None":
    """An object's own docstring, cleaned the way inspect.cleandoc cleans one, or None."""
    text = getattr(value, "__doc__", None)
    if not isinstance(text, str) or not text.strip():
        return None
    return inspect.cleandoc(text)


def _ordered(words) -> list:
    return [word for word in QUALIFIER_ORDER if word in words]


def _code(value):
    try:
        target = inspect.unwrap(value)
    except Exception:  # noqa: BLE001 - a wrapper chain that loops
        target = value
    for candidate in (target, getattr(target, "__func__", None), getattr(target, "fget", None)):
        code = getattr(candidate, "__code__", None)
        if isinstance(code, types.CodeType):
            return code
    return None


def module_of(value) -> "str | None":
    """The module an object belongs to: its own __module__, a method descriptor's class's, a bound builtin's."""
    name = getattr(value, "__module__", None)
    if isinstance(name, str):
        return name
    owner = getattr(value, "__objclass__", None)
    if owner is not None and isinstance(getattr(owner, "__module__", None), str):
        return owner.__module__
    bound = getattr(value, "__self__", None)
    if bound is not None and not isinstance(bound, types.ModuleType):
        return getattr(type(bound), "__module__", None)
    return None


class Reader:
    """Everything one read sees: the unpacked wheels' folders, the target's, the candidates and their order."""

    def __init__(self, spec: dict) -> None:
        self.roots = [os.path.abspath(path) + os.sep for path in spec["roots"]]
        self.target = spec.get("target", 0)
        self.spec = spec

    def place(self, filename, line=None) -> dict:
        """{"root", "file", "line", "compiled"} of a file: the wheel folder it is in (None for the interpreter's
        own) and its path inside that folder."""
        filename = os.path.abspath(str(filename))
        for index, root in enumerate(self.roots):
            if filename.startswith(root):
                return {"root": index, "file": filename[len(root):], "line": line,
                        "compiled": filename.endswith(COMPILED_SUFFIXES)}
        return {"root": None, "file": filename, "line": line, "compiled": filename.endswith(COMPILED_SUFFIXES)}

    def source_of(self, value) -> "dict | None":
        """Where an object is defined: its code's file and first line, a class's first own function, else the file
        of the module it names (a compiled extension for most builtins)."""
        code = _code(value)
        # A Cython function carries a code object naming the .pyx file where it was compiled, on the build machine;
        # it is then found by its module, a compiled extension of the wheel.
        if code is not None and self.place(code.co_filename)["root"] is not None:
            return self.place(code.co_filename, code.co_firstlineno)
        if inspect.isclass(value):
            prefix = getattr(value, "__qualname__", "") + "."
            for member in list(vars(value).values()):
                code = _code(member)
                if code is not None and str(getattr(code, "co_qualname", prefix)).startswith(prefix) and \
                        self.place(code.co_filename)["root"] is not None:
                    return self.place(code.co_filename, code.co_firstlineno)
        module = sys.modules.get(module_of(value) or "")
        filename = getattr(module, "__file__", None)
        return self.place(filename) if isinstance(filename, str) else None

    def owned(self, value) -> bool:
        source = self.source_of(value)
        return bool(source) and source["root"] == self.target


def key_of(value) -> str:
    return f"{module_of(value) or '?'}.{getattr(value, '__qualname__', getattr(value, '__name__', '?'))}"


def is_function(value) -> bool:
    """A routine, or a callable object that names itself and is not a class or a typing construct (a ufunc)."""
    if inspect.isclass(value) or isinstance(value, types.ModuleType):
        return False
    if inspect.isroutine(value):
        return True
    return (callable(value) and isinstance(getattr(value, "__name__", None), str)
            and getattr(type(value), "__module__", "") not in TYPING_MODULES)


def annotations_of(owner) -> dict:
    try:
        found = inspect.get_annotations(owner, **ANNOTATION_OPTIONS)
    except Exception:  # noqa: BLE001
        return {}
    return {name: annotation_text(value) for name, value in found.items() if isinstance(name, str)}


def member_record(reader: Reader, name: str, owner, raw) -> "dict | None":
    """One public member as the surface lists it, from the attribute its owner's namespace holds; None for a
    nested class or a member the surface does not describe."""
    row = {"name": name, "owner": key_of(owner)}
    annotations = annotations_of(owner)
    if isinstance(raw, staticmethod):
        function = raw.__func__
        row.update(kind=METHOD, qualifiers=_ordered([STATICMETHOD] + _flags(function)),
                   signature=signature_of(function), doc=own_doc(function), source=reader.source_of(function))
    elif isinstance(raw, (classmethod, types.ClassMethodDescriptorType)):
        function = getattr(raw, "__func__", raw)
        row.update(kind=METHOD, qualifiers=_ordered([CLASSMETHOD] + _flags(function)),
                   signature=signature_of(function, drop_first=True), doc=own_doc(function),
                   source=reader.source_of(function))
    elif isinstance(raw, property):
        returned = (signature_of(raw.fget) or {}).get("returns") if raw.fget is not None else None
        row.update(kind=PROPERTY, qualifiers=_ordered([READONLY] if raw.fset is None else []) +
                   ([ABSTRACT] if getattr(raw, "__isabstractmethod__", False) else []),
                   type=returned, doc=own_doc(raw), source=reader.source_of(raw.fget) if raw.fget else None)
    elif isinstance(raw, functools.cached_property):
        returned = (signature_of(raw.func) or {}).get("returns")
        row.update(kind=PROPERTY, qualifiers=[], type=returned, doc=own_doc(raw.func),
                   source=reader.source_of(raw.func))
    elif inspect.isfunction(raw) or inspect.isbuiltin(raw) or (inspect.ismethoddescriptor(raw) and callable(raw)):
        row.update(kind=METHOD, qualifiers=_ordered(_flags(raw)), signature=signature_of(raw, drop_first=True),
                   doc=own_doc(raw), source=reader.source_of(raw))
    elif inspect.isdatadescriptor(raw) or (hasattr(type(raw), "__get__") and not inspect.isclass(raw)):
        # A getset or member descriptor of a compiled class, or another descriptor (an accessor): its own text
        # only when it is not its type's generic one.
        text = own_doc(raw)
        if text is not None and text == own_doc(type(raw)):
            text = None
        row.update(kind=PROPERTY, qualifiers=[], type=annotations.get(name), doc=text, source=None)
    elif inspect.isclass(raw):
        return None
    elif name in annotations:
        row.update(kind=FIELD, qualifiers=[], type=annotations[name], default=value_text(raw), doc=None,
                   source=None)
    elif callable(raw):
        return None
    else:
        row.update(kind=CONSTANT, qualifiers=[], value=value_text(raw), doc=None, source=None)
    return row


def _flags(function) -> list:
    flags = []
    try:
        if inspect.iscoroutinefunction(function) or inspect.isasyncgenfunction(function):
            flags.append(ASYNC)
    except Exception:  # noqa: BLE001
        pass
    if getattr(function, "__isabstractmethod__", False):
        flags.append(ABSTRACT)
    return flags


def members_of(reader: Reader, cls) -> list:
    """Every public member of a class with the class in its method resolution order that holds it, sorted by name;
    an annotated field without a value is listed from the annotation."""
    try:
        names = set(dir(cls))
    except Exception:  # noqa: BLE001
        names = set()
    mro = [klass for klass in getattr(cls, "__mro__", (cls,)) if klass is not object]
    annotated = {}
    for klass in reversed(mro):
        for name in annotations_of(klass):
            annotated[name] = klass
    rows = []
    for name in sorted(names | set(annotated)):
        if name.startswith("_"):
            continue
        owner = next((klass for klass in mro if name in vars(klass)), None)
        if owner is None:
            owner = annotated.get(name)
            if owner is None:
                continue
            types_ = annotations_of(owner)
            rows.append({"name": name, "owner": key_of(owner), "kind": FIELD, "qualifiers": [],
                         "type": types_.get(name), "doc": None, "source": None})
            continue
        try:
            row = member_record(reader, name, owner, vars(owner)[name])
        except Exception:  # noqa: BLE001 - a member the interpreter cannot describe is left out
            row = None
        if row is not None:
            rows.append(row)
    return rows


def class_record(reader: Reader, cls) -> dict:
    return {"constructor": signature_of(cls),
            "mro": [{"key": key_of(klass), "owned": reader.owned(klass)}
                    for klass in getattr(cls, "__mro__", ())[1:] if klass is not object],
            "members": members_of(reader, cls)}


def exported_names(module) -> tuple:
    """(names, declared): the module's __all__ when it declares one as strings, else its public attributes."""
    declared = getattr(module, "__all__", None)
    if isinstance(declared, (list, tuple)) and all(isinstance(name, str) for name in declared):
        return sorted(set(declared)), True
    return sorted(name for name in vars(module) if isinstance(name, str) and not name.startswith("_")), False


def public_module(name: str, excluded) -> bool:
    parts = name.split(".")
    return (not any(part.startswith("_") or part in TEST_PARTS for part in parts[1:])
            and not any(name == prefix or name.startswith(prefix + ".") for prefix in excluded))


def read(spec: dict, guard: Guard) -> dict:
    reader = Reader(spec)
    excluded = tuple(spec.get("exclude", ()))
    queue, visited, modules, candidates, aliases = list(spec["modules"]), set(), [], {}, {}
    order = []
    while queue:
        name = queue.pop(0)
        if name in visited or not public_module(name, excluded):
            continue
        visited.add(name)
        guard.context = name
        row = {"name": name, "ok": False}
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                module = importlib.import_module(name)
        except BaseException as error:  # noqa: BLE001 - an import that fails or exits is refused by name
            if isinstance(error, KeyboardInterrupt):
                raise
            row["error"] = f"{type(error).__name__}: {stable(error)}"[:300]
            modules.append(row)
            continue
        names, declared = exported_names(module)
        filename = getattr(module, "__file__", None)
        row.update(ok=True, file=reader.place(filename) if isinstance(filename, str) else None, declared_all=declared,
                   exported=len(names))
        modules.append(row)
        for attribute in names:
            if attribute.startswith("_"):
                continue
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    value = getattr(module, attribute)
            except BaseException as error:  # noqa: BLE001
                if isinstance(error, KeyboardInterrupt):
                    raise
                continue
            path = f"{name}.{attribute}"
            try:
                if isinstance(value, types.ModuleType):
                    if spec.get("recurse") and declared and value.__name__ == path:
                        queue.append(path)
                    continue
                if not (inspect.isclass(value) or is_function(value)):
                    continue
            except BaseException as error:  # noqa: BLE001 - a proxy whose every attribute raises is no candidate
                if isinstance(error, KeyboardInterrupt):
                    raise
                continue
            identity = id(value)
            if identity in candidates:
                aliases.setdefault(identity, []).append(path)
                continue
            candidates[identity] = (path, name, attribute, value)
            order.append(identity)
    objects = []
    for identity in order:
        path, module_name, attribute, value = candidates[identity]
        guard.context = path
        record = {"path": path, "module": module_name, "qualname": attribute}
        try:
            record.update(key=key_of(value), kind=CLASS if inspect.isclass(value) else FUNCTION,
                          source=reader.source_of(value), doc=own_doc(value),
                          aliases=sorted(aliases.get(identity, []))[:20])
            if record["kind"] == CLASS:
                record.update(class_record(reader, value))
            else:
                record.update(signature=signature_of(value), qualifiers=_ordered(_flags(value)))
        except Exception as error:  # noqa: BLE001 - recorded; the caller refuses the candidate by name
            record["error"] = f"{type(error).__name__}: {stable(error)}"[:300]
        objects.append(record)
    return {"record_type": RESULTS_RECORD, "interpreter": sys.version.split()[0], "modules": modules,
            "objects": objects}


def resolve(module_name: str, qualname: str):
    """The object at a public path: the module imported, then each attribute of the qualified name."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        value = importlib.import_module(module_name)
        for part in qualname.split("."):
            value = getattr(value, part)
    return value


def surface_of(reader: Reader, value, kind: str, member: "str | None" = None) -> dict:
    """The sections of one card's object, read the way read() reads them (a member card reads one member)."""
    if kind == FUNCTION:
        return {"functions": [{"signature": signature_of(value), "qualifiers": _ordered(_flags(value))}]}
    if kind in (METHOD, PROPERTY):
        owner = next((klass for klass in value.__mro__ if member in vars(klass)), None)
        row = member_record(reader, member, owner, vars(owner)[member]) if owner is not None else None
        return {"member": row}
    record = class_record(reader, value)
    return {"constructor": record["constructor"], "mro": [row["key"] for row in record["mro"]],
            "members": {row["name"]: row for row in record["members"]}}


def check(spec: dict, guard: Guard) -> dict:
    """Every card of the spec asked again: the answer lists what differs; the caller decides what that means."""
    reader = Reader(spec)
    answers = {}
    for card in spec["cards"]:
        guard.context = card["card"]
        answer = {"known": False}
        try:
            value = resolve(card["module"], card["qualname"])
        except BaseException as error:  # noqa: BLE001
            if isinstance(error, KeyboardInterrupt):
                raise
            answer["error"] = f"{type(error).__name__}: {stable(error)}"[:200]
            answers[card["card"]] = answer
            continue
        kind = card["kind"]
        actual = CLASS if inspect.isclass(value) else FUNCTION if is_function(value) else None
        expected_kind = CLASS if kind in (CLASS, METHOD, PROPERTY) else FUNCTION
        answer.update(known=True, kind_matches=actual == expected_kind, differs=[], missing=[])
        if actual != expected_kind:
            answers[card["card"]] = answer
            continue
        try:
            found = surface_of(reader, value, kind, card.get("member"))
        except Exception as error:  # noqa: BLE001
            answer.update(kind_matches=False, error=f"{type(error).__name__}: {stable(error)}"[:200])
            answers[card["card"]] = answer
            continue
        if kind == FUNCTION:
            if found["functions"] != card["functions"]:
                answer["differs"].append(card["qualname"])
        elif kind in (METHOD, PROPERTY):
            if found["member"] is None:
                answer["missing"].append(card["member"])
            elif any(found["member"].get(key) != card["expected"].get(key) for key in card["expected"]):
                answer["differs"].append(card["member"])
        else:
            # A constructor is compared by its parameters: the card does not write a class's return annotation.
            found_parameters = found["constructor"]["params"] if found["constructor"] is not None else None
            if found_parameters != card["constructor"]:
                answer["differs"].append("<constructor>")
            for name, expected in card["members"].items():
                row = found["members"].get(name)
                if row is None:
                    answer["missing"].append(name)
                elif any(row.get(key) != expected.get(key) for key in expected):
                    answer["differs"].append(name)
            positions = [found["mro"].index(key) if key in found["mro"] else -1 for key in card["ancestors"]]
            answer["ancestors_in_order"] = all(position >= 0 for position in positions) and positions == sorted(
                positions)
        answers[card["card"]] = answer
    return {"record_type": CHECK_RECORD, "interpreter": sys.version.split()[0], "cards": answers}


def main(argv) -> int:
    mode, spec_path, result_path = argv[1:4]
    with open(spec_path, encoding="utf-8") as stream:
        spec = json.load(stream)
    if spec.get("record_type") != SPEC_RECORD:
        raise SystemExit(f"expected {SPEC_RECORD}")
    guard = Guard(os.path.dirname(os.path.abspath(result_path)))
    sys.addaudithook(guard)
    sys.path[:] = [entry for entry in sys.path if entry] + list(spec["roots"])
    result = read(spec, guard) if mode == "read" else check(spec, guard)
    result["events"] = guard.events
    guard.busy = True  # the result file is this script's own write
    with open(result_path, "w", encoding="utf-8") as stream:
        json.dump(result, stream, sort_keys=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
