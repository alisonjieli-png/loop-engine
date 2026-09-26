"""Measure the paged list over real loopback HTTP on one real catalogue release bundle (roadmap S-6.203).

Kind: local measurement tool. It publishes the bundle into a temporary service
store with the `prepare` phase of `tools/measure_catalogue_serving.py`, which
uses the service's own code, serves that store with the real web application on
a loopback socket, and walks the list of a release-following account page by
page, the way the signed-in library table and a harness walk it:

```text
Measured for each answer cap, page size and set of step effects
├── first page     milliseconds until the first page arrives, with a cold snapshot of the list
├── walk           seconds from the first request until the last page arrived
├── pages          how many answers the walk took, and their largest size in bytes
├── rows           the rows the walk returned, the total the service offered, and the withheld count
└── once           whether every offered row arrived exactly once
```

A cold walk starts on a freshly installed copy of the served view, so the first
page takes the snapshot of the whole list, as the first load after a catalogue
release does. A warm walk repeats it on the same view. The unpaged list is
measured once at each cap for comparison.

    PYTHONPATH=src:tools python tools/measure_paged_listing.py \\
        --bundle /home/username/baltor-bundles/daily-2026-09-26-10 \\
        --root "$HOME/.le-ci-tmp/paged-listing/measure-1" \\
        --output artifacts/paged-listing-2026-09-26/paged-walk-6398-local-1.json

The bundle is only read. The root must be an empty or absent folder outside
this repository and outside the live service's volume. The tool takes no host
file and no credential; the key it issues to its own temporary store stays in
its memory. The numbers describe this machine only, not the hosted service.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import statistics
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

import measure_catalogue_serving as serving  # noqa: E402

RESULT_RECORD_TYPE = "paged_listing_measurement/v1"
LABEL = "local measurement on one workstation of a real release bundle over loopback HTTP; not a production claim"
REQUEST_VERSION = "service_provisioning_request/v2"
PATH = "/api/v1/provisioning"
#: The service default, one mebibyte, and the live host's stop-gap of September 26, 2026.
DEFAULT_CAPS = (262_144, 1_048_576, 16_777_216)
DEFAULT_PAGE_SIZES = (250, 500, 1000)


def effect_sets():
    """The step effects a list is asked with: the website's, the website's once pure is ignored, and a harness default."""
    from loop_engine.core.facets import EFFECTS
    from loop_engine.core.service_runtime.http import STEP_EFFECTS
    return {"every_step_effect": list(STEP_EFFECTS), "every_effect_with_pure": list(EFFECTS), "harness_default": None}


def walk(client, base, headers, *, page_size, effects):
    body = {"record_type": REQUEST_VERSION, "operation": "list", "page_size": page_size}
    if effects is not None:
        body["authority_effects"] = effects
    pages, cursor, identities, value = [], None, [], {}
    started = time.perf_counter()
    while len(pages) < 10_000:
        sent = time.perf_counter()
        answer = client.post(base + PATH, headers=headers, json={**body, **({"cursor": cursor} if cursor else {})})
        milliseconds = (time.perf_counter() - sent) * 1000
        if answer.status_code != 200:
            return {"refused": answer.json().get("error", {}).get("code"), "status": answer.status_code,
                    "pages_before": len(pages)}
        value = answer.json()["result"]
        pages.append({"ms": milliseconds, "rows": len(value["items"]), "bytes": len(answer.content)})
        identities += [row["identity"] for row in value["items"]]
        cursor = value["next_cursor"]
        if cursor is None:
            break
    later = [page["ms"] for page in pages[1:]]
    return {"pages": len(pages), "rows": len(identities), "total_offered": value.get("total_offered"),
            "withheld_count": value.get("withheld_count"), "every_row_once": len(identities) == len(set(identities))
            == value.get("total_offered"), "first_page_ms": round(pages[0]["ms"], 1),
            "later_page_ms_p50": round(statistics.median(later), 1) if later else None,
            "later_page_ms_max": round(max(later), 1) if later else None,
            "walk_seconds": round(time.perf_counter() - started, 3),
            "largest_answer_bytes": max(page["bytes"] for page in pages),
            "rows_on_first_page": pages[0]["rows"]}


def unpaged(client, base, headers, effects):
    body = {"record_type": REQUEST_VERSION, "operation": "list", "authority_effects": effects}
    started = time.perf_counter()
    answer = client.post(base + PATH, headers=headers, json=body)
    seconds = round(time.perf_counter() - started, 3)
    if answer.status_code != 200:
        return {"status": answer.status_code, "refused": answer.json().get("error", {}).get("code"), "seconds": seconds}
    return {"status": 200, "seconds": seconds, "bytes": len(answer.content), "rows": len(answer.json()["result"]["items"])}


def measure(bundle, root, *, caps=DEFAULT_CAPS, page_sizes=DEFAULT_PAGE_SIZES,
            accepted_licenses=serving.LIVE_ACCEPTED_LICENSES):
    import httpx
    from loop_engine.core.service_runtime.catalogue_serving import store_view
    from loop_engine.core.service_runtime.http import ServiceHttpApplication
    from loop_engine.core.service_runtime.http_test_fixtures import running_http
    from loop_engine.core.service_runtime.provisioning import DurableProvisioningBinding
    from loop_engine.core.service_runtime.records import TenantKeyIssue
    from loop_engine.core.service_runtime.runtime import ServiceRuntime
    bundle, root = Path(bundle), Path(root)
    refusal = serving.bundle_refusal(bundle) or serving.root_refusal(root, bundle)
    if refusal:
        raise serving.MeasurementRefused(refusal)
    prepared = serving.prepare(bundle, root, 1, accepted_licenses)
    license_policy, family_policy = serving.policies(accepted_licenses)
    config, _context, settings = serving.service(root)
    runtime = ServiceRuntime(config)
    started = time.perf_counter()
    view = store_view(config, settings, license_policy=license_policy, family_policy=family_policy)
    build_seconds = round(time.perf_counter() - started, 2)
    binding = DurableProvisioningBinding(runtime, view.catalogue, view.qualification_resolver, view.body_reader,
                                         view=view)
    headers = {"Authorization": "Bearer " + runtime.issue_key(TenantKeyIssue(serving.TENANT, "paged walk")).key}
    effects, results = effect_sets(), []
    for cap in caps:
        with running_http(None, application_factory=lambda configuration: ServiceHttpApplication(
                runtime, binding, configuration), maximum_response_bytes=cap) as (base, _service), \
                httpx.Client(trust_env=False, timeout=120) as client:
            results.append({"cap": cap, "walk": "unpaged", "effects": "every_effect_with_pure",
                            **unpaged(client, base, headers, effects["every_effect_with_pure"])})
            for name, named in effects.items():
                for page_size in page_sizes:
                    # A fresh copy of the served view: the first page takes the list's snapshot, as the first load
                    # after a release does. The second walk finds the snapshot kept with that view.
                    binding.install_view(replace(binding.current_view(), _lazy={}))
                    for temperature in ("cold", "warm"):
                        results.append({"cap": cap, "walk": temperature, "effects": name, "page_size": page_size,
                                        "load_average": serving.load_average(),
                                        **walk(client, base, headers, page_size=page_size, effects=named)})
    header = json.loads((bundle / "bundle.json").read_text("utf-8"))
    return {"record_type": RESULT_RECORD_TYPE, "label": LABEL, "bundle": str(bundle),
            "bundle_items": header.get("items"), "bundle_items_digest": header.get("items_digest"),
            "release_id": prepared["release_id"], "view_build_seconds": build_seconds,
            "items_in_view": len(view.catalogue.items), "effect_sets": effects, "walks": results,
            "machine": serving.machine()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bundle", type=Path, required=True, help="The release bundle folder; it is only read.")
    parser.add_argument("--root", type=Path, required=True, help="An empty or absent scratch folder.")
    parser.add_argument("--caps", type=int, nargs="+", default=list(DEFAULT_CAPS))
    parser.add_argument("--page-sizes", type=int, nargs="+", default=list(DEFAULT_PAGE_SIZES))
    parser.add_argument("--output", type=Path, help="Where to write the JSON record; it is also printed.")
    options = parser.parse_args(argv)
    try:
        record = measure(options.bundle, options.root, caps=tuple(options.caps), page_sizes=tuple(options.page_sizes))
    except serving.MeasurementRefused as refused:
        print(json.dumps({"refused": refused.code}))
        return 2
    text = json.dumps(record, indent=1, sort_keys=True)
    if options.output:
        options.output.parent.mkdir(parents=True, exist_ok=True)
        options.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
