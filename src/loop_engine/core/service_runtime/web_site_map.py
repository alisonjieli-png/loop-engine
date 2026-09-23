"""The website's site map and its layout standard, read as two typed, versioned records.

Kind: passive typed records with their reader. This module owns two packaged
records and nothing that serves them. `web_site_map.json` beside it is the site
map: every page the website serves (its address, the view that shows it, its
title, its group, the places that link to it or the reason nothing does, its
scroll budget), the header entries in order for a visitor who is signed out, a
signed-in person and an operator, the footer groups and their links, the base
row of the footer, the page each hostname opens, and a dated row for everything
the website removed on purpose. `web_layout_standard.json` holds the measured
rules of `docs/guides/website-design-standards.md`: the widths a check measures
at, the section padding values it allows, the containers, the scroll budget,
the text contrast, the touch target size, the typefaces and the price wording.

Both records are refused here, before any check uses them, when they carry a
record version this reader was not written for, an unknown or a missing field,
a duplicate address, a header or footer link to an address that is not a page,
a page that nothing links to without a written reason, a page that says it is
linked from the header or the footer when that list does not hold it, or a
removal without a date and a reason. `tools/test_website_site_map.py` compares
the site map with the pages the service serves, and
`tools/check_website_layout.mjs` measures the served pages in a browser; both
read the records through `load_site_map` and `load_layout_standard`.

Nothing here serves a page, reads a request or grants authority. The served
address table stays in `web_pages.py`.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re
from typing import Any

SITE_MAP_RECORD_TYPE = "service_web_site_map/v1"
LAYOUT_STANDARD_RECORD_TYPE = "service_web_layout_standard/v1"
#: The packaged files that hold the two records, beside this module.
SITE_MAP_FILE = "web_site_map.json"
LAYOUT_STANDARD_FILE = "web_layout_standard.json"
#: The three header states a page shows: a visitor, a signed-in person and an operator.
HEADER_STATES = ("signed_out", "signed_in", "operator")
#: The places a page can be linked from. A hub page and any other page count as "page".
LINK_PLACES = ("header", "footer", "page")
#: What a header entry is. A button carries no address.
ENTRY_ROLES = ("brand", "link", "button", "primary")
#: What a footer group holds: links only.
FOOTER_ROLES = ("link",)
#: How much scrolling a page may ask for; the pixel values live in the layout standard.
SCROLL_BUDGETS = ("long", "page", "documentation")
#: What a dated removal row can name.
REMOVAL_KINDS = ("page", "header_link", "footer_link", "section")
#: The window sizes the layout standard names: a desktop, a laptop, the widest screen that folds the header
#: into its menu, a phone upright and a phone held sideways.
VIEWPORTS = ("desktop", "laptop", "menu", "phone", "landscape")

_ADDRESS = re.compile(r"^/(?:[a-z0-9]+(?:-[a-z0-9]+)*(?:/[a-z0-9]+(?:-[a-z0-9]+)*)*)?$")
_HREF = re.compile(r"^(/[A-Za-z0-9._/-]*)(?:#([A-Za-z][A-Za-z0-9_-]*))?$")
_TOKEN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
_DATE = re.compile(r"^20[0-9]{2}-[01][0-9]-[0-3][0-9]$")
_HOSTNAME = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*\.[a-z]{2,}$")
_SECTION = re.compile(r"^(?:band|heading):[A-Za-z][A-Za-z0-9_-]*$")


class SiteMapError(ValueError):
    """A site map or layout standard record that this reader refuses, with the reason."""


@dataclass(frozen=True)
class SitePage:
    """One page the website serves, and the one view that shows it."""

    address: str
    view: str
    title: str
    group: str
    linked_from: tuple[str, ...]
    unlinked_reason: str
    scroll_budget: str
    price_in_first_screen: bool


@dataclass(frozen=True)
class NavigationEntry:
    """One entry of the header or of a footer group, in its written order."""

    role: str
    label: str
    href: str | None

    @property
    def path(self) -> str:
        """The address without its fragment, or an empty string for a button."""
        return (self.href or "").split("#", 1)[0]


@dataclass(frozen=True)
class FooterGroup:
    """One named group of footer links."""

    name: str
    links: tuple[NavigationEntry, ...]


@dataclass(frozen=True)
class FooterBaseRow:
    """The last row of the footer: the mark, the operator and the operator's postal line."""

    operator: str
    operator_line: str
    mark: str


@dataclass(frozen=True)
class HostnameSurface:
    """The page a hostname opens at its root address, and the part of it shown first."""

    hostname: str
    address: str
    anchor: str


@dataclass(frozen=True)
class Removal:
    """A dated row for something the website removed on purpose, with the reason."""

    date: str
    kind: str
    state: str
    subject: str
    reason: str
    decided_by: str


@dataclass(frozen=True)
class SiteMap:
    """The whole site map record."""

    record_type: str
    decided_on: str
    decided_by: str
    display_name: str
    canonical_hostname: str
    groups: tuple[str, ...]
    pages: tuple[SitePage, ...]
    header: dict
    footer_brand: str
    footer_groups: tuple[FooterGroup, ...]
    footer_base_row: FooterBaseRow
    hostnames: tuple[HostnameSurface, ...]
    removed: tuple[Removal, ...]

    def page(self, address: str) -> SitePage | None:
        """The page at an exact address, or None."""
        return next((page for page in self.pages if page.address == address), None)

    def header_paths(self) -> dict:
        """The addresses each header state links to, without fragments."""
        return {state: {entry.path for entry in entries if entry.href} for state, entries in self.header.items()}

    def footer_paths(self) -> set:
        """Every address the footer groups and the footer brand link to, without fragments."""
        return {link.path for group in self.footer_groups for link in group.links} | {self.footer_brand}


@dataclass(frozen=True)
class Viewport:
    """One window size a check measures at."""

    width: int
    height: int


@dataclass(frozen=True)
class LayoutStandard:
    """The measured rules of the website design standards."""

    record_type: str
    decided_on: str
    decided_by: str
    viewports: dict
    header_one_row_widths: tuple[int, ...]
    header_menu_widths: tuple[int, ...]
    header_landscape_max_px: int
    section_padding_px: dict
    containers_px: dict
    shared_edge_tolerance_px: int
    empty_vertical_run_max_px: int
    page_height_max_px: dict
    phone_screens_factor: int
    contents_list_after_px: int
    text_contrast_min: float
    tap_target_min_px: int
    font_families: tuple[str, ...]
    primary_actions_per_view_max: int
    dark_bands_per_view_max: int
    line_characters_max: int
    price: dict


def _fields(value: Any, where: str, required: tuple[str, ...]) -> dict:
    """An object with exactly the named fields, or a refusal naming the difference."""
    if not isinstance(value, dict):
        raise SiteMapError(f"{where} must be an object")
    missing, unknown = sorted(set(required) - set(value)), sorted(set(value) - set(required))
    if missing or unknown:
        raise SiteMapError(f"{where} has missing fields {missing} and unknown fields {unknown}")
    return value


def _text(value: Any, where: str, pattern: re.Pattern | None = None, empty: bool = False) -> str:
    """A string, nonempty unless allowed, that matches the pattern when one is given."""
    if not isinstance(value, str) or (not empty and not value.strip()) or value != value.strip():
        raise SiteMapError(f"{where} must be a trimmed{' ' if empty else ' nonempty '}string")
    if pattern is not None and value and not pattern.fullmatch(value):
        raise SiteMapError(f"{where} is not in the required form: {value!r}")
    return value


def _list(value: Any, where: str, empty: bool = False) -> list:
    if not isinstance(value, list) or (not empty and not value):
        raise SiteMapError(f"{where} must be a{'' if empty else ' nonempty'} list")
    return value


def _unique(values: list, where: str) -> None:
    repeated = sorted({value for value in values if values.count(value) > 1})
    if repeated:
        raise SiteMapError(f"{where} repeats {repeated}")


def _page(value: Any, where: str, groups: tuple[str, ...]) -> SitePage:
    row = _fields(value, where, ("address", "view", "title", "group", "linked_from", "unlinked_reason",
                                 "scroll_budget", "price_in_first_screen"))
    address = _text(row["address"], where + ".address", _ADDRESS)
    places = tuple(_text(place, where + ".linked_from", None) for place in _list(row["linked_from"], where + ".linked_from", True))
    if any(place not in LINK_PLACES for place in places):
        raise SiteMapError(f"{where}.linked_from may name only {LINK_PLACES}")
    _unique(list(places), where + ".linked_from")
    reason = _text(row["unlinked_reason"], where + ".unlinked_reason", empty=True)
    if bool(places) == bool(reason):
        raise SiteMapError(f"{where} needs either places that link to it or a reason that nothing does, and not both")
    if row["group"] not in groups:
        raise SiteMapError(f"{where}.group must be one of {groups}")
    if row["scroll_budget"] not in SCROLL_BUDGETS:
        raise SiteMapError(f"{where}.scroll_budget must be one of {SCROLL_BUDGETS}")
    if not isinstance(row["price_in_first_screen"], bool):
        raise SiteMapError(f"{where}.price_in_first_screen must be true or false")
    return SitePage(address, _text(row["view"], where + ".view", _TOKEN), _text(row["title"], where + ".title"),
                    row["group"], places, reason, row["scroll_budget"], row["price_in_first_screen"])


def _entry(value: Any, where: str) -> NavigationEntry:
    row = _fields(value, where, ("role", "label", "href"))
    if row["role"] not in ENTRY_ROLES:
        raise SiteMapError(f"{where}.role must be one of {ENTRY_ROLES}")
    if (row["role"] == "button") != (row["href"] is None):
        raise SiteMapError(f"{where}: a button carries no address and every other entry carries one")
    href = None if row["href"] is None else _text(row["href"], where + ".href", _HREF)
    return NavigationEntry(row["role"], _text(row["label"], where + ".label"), href)


def _header(value: Any, where: str) -> dict:
    row = _fields(value, where, HEADER_STATES)
    header = {}
    for state in HEADER_STATES:
        entries = tuple(_entry(item, f"{where}.{state}[{index}]")
                        for index, item in enumerate(_list(row[state], f"{where}.{state}")))
        roles = [entry.role for entry in entries]
        if roles[0] != "brand" or roles.count("brand") != 1 or roles.count("primary") > 1:
            raise SiteMapError(f"{where}.{state} opens with the one brand entry and holds at most one primary action")
        _unique([entry.href for entry in entries if entry.href], f"{where}.{state} addresses")
        header[state] = entries
    return header


def _footer(value: Any, where: str) -> tuple:
    row = _fields(value, where, ("brand_href", "groups", "base_row"))
    groups = []
    for index, item in enumerate(_list(row["groups"], where + ".groups")):
        group = _fields(item, f"{where}.groups[{index}]", ("name", "links"))
        links = tuple(_entry(link, f"{where}.groups[{index}].links[{number}]")
                      for number, link in enumerate(_list(group["links"], f"{where}.groups[{index}].links")))
        if any(link.role not in FOOTER_ROLES for link in links):
            raise SiteMapError(f"{where}.groups[{index}] holds links only")
        groups.append(FooterGroup(_text(group["name"], f"{where}.groups[{index}].name"), links))
    _unique([group.name for group in groups], where + ".groups")
    _unique([link.href for group in groups for link in group.links], where + " addresses")
    base = _fields(row["base_row"], where + ".base_row", ("operator", "operator_line", "mark"))
    base_row = FooterBaseRow(_text(base["operator"], where + ".base_row.operator"),
                             _text(base["operator_line"], where + ".base_row.operator_line"),
                             _text(base["mark"], where + ".base_row.mark", _HREF))
    return _text(row["brand_href"], where + ".brand_href", _ADDRESS), tuple(groups), base_row


def _removal(value: Any, where: str) -> Removal:
    row = _fields(value, where, ("date", "kind", "state", "subject", "reason", "decided_by"))
    if row["kind"] not in REMOVAL_KINDS:
        raise SiteMapError(f"{where}.kind must be one of {REMOVAL_KINDS}")
    state = _text(row["state"], where + ".state", empty=True)
    if (row["kind"] == "header_link") != (state in HEADER_STATES):
        raise SiteMapError(f"{where}: a header link names one of {HEADER_STATES}, and nothing else names a state")
    subject = _text(row["subject"], where + ".subject", _SECTION if row["kind"] == "section" else None)
    if row["kind"] != "section" and not (_HREF.fullmatch(subject) or subject.startswith("button:")):
        raise SiteMapError(f"{where}.subject must be an address, or button:<label> for a header button")
    return Removal(_text(row["date"], where + ".date", _DATE), row["kind"], state, subject,
                   _text(row["reason"], where + ".reason"), _text(row["decided_by"], where + ".decided_by"))


def _consistency(site_map: SiteMap) -> None:
    """Every link names a page, and every page's declared places agree with the lists that hold it."""
    addresses = {page.address for page in site_map.pages}
    header_paths, footer_paths = site_map.header_paths(), site_map.footer_paths()
    linked = set().union(*header_paths.values()) | footer_paths
    strays = sorted(path for path in linked if path not in addresses and not path.startswith("/assets/"))
    if strays:
        raise SiteMapError(f"the header or footer links to addresses that are not pages: {strays}")
    for page in site_map.pages:
        in_header = any(page.address in paths for paths in header_paths.values())
        in_footer = page.address in footer_paths
        if ("header" in page.linked_from) != in_header or ("footer" in page.linked_from) != in_footer:
            raise SiteMapError(f"page {page.address} says it is linked from {list(page.linked_from)}, "
                               f"and the header {'holds' if in_header else 'does not hold'} it and the footer "
                               f"{'holds' if in_footer else 'does not hold'} it")
    for surface in site_map.hostnames:
        if surface.address not in addresses:
            raise SiteMapError(f"hostname {surface.hostname} opens {surface.address}, which is not a page")


def site_map_from_record(record: Any) -> SiteMap:
    """Read a site map record, or refuse it with the reason."""
    row = _fields(record, "site map", ("record_type", "decided_on", "decided_by", "display_name", "canonical_hostname",
                                       "groups", "pages", "header", "footer", "hostnames", "removed"))
    if row["record_type"] != SITE_MAP_RECORD_TYPE:
        raise SiteMapError(f"this reader reads {SITE_MAP_RECORD_TYPE}, not {row['record_type']!r}")
    groups = tuple(_text(name, "site map.groups") for name in _list(row["groups"], "site map.groups"))
    _unique(list(groups), "site map.groups")
    pages = tuple(_page(item, f"site map.pages[{index}]", groups) for index, item in enumerate(_list(row["pages"], "site map.pages")))
    _unique([page.address for page in pages], "site map.pages addresses")
    if not any(page.address == "/" for page in pages):
        raise SiteMapError("the site map needs the homepage at /")
    footer_brand, footer_groups, base_row = _footer(row["footer"], "site map.footer")
    hostnames = []
    for index, item in enumerate(_list(row["hostnames"], "site map.hostnames", True)):
        surface = _fields(item, f"site map.hostnames[{index}]", ("hostname", "address", "anchor"))
        hostnames.append(HostnameSurface(_text(surface["hostname"], f"site map.hostnames[{index}].hostname", _HOSTNAME),
                                         _text(surface["address"], f"site map.hostnames[{index}].address", _ADDRESS),
                                         _text(surface["anchor"], f"site map.hostnames[{index}].anchor", _TOKEN, empty=True)))
    _unique([surface.hostname for surface in hostnames], "site map.hostnames")
    removed = tuple(_removal(item, f"site map.removed[{index}]") for index, item in enumerate(_list(row["removed"], "site map.removed", True)))
    site_map = SiteMap(SITE_MAP_RECORD_TYPE, _text(row["decided_on"], "site map.decided_on", _DATE),
                       _text(row["decided_by"], "site map.decided_by"), _text(row["display_name"], "site map.display_name"),
                       _text(row["canonical_hostname"], "site map.canonical_hostname", _HOSTNAME), groups, pages,
                       _header(row["header"], "site map.header"), footer_brand, footer_groups, base_row,
                       tuple(hostnames), removed)
    _consistency(site_map)
    return site_map


def _whole(value: Any, where: str, low: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < low:
        raise SiteMapError(f"{where} must be a whole number of at least {low}")
    return value


def _widths(value: Any, where: str) -> tuple[int, ...]:
    widths = tuple(_whole(item, where, 1) for item in _list(value, where))
    _unique(list(widths), where)
    return widths


def layout_standard_from_record(record: Any) -> LayoutStandard:
    """Read a layout standard record, or refuse it with the reason."""
    names = ("record_type", "decided_on", "decided_by", "viewports", "header_one_row_widths", "header_menu_widths",
             "header_landscape_max_px", "section_padding_px", "containers_px", "shared_edge_tolerance_px", "empty_vertical_run_max_px",
             "page_height_max_px", "phone_screens_factor", "contents_list_after_px", "text_contrast_min",
             "tap_target_min_px", "font_families", "primary_actions_per_view_max", "dark_bands_per_view_max",
             "line_characters_max", "price")
    row = _fields(record, "layout standard", names)
    if row["record_type"] != LAYOUT_STANDARD_RECORD_TYPE:
        raise SiteMapError(f"this reader reads {LAYOUT_STANDARD_RECORD_TYPE}, not {row['record_type']!r}")
    viewports = {}
    for name, item in _fields(row["viewports"], "layout standard.viewports", VIEWPORTS).items():
        size = _fields(item, f"layout standard.viewports.{name}", ("width", "height"))
        viewports[name] = Viewport(_whole(size["width"], name, 1), _whole(size["height"], name, 1))
    padding = {}
    for name, values in _fields(row["section_padding_px"], "layout standard.section_padding_px", ("desktop", "phone")).items():
        allowed = tuple(_whole(value, f"section padding {name}") for value in _list(values, f"section padding {name}"))
        _unique(list(allowed), f"section padding {name}")
        if 0 not in allowed:
            raise SiteMapError("a section without padding of its own is always allowed, so 0 is in each list")
        padding[name] = tuple(sorted(allowed))
    containers = _fields(row["containers_px"], "layout standard.containers_px",
                         ("content_max", "reading_max", "lead_max", "desktop_edge", "phone_edge"))
    heights = _fields(row["page_height_max_px"], "layout standard.page_height_max_px", ("long", "page"))
    contrast = row["text_contrast_min"]
    if not isinstance(contrast, (int, float)) or isinstance(contrast, bool) or not 1 < contrast <= 21:
        raise SiteMapError("layout standard.text_contrast_min is a ratio above 1 and at most 21")
    price = _fields(row["price"], "layout standard.price", ("marker", "phrase", "refused_phrases"))
    if not _text(price["phrase"], "price.phrase").startswith(_text(price["marker"], "price.marker")):
        raise SiteMapError("the price phrase starts with the price marker")
    fonts = tuple(_text(name, "layout standard.font_families") for name in _list(row["font_families"], "font families"))
    return LayoutStandard(
        LAYOUT_STANDARD_RECORD_TYPE, _text(row["decided_on"], "layout standard.decided_on", _DATE),
        _text(row["decided_by"], "layout standard.decided_by"), viewports,
        _widths(row["header_one_row_widths"], "header_one_row_widths"),
        _widths(row["header_menu_widths"], "header_menu_widths"),
        _whole(row["header_landscape_max_px"], "header_landscape_max_px", 1), padding,
        {name: _whole(value, name, 1) for name, value in containers.items()},
        _whole(row["shared_edge_tolerance_px"], "shared_edge_tolerance_px"),
        _whole(row["empty_vertical_run_max_px"], "empty_vertical_run_max_px", 1),
        {name: _whole(value, name, 1) for name, value in heights.items()},
        _whole(row["phone_screens_factor"], "phone_screens_factor", 1),
        _whole(row["contents_list_after_px"], "contents_list_after_px", 1), float(contrast),
        _whole(row["tap_target_min_px"], "tap_target_min_px", 1), fonts,
        _whole(row["primary_actions_per_view_max"], "primary_actions_per_view_max", 1),
        _whole(row["dark_bands_per_view_max"], "dark_bands_per_view_max"),
        _whole(row["line_characters_max"], "line_characters_max", 1),
        {"marker": price["marker"], "phrase": price["phrase"],
         "refused_phrases": tuple(_text(item, "price.refused_phrases") for item in _list(price["refused_phrases"], "refused"))})


def _packaged_record(name: str) -> Any:
    from importlib.resources import files
    return json.loads(files(__package__).joinpath(name).read_text(encoding="utf-8"))


def load_site_map() -> SiteMap:
    """The packaged site map, read and checked."""
    return site_map_from_record(_packaged_record(SITE_MAP_FILE))


def load_layout_standard() -> LayoutStandard:
    """The packaged layout standard, read and checked."""
    return layout_standard_from_record(_packaged_record(LAYOUT_STANDARD_FILE))


def as_plain_record(value: SiteMap | LayoutStandard) -> dict:
    """The checked record as plain JSON values, for a check written in another language."""
    return json.loads(json.dumps(asdict(value)))
