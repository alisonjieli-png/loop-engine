"""RDF terms, a Turtle subset reader, an N-Triples reader and the canonical graph digest.

A term is kept in its canonical N-Triples spelling: ``<iri>``, ``_:label`` or a
literal ``"lexical"`` with an optional ``@lang`` or ``^^<datatype>``. A graph is a
frozenset of (subject, predicate, object) tuples of such spellings, and its
digest is the SHA-256 of its sorted canonical N-Triples lines, so the same graph
always has the same digest whatever file it was read from.

The Turtle reader accepts prefixes and base, prefixed names, ``a``, the three
literal forms with escapes, numbers and booleans, blank node labels, blank node
property lists and collections. Anything else is refused by name with its line
and column: the reader never guesses. Blank nodes read from Turtle are labelled
``_:b0``, ``_:b1`` ... in document order; an N-Triples file keeps its own labels,
so a graph written as canonical N-Triples reads back to the same digest.
Standard library only; nothing is fetched, imported or executed.
"""
from __future__ import annotations

import hashlib
import re

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
OWL = "http://www.w3.org/2002/07/owl#"
XSD = "http://www.w3.org/2001/XMLSchema#"
RDF_TYPE = f"<{RDF}type>"
RDF_FIRST, RDF_REST, RDF_NIL = f"<{RDF}first>", f"<{RDF}rest>", f"<{RDF}nil>"
XSD_STRING = f"{XSD}string"
#: Namespaces whose terms are vocabulary, not the user's own names.
VOCABULARY_NAMESPACES = (RDF, RDFS, OWL, XSD)
#: The most triples one document may hold before reading stops with a refusal.
DEFAULT_MAXIMUM_TRIPLES = 2_000_000

_IRI_FORBIDDEN = set('<>"{}|^`\\ ') | {chr(code) for code in range(0x21)}
_ECHAR = {"t": "\t", "b": "\b", "n": "\n", "r": "\r", "f": "\f", '"': '"', "'": "'", "\\": "\\"}
_ESCAPE_OUT = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\r": "\\r", "\t": "\\t", "\b": "\\b", "\f": "\\f"}
_LANG = re.compile(r"[A-Za-z]+(?:-[A-Za-z0-9]+)*")
_NUMBER = re.compile(r"[+-]?(?:[0-9]+\.?[0-9]*[eE][+-]?[0-9]+|\.[0-9]+[eE][+-]?[0-9]+|[0-9]*\.[0-9]+|[0-9]+)")
_PREFIX = re.compile(r"(?:[A-Za-zÀ-￿](?:[A-Za-z0-9_.·À-￿-]*[A-Za-z0-9_·À-￿-])?)?:")
_LOCAL_ESCAPABLE = set("_~.-!$&'()*+,;=/?#@%")


_REFERENCE = re.compile(r"^(?:([A-Za-z][A-Za-z0-9+.-]*):)?(?://([^/?#]*))?([^?#]*)(?:\?([^#]*))?(?:#(.*))?$")


def _remove_dot_segments(path: str) -> str:
    """RFC 3986 section 5.2.4."""
    output, remaining = [], path
    while remaining:
        if remaining.startswith("../"):
            remaining = remaining[3:]
        elif remaining.startswith("./"):
            remaining = remaining[2:]
        elif remaining.startswith("/./") or remaining == "/.":
            remaining = "/" + remaining[3:]
        elif remaining.startswith("/../") or remaining == "/..":
            remaining = "/" + remaining[4:]
            if output:
                output.pop()
        elif remaining in (".", ".."):
            remaining = ""
        else:
            start = 1 if remaining.startswith("/") else 0
            end = remaining.find("/", start)
            end = len(remaining) if end < 0 else end
            output.append(remaining[:end])
            remaining = remaining[end:]
    return "".join(output)


def resolve_reference(base: str, reference: str) -> str:
    """RFC 3986 section 5.2.2: the target of a reference against an absolute base, as text."""
    scheme, authority, path, query, fragment = _REFERENCE.match(reference).groups()
    b_scheme, b_authority, b_path, b_query, _fragment = _REFERENCE.match(base).groups()
    if scheme is None:
        scheme = b_scheme
        if authority is None:
            if path == "":
                path, query = b_path, query if query is not None else b_query
            elif path.startswith("/"):
                path = _remove_dot_segments(path)
            else:
                merged = ("/" + path) if b_authority is not None and b_path == "" else (
                    b_path[:b_path.rfind("/") + 1] + path)
                path = _remove_dot_segments(merged)
            authority = b_authority
        else:
            path = _remove_dot_segments(path)
    else:
        path = _remove_dot_segments(path)
    target = f"{scheme}:" + (f"//{authority}" if authority is not None else "") + path
    return target + (f"?{query}" if query is not None else "") + (f"#{fragment}" if fragment is not None else "")


class RdfSyntaxError(ValueError):
    """The document is outside the accepted syntax; the message names where."""

    code = "unsupported_syntax"

    def __init__(self, detail: str, line: int = 0, column: int = 0):
        super().__init__(f"line {line} column {column}: {detail}" if line else detail)
        self.detail, self.line, self.column = detail, line, column


def is_iri(term: str) -> bool:
    return term.startswith("<")


def is_blank(term: str) -> bool:
    return term.startswith("_:")


def is_literal(term: str) -> bool:
    return term.startswith('"')


def writable(triple) -> bool:
    """Whether an RDF 1.1 serialiser can write it: a literal is never a subject, a predicate is an IRI."""
    subject, predicate, _object = triple
    return not is_literal(subject) and is_iri(predicate)


def iri(value: str) -> str:
    """The canonical spelling of an absolute IRI, refused when it holds a character N-Triples forbids."""
    if not value or any(character in _IRI_FORBIDDEN for character in value) or ":" not in value:
        raise RdfSyntaxError(f"not an absolute IRI: {value[:80]!r}")
    return f"<{value}>"


def literal(lexical: str, language: "str | None" = None, datatype: "str | None" = None) -> str:
    """The canonical literal: escapes as canonical N-Triples, xsd:string written as a plain literal."""
    escaped = "".join(_ESCAPE_OUT.get(character) or (
        f"\\u{ord(character):04X}" if ord(character) < 0x20 or ord(character) == 0x7F else character)
        for character in lexical)
    if language:
        if not _LANG.fullmatch(language):
            raise RdfSyntaxError(f"not a language tag: {language!r}")
        return f'"{escaped}"@{language.lower()}'
    if datatype and datatype != XSD_STRING:
        return f'"{escaped}"^^{iri(datatype)}'
    return f'"{escaped}"'


def ntriples_line(triple) -> str:
    return f"{triple[0]} {triple[1]} {triple[2]} .\n"


def canonical_ntriples(triples) -> str:
    """The graph as sorted, unique canonical N-Triples lines."""
    return "".join(sorted({ntriples_line(triple) for triple in triples}))


def graph_digest(triples) -> str:
    """SHA-256 of the canonical N-Triples: the identity of a graph's state."""
    return hashlib.sha256(canonical_ntriples(triples).encode("utf-8")).hexdigest()


def user_terms(triple) -> tuple:
    """The IRIs of a triple that are not RDF, RDFS, OWL or XSD vocabulary."""
    return tuple(term for term in triple if is_iri(term) and not term[1:].startswith(VOCABULARY_NAMESPACES))


class _Scanner:
    """Character-level reading shared by the two readers; it builds terms, never triples."""

    def __init__(self, text: str):
        if not isinstance(text, str):
            raise RdfSyntaxError("a document is text")
        self.text, self.index, self.length = text, 0, len(text)

    def where(self) -> tuple:
        line = self.text.count("\n", 0, self.index) + 1
        return line, self.index - (self.text.rfind("\n", 0, self.index) + 1) + 1

    def fail(self, detail: str):
        raise RdfSyntaxError(detail, *self.where())

    def peek(self, size: int = 1) -> str:
        return self.text[self.index:self.index + size]

    def skip_space(self, newlines: bool = True) -> None:
        while self.index < self.length:
            character = self.text[self.index]
            if character == "#":
                end = self.text.find("\n", self.index)
                self.index = self.length if end < 0 else end
            elif character in " \t\r" or (newlines and character == "\n"):
                self.index += 1
            else:
                return

    def expect(self, token: str) -> None:
        if not self.text.startswith(token, self.index):
            self.fail(f"expected {token!r}")
        self.index += len(token)

    def unicode_escape(self) -> str:
        kind = self.peek()
        size = {"u": 4, "U": 8}.get(kind)
        digits = self.text[self.index + 1:self.index + 1 + (size or 0)]
        if size is None or len(digits) != size or not re.fullmatch(r"[0-9A-Fa-f]+", digits):
            self.fail("a \\u escape needs 4 hexadecimal digits and \\U needs 8")
        self.index += 1 + size
        code = int(digits, 16)
        if code > 0x10FFFF or 0xD800 <= code <= 0xDFFF:
            self.fail("an escape names no Unicode character")
        return chr(code)

    def iriref(self) -> str:
        """``<...>`` with its UCHAR escapes read, returned without the brackets."""
        self.expect("<")
        parts = []
        while True:
            if self.index >= self.length:
                self.fail("an IRI is not closed")
            character = self.text[self.index]
            if character == ">":
                self.index += 1
                return "".join(parts)
            if character == "\\":
                self.index += 1
                parts.append(self.unicode_escape())
                continue
            if character in _IRI_FORBIDDEN:
                self.fail(f"character {character!r} is not allowed in an IRI")
            parts.append(character)
            self.index += 1

    def string(self) -> str:
        """One of the four quoted forms, escapes read."""
        quote = self.peek()
        if quote not in "\"'":
            self.fail("expected a quoted string")
        long = self.peek(3) == quote * 3
        self.index += 3 if long else 1
        parts = []
        while True:
            if self.index >= self.length:
                self.fail("a string is not closed")
            if long and self.text.startswith(quote * 3, self.index):
                self.index += 3
                return "".join(parts)
            character = self.text[self.index]
            if not long and character == quote:
                self.index += 1
                return "".join(parts)
            if not long and character in "\r\n":
                self.fail("a short string cannot hold a line break")
            if character == "\\":
                self.index += 1
                escaped = self.peek()
                if escaped in "uU":
                    parts.append(self.unicode_escape())
                    continue
                if escaped not in _ECHAR:
                    self.fail(f"unknown escape \\{escaped}")
                parts.append(_ECHAR[escaped])
                self.index += 1
                continue
            parts.append(character)
            self.index += 1

    def blank_label(self) -> str:
        self.expect("_:")
        match = re.compile(r"[A-Za-z0-9_À-￿](?:[A-Za-z0-9_.·À-￿-]*[A-Za-z0-9_·À-￿-])?"
                           ).match(self.text, self.index)
        if not match:
            self.fail("a blank node label is empty or malformed")
        self.index = match.end()
        return match.group(0)

    def language(self) -> str:
        self.expect("@")
        match = _LANG.match(self.text, self.index)
        if not match:
            self.fail("a language tag is malformed")
        self.index = match.end()
        return match.group(0)


class _TurtleReader(_Scanner):
    """Recursive descent over the accepted Turtle subset."""

    def __init__(self, text: str, base: "str | None", maximum: int):
        super().__init__(text)
        self.base, self.prefixes, self.maximum = base, {}, maximum
        self.blanks, self.triples, self.counter = {}, set(), 0

    def add(self, subject: str, predicate: str, obj: str) -> None:
        if is_literal(subject) or not is_iri(predicate):
            self.fail("a literal cannot be a subject and a predicate must be an IRI")
        self.triples.add((subject, predicate, obj))
        if len(self.triples) > self.maximum:
            self.fail(f"the document holds more than {self.maximum} triples")

    def fresh_blank(self) -> str:
        label = f"_:b{self.counter}"
        self.counter += 1
        return label

    def resolve(self, value: str) -> str:
        if re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", value):
            return iri(value)
        if self.base is None:
            self.fail(f"a relative IRI {value!r} needs a base")
        return iri(resolve_reference(self.base, value))

    def read(self) -> frozenset:
        while True:
            self.skip_space()
            if self.index >= self.length:
                return frozenset(self.triples)
            if not self.directive():
                self.triples_statement()

    def directive(self) -> bool:
        lowered = self.text[self.index:self.index + 7].lower()
        sparql_style = lowered.startswith("prefix") or lowered.startswith("base")
        if not (self.peek() == "@" or sparql_style):
            return False
        if sparql_style and not re.match(r"(?i)(prefix|base)\s", self.text[self.index:self.index + 7]):
            return False
        keyword = re.match(r"@?(prefix|base)", self.text[self.index:], re.IGNORECASE)
        if keyword is None or (self.peek() == "@" and keyword.group(0) not in ("@prefix", "@base")):
            self.fail("unknown directive")
        self.index += len(keyword.group(0))
        self.skip_space()
        if keyword.group(1).lower() == "prefix":
            match = _PREFIX.match(self.text, self.index)
            if not match:
                self.fail("a prefix name is malformed")
            self.index = match.end()
            self.skip_space()
            self.prefixes[match.group(0)[:-1]] = self.resolve(self.iriref())[1:-1]
        else:
            self.base = self.resolve(self.iriref())[1:-1]
        if keyword.group(0).startswith("@"):
            self.skip_space()
            self.expect(".")
        return True

    def triples_statement(self) -> None:
        if self.peek() == "[" and not re.match(r"\[\s*\]", self.text[self.index:self.index + 64]):
            subject = self.blank_property_list()
            self.skip_space()
            if self.peek() != ".":
                self.predicate_object_list(subject)
        else:
            subject = self.subject()
            self.skip_space()
            self.predicate_object_list(subject)
        self.skip_space()
        self.expect(".")

    def subject(self) -> str:
        if self.peek() == "(":
            return self.collection()
        term = self.iri_or_blank()
        if term is None:
            self.fail("expected a subject: an IRI, a blank node or a collection")
        return term

    def predicate_object_list(self, subject: str) -> None:
        while True:
            self.skip_space()
            predicate = self.verb()
            while True:
                self.skip_space()
                self.add(subject, predicate, self.object())
                self.skip_space()
                if self.peek() != ",":
                    break
                self.index += 1
            if self.peek() != ";":
                return
            while self.peek() == ";":
                self.index += 1
                self.skip_space()
            if self.peek() in (".", "]", ""):
                return

    def verb(self) -> str:
        if self.peek() == "a" and (self.index + 1 >= self.length or not re.match(r"[A-Za-z0-9_:.-]", self.peek(2)[1:])):
            self.index += 1
            return RDF_TYPE
        term = self.iri_or_blank(allow_blank=False)
        if term is None:
            self.fail("expected a predicate IRI or 'a'")
        return term

    def iri_or_blank(self, allow_blank: bool = True) -> "str | None":
        if self.peek() == "<":
            return self.resolve(self.iriref())
        if self.peek(2) == "_:":
            if not allow_blank:
                self.fail("a blank node cannot be a predicate")
            label = self.blank_label()
            if label not in self.blanks:
                self.blanks[label] = self.fresh_blank()
            return self.blanks[label]
        if self.peek(2) == "[]" or (self.peek() == "[" and re.match(r"\[\s*\]", self.text[self.index:self.index + 64])):
            if not allow_blank:
                self.fail("a blank node cannot be a predicate")
            self.index = self.text.index("]", self.index) + 1
            return self.fresh_blank()
        return self.prefixed_name()

    def prefixed_name(self) -> "str | None":
        match = _PREFIX.match(self.text, self.index)
        if not match:
            return None
        prefix = match.group(0)[:-1]
        if prefix not in self.prefixes:
            self.fail(f"undeclared prefix {prefix + ':'!r}")
        self.index = match.end()
        local = []
        while self.index < self.length:
            character = self.text[self.index]
            if character == "\\" and self.peek(2)[1:] in _LOCAL_ESCAPABLE and self.peek(2)[1:]:
                local.append(self.text[self.index + 1])
                self.index += 2
            elif character == "%" and re.fullmatch(r"%[0-9A-Fa-f]{2}", self.peek(3)):
                local.append(self.peek(3))
                self.index += 3
            elif character.isalnum() or character in "_-:" or ord(character) > 0x7F:
                local.append(character)
                self.index += 1
            elif character == "." and self.index + 1 < self.length and (
                    self.text[self.index + 1].isalnum() or self.text[self.index + 1] in "_-:%"):
                local.append(character)
                self.index += 1
            else:
                break
        return iri(self.prefixes[prefix] + "".join(local))

    def object(self) -> str:
        character = self.peek()
        if character == "(":
            return self.collection()
        if character == "[" and not re.match(r"\[\s*\]", self.text[self.index:self.index + 64]):
            return self.blank_property_list()
        if character in "\"'":
            return self.rdf_literal()
        number = _NUMBER.match(self.text, self.index)
        if number and (character.isdigit() or character in "+-."):
            self.index = number.end()
            text = number.group(0)
            kind = "double" if re.search("[eE]", text) else "decimal" if "." in text else "integer"
            return literal(text, datatype=XSD + kind)
        for keyword in ("true", "false"):
            if self.text.startswith(keyword, self.index) and not re.match(
                    r"[A-Za-z0-9_:]", self.text[self.index + len(keyword):self.index + len(keyword) + 1]):
                self.index += len(keyword)
                return literal(keyword, datatype=XSD + "boolean")
        term = self.iri_or_blank()
        if term is None:
            self.fail("expected an object")
        return term

    def rdf_literal(self) -> str:
        lexical = self.string()
        if self.peek() == "@":
            return literal(lexical, language=self.language())
        if self.peek(2) == "^^":
            self.index += 2
            datatype = self.iri_or_blank(allow_blank=False)
            if datatype is None:
                self.fail("a datatype must be an IRI")
            return literal(lexical, datatype=datatype[1:-1])
        return literal(lexical)

    def blank_property_list(self) -> str:
        self.expect("[")
        node = self.fresh_blank()
        self.skip_space()
        self.predicate_object_list(node)
        self.skip_space()
        self.expect("]")
        return node

    def collection(self) -> str:
        self.expect("(")
        items = []
        while True:
            self.skip_space()
            if self.peek() == ")":
                self.index += 1
                break
            if self.index >= self.length:
                self.fail("a collection is not closed")
            items.append(self.object())
        if not items:
            return RDF_NIL
        nodes = [self.fresh_blank() for _ in items]
        for position, (node, item) in enumerate(zip(nodes, items)):
            self.add(node, RDF_FIRST, item)
            self.add(node, RDF_REST, nodes[position + 1] if position + 1 < len(nodes) else RDF_NIL)
        return nodes[0]


def parse_turtle(text: str, *, base_iri: "str | None" = None,
                 maximum_triples: int = DEFAULT_MAXIMUM_TRIPLES) -> frozenset:
    """The triples of a Turtle document in the accepted subset, or RdfSyntaxError naming where."""
    if base_iri is not None:
        iri(base_iri)
    return _TurtleReader(text, base_iri, maximum_triples).read()


class _NTriplesReader(_Scanner):
    def term(self, position: str) -> str:
        character = self.peek()
        if character == "<":
            return iri(self.iriref())
        if self.peek(2) == "_:" and position != "predicate":
            return "_:" + self.blank_label()
        if character == '"' and position == "object":
            lexical = self.string()
            if self.peek() == "@":
                return literal(lexical, language=self.language())
            if self.peek(2) == "^^":
                self.index += 2
                return literal(lexical, datatype=self.iriref())
            return literal(lexical)
        self.fail(f"expected an N-Triples {position}")


def parse_ntriples(text: str, *, maximum_triples: int = DEFAULT_MAXIMUM_TRIPLES) -> frozenset:
    """The triples of an N-Triples document, blank node labels kept, literals made canonical."""
    reader, triples = _NTriplesReader(text), set()
    while True:
        reader.skip_space()
        if reader.index >= reader.length:
            return frozenset(triples)
        subject = reader.term("subject")
        reader.skip_space(newlines=False)
        predicate = reader.term("predicate")
        reader.skip_space(newlines=False)
        obj = reader.term("object")
        reader.skip_space(newlines=False)
        reader.expect(".")
        reader.skip_space(newlines=False)
        if reader.index < reader.length and reader.peek() != "\n":
            reader.fail("one triple per line")
        triples.add((subject, predicate, obj))
        if len(triples) > maximum_triples:
            reader.fail(f"the document holds more than {maximum_triples} triples")


def parse_term(text: str, position: str = "object") -> str:
    """One N-Triples term in its canonical spelling."""
    if position not in ("subject", "predicate", "object"):
        raise RdfSyntaxError("a term position is subject, predicate or object")
    reader = _NTriplesReader(text.strip())
    term = reader.term(position)
    if reader.index != reader.length:
        reader.fail("one term only")
    return term


def parse_graph(text: str, format_name: str, *, maximum_triples: int = DEFAULT_MAXIMUM_TRIPLES) -> frozenset:
    """Read a document in one of the two accepted formats."""
    if format_name == "turtle":
        return parse_turtle(text, maximum_triples=maximum_triples)
    if format_name == "ntriples":
        return parse_ntriples(text, maximum_triples=maximum_triples)
    raise RdfSyntaxError(f"unknown format {format_name!r}; turtle or ntriples")
