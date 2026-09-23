"""The attribute schema of a catalogue release, declared as data.

An operator adds a searchable, filterable or displayed detail to the library
by publishing a release whose schema names it. A new attribute of an existing
type is a data change and needs no code, the way a search index setting names
its searchable, filterable and displayed attributes. A new type is code.

```text
catalogue_attribute_schema/v1
└── attribute
    ├── name        lower case words joined by underscores
    ├── type        text, keyword, choice (with its allowed values), number, date, keyword_list
    ├── searchable  its words enter the full-text index
    ├── filterable  a request may filter on it
    ├── sortable    recorded for ordered browsing; no route sorts on it yet
    ├── shown       returned with a search result
    └── visibility  public, or internal: stored, never searched, filtered or shown
```

Attributes are descriptive only. Effects, the licence, permissions, grants,
approval and review state stay the existing typed fields of an item, so an
attribute may never carry one of their names, and no code that decides access
reads an attribute. A value that is not declared, has the wrong type or names
a choice the schema does not list is refused before a release is published.
"""
from __future__ import annotations

from dataclasses import dataclass
import datetime
import hashlib
import json
import math
import re

from .records import ServiceRuntimeError

SCHEMA_RECORD_TYPE = "catalogue_attribute_schema/v1"
ATTRIBUTE_TYPES = ("text", "keyword", "choice", "number", "date", "keyword_list")
TEXT, KEYWORD, CHOICE, NUMBER, DATE, KEYWORD_LIST = ATTRIBUTE_TYPES
VISIBILITIES = ("public", "internal")
PUBLIC, INTERNAL = VISIBILITIES
SEARCHABLE_TYPES = (TEXT, KEYWORD, CHOICE, KEYWORD_LIST)
FILTERABLE_TYPES = (KEYWORD, CHOICE, NUMBER, DATE, KEYWORD_LIST)
SORTABLE_TYPES = (KEYWORD, CHOICE, NUMBER, DATE)
RANGE_TYPES = (NUMBER, DATE)
MAXIMUM_ATTRIBUTES = 64
MAXIMUM_CHOICES = 64
MAXIMUM_LIST_VALUES = 50
MAXIMUM_TEXT_CHARACTERS = 2000
MAXIMUM_KEYWORD_CHARACTERS = 120
MAXIMUM_FILTERS = 8
MAXIMUM_NUMBER = 1e15
FILTER_OPERATORS = ("equals", "any_of", "at_least", "at_most")
_NAME = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+){0,5}")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
#: The typed fields of an item. An attribute never takes one of these names.
RESERVED_NAMES = frozenset((
    "identity", "kind", "purpose", "digest", "source_layer", "source_ref", "family", "size_bytes",
    "license", "licence", "license_name", "declared_effects", "effects", "styles", "harness_styles",
    "tags", "exposure", "availability", "body_included", "body_allowed", "body_form", "files",
    "package", "approval", "approval_ref", "qualification_basis", "metering", "metering_policy",
    "reference", "score", "modes", "attributes", "release", "record_type"))
#: A word that begins with one of these stems names authority, not a
#: description. `network_effects`, `licence_state` and `review_passed` are all
#: refused, so no attribute can look like a typed permission to a reader.
RESERVED_STEMS = ("effect", "licen", "permi", "grant", "approv", "review", "scope", "entitle",
                  "withdraw", "qualif", "meter", "secret", "credential", "token", "password",
                  "digest", "authori", "allow", "deny", "denial", "access")


def _refuse(code, message):
    raise ServiceRuntimeError(code, message)


def _flag(value, name):
    if type(value) is not bool:
        _refuse("attribute_schema_invalid", f"{name} is an explicit Boolean")
    return value


def _bounded_text(value, limit):
    return (isinstance(value, str) and value == value.strip() and 0 < len(value) <= limit
            and all(character.isprintable() for character in value))


def attribute_name_refusal(name):
    """Empty text when a name may be declared, otherwise the refusal code."""
    if not isinstance(name, str) or not _NAME.fullmatch(name) or len(name) > 48:
        return "attribute_name_invalid"
    if name in RESERVED_NAMES or any(word.startswith(RESERVED_STEMS) for word in name.split("_")):
        return "attribute_name_reserved"
    return ""


@dataclass(frozen=True)
class CatalogueAttribute:
    """One declared detail of the items in a release."""

    name: str
    type: str
    searchable: bool = False
    filterable: bool = False
    sortable: bool = False
    shown: bool = False
    visibility: str = PUBLIC
    choices: tuple = ()
    description: str = ""

    def __post_init__(self):
        refusal = attribute_name_refusal(self.name)
        if refusal:
            _refuse(refusal, "an attribute name is lower case words and never names a typed field or authority")
        if self.type not in ATTRIBUTE_TYPES:
            _refuse("attribute_schema_invalid", f"an attribute type is one of {ATTRIBUTE_TYPES}; a new type is code")
        for name in ("searchable", "filterable", "sortable", "shown"):
            _flag(getattr(self, name), name)
        if self.visibility not in VISIBILITIES:
            _refuse("attribute_schema_invalid", f"visibility is one of {VISIBILITIES}")
        if self.visibility == INTERNAL and (self.searchable or self.filterable or self.sortable or self.shown):
            # A searchable or filterable internal value could be probed one
            # request at a time, so internal means stored and nothing else.
            _refuse("attribute_schema_invalid", "an internal attribute is never searched, filtered, sorted or shown")
        if self.searchable and self.type not in SEARCHABLE_TYPES:
            _refuse("attribute_schema_invalid", f"a searchable attribute is one of {SEARCHABLE_TYPES}")
        if self.filterable and self.type not in FILTERABLE_TYPES:
            _refuse("attribute_schema_invalid", f"a filterable attribute is one of {FILTERABLE_TYPES}")
        if self.sortable and self.type not in SORTABLE_TYPES:
            _refuse("attribute_schema_invalid", f"a sortable attribute is one of {SORTABLE_TYPES}")
        choices = tuple(self.choices) if isinstance(self.choices, (tuple, list)) else None
        if choices is None or (self.type == CHOICE) != bool(choices):
            _refuse("attribute_schema_invalid", "a choice attribute lists its allowed values; no other type does")
        if (len(choices) > MAXIMUM_CHOICES or len(set(choices)) != len(choices)
                or any(not _bounded_text(value, MAXIMUM_KEYWORD_CHARACTERS) for value in choices)):
            _refuse("attribute_schema_invalid", "choices are distinct bounded printable values")
        object.__setattr__(self, "choices", choices)
        if not isinstance(self.description, str) or len(self.description) > 400:
            _refuse("attribute_schema_invalid", "a description is bounded text")

    def to_dict(self):
        return {"name": self.name, "type": self.type, "searchable": self.searchable,
                "filterable": self.filterable, "sortable": self.sortable, "shown": self.shown,
                "visibility": self.visibility, "choices": list(self.choices), "description": self.description}

    @classmethod
    def from_dict(cls, value):
        allowed = {"name", "type", "searchable", "filterable", "sortable", "shown", "visibility", "choices",
                   "description"}
        if not isinstance(value, dict) or not {"name", "type"} <= set(value) or set(value) - allowed:
            _refuse("attribute_schema_invalid", "an attribute declares its name and type and only the known flags")
        return cls(**value)

    def value(self, raw):
        """Return the normalized value of this attribute, or refuse it."""
        kind = self.type
        if kind == TEXT and _bounded_text(raw, MAXIMUM_TEXT_CHARACTERS):
            return raw
        if kind == KEYWORD and _bounded_text(raw, MAXIMUM_KEYWORD_CHARACTERS):
            return raw
        if kind == CHOICE and isinstance(raw, str) and raw in self.choices:
            return raw
        if (kind == NUMBER and type(raw) in (int, float) and math.isfinite(raw)
                and abs(raw) <= MAXIMUM_NUMBER):
            return raw
        if kind == DATE and isinstance(raw, str) and _DATE.fullmatch(raw):
            try:
                datetime.date.fromisoformat(raw)
                return raw
            except ValueError:
                pass
        if (kind == KEYWORD_LIST and isinstance(raw, list) and 0 < len(raw) <= MAXIMUM_LIST_VALUES
                and len(set(map(str, raw))) == len(raw)
                and all(_bounded_text(item, MAXIMUM_KEYWORD_CHARACTERS) for item in raw)):
            return list(raw)
        _refuse("attribute_value_invalid", f"the value of {self.name} is not a valid {kind}")


@dataclass(frozen=True)
class CatalogueAttributeSchema:
    """The attributes one release declares, identified by the digest of its canonical form."""

    attributes: tuple = ()
    record_type: str = SCHEMA_RECORD_TYPE

    def __post_init__(self):
        if self.record_type != SCHEMA_RECORD_TYPE:
            _refuse("attribute_schema_unsupported", f"this release reads {SCHEMA_RECORD_TYPE} only")
        attributes = tuple(self.attributes)
        if len(attributes) > MAXIMUM_ATTRIBUTES or any(not isinstance(item, CatalogueAttribute) for item in attributes):
            _refuse("attribute_schema_invalid", f"a schema declares at most {MAXIMUM_ATTRIBUTES} typed attributes")
        names = [item.name for item in attributes]
        if len(set(names)) != len(names):
            _refuse("attribute_schema_invalid", "each attribute is declared once")
        object.__setattr__(self, "attributes", tuple(sorted(attributes, key=lambda item: item.name)))
        object.__setattr__(self, "_by_name", {item.name: item for item in attributes})

    def to_dict(self):
        return {"record_type": self.record_type, "attributes": [item.to_dict() for item in self.attributes]}

    @classmethod
    def from_dict(cls, value):
        if (not isinstance(value, dict) or set(value) != {"record_type", "attributes"}
                or not isinstance(value["attributes"], list)):
            _refuse("attribute_schema_invalid", "a schema names its record version and its attributes only")
        if value["record_type"] != SCHEMA_RECORD_TYPE:
            _refuse("attribute_schema_unsupported", f"this release reads {SCHEMA_RECORD_TYPE} only")
        return cls(tuple(CatalogueAttribute.from_dict(item) for item in value["attributes"]))

    @property
    def digest(self):
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"),
                                         ensure_ascii=False).encode("utf-8")).hexdigest()

    def attribute(self, name):
        return self._by_name.get(name)

    def validate_values(self, values):
        """Return one item's attribute values in canonical order, or refuse the first fault."""
        if not isinstance(values, dict) or len(values) > MAXIMUM_ATTRIBUTES:
            _refuse("attribute_value_invalid", "attribute values are a bounded mapping")
        normalized = {}
        for name in sorted(values):
            declared = self._by_name.get(name)
            if declared is None:
                _refuse("attribute_not_declared", "an item names an attribute its release schema does not declare")
            normalized[name] = declared.value(values[name])
        return normalized

    def search_text(self, values):
        """The words of the searchable public attributes, in schema order."""
        words = []
        for item in self.attributes:
            if item.searchable and item.name in values:
                value = values[item.name]
                words.extend(value if isinstance(value, list) else [str(value)])
        return " ".join(words)

    def shown_values(self, values):
        return {item.name: values[item.name] for item in self.attributes
                if item.shown and item.visibility == PUBLIC and item.name in values}

    def filter_request(self, filters):
        """Return a request's filters as typed conditions, or refuse before anything is ranked.

        A filter names a declared, filterable, public attribute. An undeclared
        or internal attribute is refused with its own code, so a caller cannot
        learn an internal value by filtering on it.
        """
        if filters is None:
            return ()
        if not isinstance(filters, dict) or len(filters) > MAXIMUM_FILTERS:
            _refuse("search_filter_invalid", f"filters are a mapping of at most {MAXIMUM_FILTERS} attributes")
        conditions = []
        for name in sorted(filters):
            declared = self._by_name.get(name) if isinstance(name, str) else None
            if not filter_permitted(declared):
                _refuse("search_filter_not_allowed",
                        "a filter names a declared, filterable, public attribute of the active release")
            condition = filters[name]
            if (not isinstance(condition, dict) or not condition or set(condition) - set(FILTER_OPERATORS)
                    or ("equals" in condition and len(condition) != 1)
                    or ("any_of" in condition and len(condition) != 1)
                    or (({"at_least", "at_most"} & set(condition)) and declared.type not in RANGE_TYPES)):
                _refuse("search_filter_invalid", "a filter uses equals, any_of, or at_least and at_most on a number or date")
            scalar = CatalogueAttribute(declared.name, KEYWORD) if declared.type == KEYWORD_LIST else declared
            if "any_of" in condition:
                wanted = condition["any_of"]
                if not isinstance(wanted, list) or not 0 < len(wanted) <= MAXIMUM_LIST_VALUES:
                    _refuse("search_filter_invalid", "any_of lists one to fifty values")
                conditions.append((name, "any_of", tuple(scalar.value(value) for value in wanted)))
            elif "equals" in condition:
                conditions.append((name, "any_of", (scalar.value(condition["equals"]),)))
            else:
                low = scalar.value(condition["at_least"]) if "at_least" in condition else None
                high = scalar.value(condition["at_most"]) if "at_most" in condition else None
                conditions.append((name, "range", (low, high)))
        return tuple(conditions)


def filter_permitted(declared):
    """A request may filter only on a declared, filterable, public attribute."""
    return declared is not None and declared.visibility == PUBLIC and declared.filterable


EMPTY_SCHEMA = CatalogueAttributeSchema(())
