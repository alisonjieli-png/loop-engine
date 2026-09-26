"""Real loopback checks of the paged list (roadmap S-6.203, its paged listing part).

Each check runs against the real application over a loopback socket, and each
guard it depends on is removed once, in memory, by a known-wrong control that
must make the same check fail. No provider is contacted and nothing is written
outside the temporary folder the suite gives.

```text
Paged list checks
├── a walk returns every offered item exactly once, in the whole list's order
├── a page never exceeds the answer cap, over the web address and the protocol tool
├── a list too large for the cap names page_size in its refusal
├── a cursor of another release, and a cursor after a grant change, are refused as list_release_changed
├── a tampered, foreign or other-filter cursor is refused as list_cursor_invalid
├── a page size outside its bounds is refused as list_page_size_invalid
└── the first page names at most MAXIMUM_WITHHELD_ROWS held-back items; every page counts them
```
"""
from __future__ import annotations

import asyncio
from dataclasses import replace
import hmac
from types import SimpleNamespace
from unittest.mock import patch

from ..harness_intelligence import HarnessIntelligenceDraft, item_from_body
from ..provisioning_server import ProvisioningGrant, ProvisioningItemBinding
from . import list_paging
from .http_test_fixtures import HttpDomainFixture, running_http

V2 = "service_provisioning_request/v2"
PATH = "/api/v1/provisioning"
#: Small enough that a page of the large rows below holds a handful of them, and large enough that the protocol
#: endpoint, which sends a page twice, still fits one.
SMALL_CAP = 12_000
#: The bound as released, read before any known-wrong control can change it.
WITHHELD_BOUND = list_paging.MAXIMUM_WITHHELD_ROWS


def _fixture(root, *, offered, withheld, purpose_characters):
    """The shared fixture's two tenants, plus `offered` items and `withheld` items that declare running a process."""
    fixture = HttpDomainFixture(root)
    added = []
    for index in range(offered + withheld):
        identity = f"paged.item.{index:05d}"
        purpose = (f"Paged item {index}: " + "a description long enough to matter " * 200)[:purpose_characters]
        effects = ("spawns_process",) if index >= offered else ()
        body = "PAGED BODY " + identity
        item = item_from_body(HarnessIntelligenceDraft(identity, "skill", purpose, "context_intelligence",
                                                       "fixture:" + identity + "/v1", "MIT", effects), body)
        fixture.catalogue.register(item)
        fixture.bodies[identity] = body
        fixture.bindings[identity] = ProvisioningItemBinding.from_item(item)
        added.append(identity)
    fixture.runtime.set_grants("alpha", tuple(ProvisioningGrant("alpha", fixture.bindings[identity], True)
                                              for identity in ("skill.alpha", "skill.large", *added)))
    return fixture


def _fresh_view(fixture, release_id):
    """A new served view of the same catalogue under `release_id`, as a catalogue release installs one."""
    fixture.provisioning.install_view(replace(fixture.provisioning.current_view(), release_id=release_id, _lazy={}))


def _post(client, base, fixture, body, tenant="alpha"):
    answer = client.post(base + PATH, headers=fixture.headers(tenant), json=body)
    value = answer.json()
    return answer, value.get("result") if answer.status_code == 200 else value.get("error")


def _walk(client, base, fixture, page_size, **fields):
    """Every page of one list, or the refusal that stopped it: (pages, sizes, refusal)."""
    pages, sizes, cursor = [], [], None
    while len(pages) < 500:
        body = {"record_type": V2, "operation": "list", "page_size": page_size, **fields}
        if cursor is not None:
            body["cursor"] = cursor
        answer, value = _post(client, base, fixture, body)
        if answer.status_code != 200:
            return pages, sizes, value
        pages.append(value)
        sizes.append(len(answer.content))
        cursor = value["next_cursor"]
        if cursor is None:
            return pages, sizes, None
    return pages, sizes, {"code": "walk_did_not_end"}


def _whole(client, base, fixture, **fields):
    _answer, value = _post(client, base, fixture, {"record_type": V2, "operation": "list", **fields})
    return value


def _offered_identities(fixture):
    """The account's whole list, asked of the provisioning boundary in this process, as the service asks it."""
    from .catalogue_tiers import DEFAULT_LIBRARY_SETTINGS, narrowed
    principal = fixture.runtime.authenticate_key(fixture.keys["alpha"].key)
    answer = fixture.provisioning.invoke_for_principal(principal, "list", authority_effects=("reads_fs",),
                                                       community_items=narrowed(DEFAULT_LIBRARY_SETTINGS, None))
    return [row["identity"] for row in answer["items"]]


def _exactly_once(client, base, fixture, page_size):
    """Every offered item once, in the whole list's order; where the whole list fits one answer, the same rows."""
    expected = _offered_identities(fixture)
    whole_answer, whole = _post(client, base, fixture, {"record_type": V2, "operation": "list"})
    pages, _sizes, refusal = _walk(client, base, fixture, page_size)
    rows = [row for page in pages for row in page["items"]]
    return (refusal is None and bool(expected) and [row["identity"] for row in rows] == expected
            and (whole_answer.status_code != 200 or rows == whole["items"])
            and all(page["record_type"] == list_paging.LIST_PAGE_RECORD_TYPE
                    and page["total_offered"] == len(expected) and len(page["items"]) <= page_size
                    for page in pages)
            and pages[-1]["next_cursor"] is None and len(pages) > 1)


def _fits_the_cap(client, base, fixture):
    """A walk under a small cap: every answer at most the cap, every item once, pages cut by bytes not rows."""
    whole_answer, whole = _post(client, base, fixture, {"record_type": V2, "operation": "list"})
    pages, sizes, refusal = _walk(client, base, fixture, list_paging.MAXIMUM_LIST_PAGE_SIZE)
    rows = [row["identity"] for page in pages for row in page["items"]]
    return (whole_answer.status_code == 413 and refusal is None and bool(sizes) and max(sizes) <= SMALL_CAP
            and len(pages) > 2 and len(rows) == len(set(rows)) == pages[0]["total_offered"])


async def _protocol_fits_the_cap(base, fixture):
    from .protocol_checks import _protocol_client
    identities, sizes, cursor = [], [], None
    async with _protocol_client(base, fixture, "legacy") as client:
        while len(sizes) < 500:
            arguments = {"page_size": list_paging.MAXIMUM_LIST_PAGE_SIZE, **({"cursor": cursor} if cursor else {})}
            result = await client.call_tool("provisioning_list", arguments)
            if result.is_error:
                return False
            sizes.append(len(result.model_dump_json(by_alias=True).encode("utf-8")))
            page = result.structured_content["result"]
            identities += [row["identity"] for row in page["items"]]
            cursor = page["next_cursor"]
            if cursor is None:
                break
    return len(sizes) > 2 and max(sizes) <= SMALL_CAP and len(identities) == len(set(identities)) == page["total_offered"]


def _unpaged_names_page_size(client, base, fixture):
    answer, error = _post(client, base, fixture, {"record_type": V2, "operation": "list"})
    return answer.status_code == 413 and error["code"] == "response_limit_exceeded" and "page_size" in error["next_action"]


def _release_change_refused(client, base, fixture):
    _fresh_view(fixture, "release-one")
    _answer, first = _post(client, base, fixture, {"record_type": V2, "operation": "list", "page_size": 5})
    _fresh_view(fixture, "release-two")
    answer, error = _post(client, base, fixture, {"record_type": V2, "operation": "list", "page_size": 5,
                                                  "cursor": first["next_cursor"]})
    again, restarted = _post(client, base, fixture, {"record_type": V2, "operation": "list", "page_size": 5})
    return (first["catalogue_release"] == "release-one" and answer.status_code == 409
            and error["code"] == "list_release_changed" and "first page" in error["next_action"]
            and again.status_code == 200 and restarted["catalogue_release"] == "release-two")


def _grant_change_refused(client, base, fixture):
    _fresh_view(fixture, "release-grants")
    _answer, first = _post(client, base, fixture, {"record_type": V2, "operation": "list", "page_size": 5})
    grants, _guard = fixture.runtime.grant_snapshot(fixture.runtime.authenticate_key(fixture.keys["alpha"].key))
    item = item_from_body(HarnessIntelligenceDraft("paged.added", "skill", "An item granted during a walk",
                                                   "context_intelligence", "fixture:paged.added/v1", "MIT"), "ADDED")
    if item.identity not in fixture.catalogue.items:
        fixture.catalogue.register(item)
    fixture.bodies[item.identity] = "ADDED"
    fixture.bindings[item.identity] = ProvisioningItemBinding.from_item(item)
    try:
        fixture.runtime.set_grants("alpha", (*grants, ProvisioningGrant("alpha", fixture.bindings[item.identity], True)))
        answer, error = _post(client, base, fixture, {"record_type": V2, "operation": "list", "page_size": 5,
                                                      "cursor": first["next_cursor"]})
        pages, _sizes, refusal = _walk(client, base, fixture, 50)
        listed = [row["identity"] for page in pages for row in page["items"]]
    finally:
        fixture.runtime.set_grants("alpha", grants)
    return (answer.status_code == 409 and error["code"] == "list_release_changed" and refusal is None
            and "paged.added" in listed)


def _foreign_cursors_refused(client, base, fixture):
    _fresh_view(fixture, "release-cursors")
    _answer, first = _post(client, base, fixture, {"record_type": V2, "operation": "list", "page_size": 5})
    cursor = first["next_cursor"]
    version, offset, digest, mac = cursor.split(".")
    other_process = list_paging.ListCursors().mint("alpha", list_paging.request_digest(
        {"authority_effects": ["reads_fs"], "community_items": first["community_items"]}), int(offset), digest)
    tampered = [".".join((version, offset, digest, mac[:-1] + ("0" if mac[-1] != "0" else "1"))),
                ".".join((version, str(int(offset) + 1), digest, mac)), "not a cursor", other_process]
    answers = [_post(client, base, fixture, {"record_type": V2, "operation": "list", "page_size": 5, "cursor": value})
               for value in tampered]
    answers.append(_post(client, base, fixture, {"record_type": V2, "operation": "list", "page_size": 5,
                                                 "cursor": cursor}, tenant="beta"))
    answers.append(_post(client, base, fixture, {"record_type": V2, "operation": "list", "page_size": 5,
                                                 "cursor": cursor, "kinds": ["skill"]}))
    accepted, _value = _post(client, base, fixture, {"record_type": V2, "operation": "list", "page_size": 5,
                                                     "cursor": cursor})
    return (accepted.status_code == 200
            and all(answer.status_code == 400 and error["code"] == "list_cursor_invalid" for answer, error in answers))


def _page_sizes_refused(client, base, fixture):
    sizes = (0, -1, list_paging.MAXIMUM_LIST_PAGE_SIZE + 1, "10", True, 2.5)
    answers = [_post(client, base, fixture, {"record_type": V2, "operation": "list", "page_size": value})
               for value in sizes]
    answers.append(_post(client, base, fixture, {"record_type": V2, "operation": "list", "cursor": "c1.5.x.y"}))
    first_version, _error = _post(client, base, fixture, {"record_type": "service_provisioning_request/v1",
                                                          "operation": "list", "page_size": 5})
    largest, _value = _post(client, base, fixture, {"record_type": V2, "operation": "list",
                                                    "page_size": list_paging.MAXIMUM_LIST_PAGE_SIZE})
    return (all(answer.status_code == 400 and error["code"] == "list_page_size_invalid" for answer, error in answers)
            and first_version.status_code == 400 and largest.status_code == 200)


def _withheld_bounded(client, base, fixture):
    _fresh_view(fixture, "release-withheld")
    pages, _sizes, refusal = _walk(client, base, fixture, 25)
    whole = _whole(client, base, fixture)
    return (refusal is None and len(pages) > 1 and len(whole["withheld"]) > WITHHELD_BOUND
            and pages[0]["withheld"] == whole["withheld"][:WITHHELD_BOUND]
            and all(page["withheld_count"] == len(whole["withheld"]) for page in pages)
            and all(page["withheld"] == [] for page in pages[1:]))


def _one_row_over_the_cap_is_refused():
    """A row larger than the whole budget is refused, never answered as an empty page that cannot advance."""
    from .http import ServiceHttpError
    try:
        list_paging.fill_page({"record_type": list_paging.LIST_PAGE_RECORD_TYPE}, [{"purpose": "x" * 5000}], (),
                              budget=4000, encoding=list_paging.JSON_ENCODING, cursor_placeholder="c1.0." + "0" * 65)
    except ServiceHttpError as error:
        return error.code == "response_limit_exceeded" and error.status == 413
    return False


def _without_the_cursor_key_check():
    """Known-wrong: a cursor's keyed digest is never compared."""
    return patch.object(list_paging, "hmac", SimpleNamespace(new=hmac.new, compare_digest=lambda _a, _b: True))


def _without_the_list_binding():
    """Known-wrong: the list digest names nothing, so a cursor survives any change of the list."""
    original = list_paging.ListSnapshot.of.__func__

    def unbound(cls, answer, view):
        return replace(original(cls, answer, view), digest="0" * 32)
    return patch.object(list_paging.ListSnapshot, "of", classmethod(unbound))


def _without_the_grant_version_in_the_snapshot_key():
    """Known-wrong: a snapshot is found again whatever the account's grants record now says."""
    cached, kept = list_paging.cached_snapshot, list_paging.keep_snapshot

    def blind(key):
        return key[:1] + (None, None, None) + key[4:]
    return (patch.object(list_paging, "cached_snapshot", lambda view, key: cached(view, blind(key))),
            patch.object(list_paging, "keep_snapshot", lambda view, key, snapshot: kept(view, blind(key), snapshot)))


def _without_the_page_size_bounds():
    """Known-wrong: any page size reaches the list, and the schema no longer bounds it."""
    from . import http

    def unbounded(fields):
        return (fields.get("page_size"), fields.get("cursor")) if "page_size" in fields or "cursor" in fields \
            else (None, None)

    def loose():
        properties = list_paging.paging_schema_properties()
        properties["page_size"] = {}
        return properties
    return (patch.object(http, "paging_request", unbounded), patch.object(http, "paging_schema_properties", loose))


def _without_the_byte_budget():
    """Known-wrong: rows are added without counting their bytes."""
    return patch.object(list_paging, "_size", lambda _value, _encoding: 0)


def _advancing_by_page_size():
    """Known-wrong: the next cursor moves by the page size asked for, not by the rows that fitted."""
    original = list_paging.fill_page

    def advancing(header, rows, withheld, **options):
        answer, _used = original(header, rows, withheld, **options)
        return answer, len(rows)
    return patch.object(list_paging, "fill_page", advancing)


def _without_the_withheld_bound():
    """Known-wrong: the first page names every held-back item."""
    return patch.object(list_paging, "MAXIMUM_WITHHELD_ROWS", 10 ** 6)


def _old_413_wording():
    """Known-wrong: the refusal of a list too large to send says nothing of pages."""
    from .refusals import CODE_GUIDANCE
    return patch.dict(CODE_GUIDANCE, {"response_limit_exceeded": (
        "The answer to this request was larger than this service sends.",
        "Ask for fewer results or a smaller item, then repeat for the rest.")})


def _under(patches, function, *arguments):
    patches = patches if isinstance(patches, tuple) else (patches,)
    for held in patches:
        held.start()
    try:
        return function(*arguments)
    except Exception:
        return False
    finally:
        for held in reversed(patches):
            held.stop()


def run_checks(check, root):
    import httpx
    (root / "whole").mkdir()
    (root / "small").mkdir()
    fixture = _fixture(root / "whole", offered=60, withheld=list_paging.MAXIMUM_WITHHELD_ROWS + 50,
                       purpose_characters=60)
    with running_http(fixture) as (base, _service), httpx.Client(trust_env=False, timeout=30) as client:
        arguments = (client, base, fixture)
        check("a_paged_list_walk_returns_every_offered_item_exactly_once", _exactly_once(*arguments, 7))
        check("a_cursor_from_another_catalogue_release_is_refused_as_list_release_changed",
              _release_change_refused(*arguments))
        check("removing_the_list_binding_fails_the_release_change_check",
              not _under(_without_the_list_binding(), _release_change_refused, *arguments))
        check("a_grant_change_between_pages_refuses_the_next_page_as_list_release_changed",
              _grant_change_refused(*arguments))
        check("removing_the_grant_version_from_the_snapshot_key_fails_the_grant_change_check",
              not _under(_without_the_grant_version_in_the_snapshot_key(), _grant_change_refused, *arguments))
        check("a_tampered_foreign_or_other_filter_cursor_is_refused_as_list_cursor_invalid",
              _foreign_cursors_refused(*arguments))
        check("removing_the_cursor_key_check_fails_the_tampered_cursor_check",
              not _under(_without_the_cursor_key_check(), _foreign_cursors_refused, *arguments))
        check("a_page_size_outside_its_bounds_is_refused_as_list_page_size_invalid", _page_sizes_refused(*arguments))
        check("removing_the_page_size_bounds_fails_the_page_size_check",
              not _under(_without_the_page_size_bounds(), _page_sizes_refused, *arguments))
        check("the_first_page_names_at_most_the_bounded_withheld_items_and_every_page_counts_them",
              _withheld_bounded(*arguments))
        check("removing_the_withheld_bound_fails_the_withheld_check",
              not _under(_without_the_withheld_bound(), _withheld_bounded, *arguments))
    check("a_row_larger_than_the_answer_cap_is_refused_rather_than_answered_as_an_empty_page",
          _one_row_over_the_cap_is_refused())
    small = _fixture(root / "small", offered=24, withheld=3, purpose_characters=1500)
    with running_http(small, maximum_response_bytes=SMALL_CAP) as (base, _service), \
            httpx.Client(trust_env=False, timeout=30) as client:
        arguments = (client, base, small)
        check("a_page_never_exceeds_a_small_answer_cap_with_large_rows", _fits_the_cap(*arguments))
        check("removing_the_byte_budget_fails_the_answer_cap_check",
              not _under(_without_the_byte_budget(), _fits_the_cap, *arguments))
        check("a_walk_under_a_small_cap_still_returns_every_item_exactly_once", _exactly_once(*arguments, 50))
        check("advancing_the_cursor_by_page_size_fails_the_exactly_once_check",
              not _under(_advancing_by_page_size(), _exactly_once, *arguments, 50))
        check("a_protocol_tool_page_never_exceeds_a_small_answer_cap",
              asyncio.run(_protocol_fits_the_cap(base, small)))
        check("removing_the_byte_budget_fails_the_protocol_answer_cap_check",
              not _under(_without_the_byte_budget(), lambda: asyncio.run(_protocol_fits_the_cap(base, small))))
        check("an_unpaged_list_over_the_cap_names_page_size_in_its_next_action", _unpaged_names_page_size(*arguments))
        check("the_old_refusal_wording_fails_the_page_size_next_action_check",
              not _under(_old_413_wording(), _unpaged_names_page_size, *arguments))
