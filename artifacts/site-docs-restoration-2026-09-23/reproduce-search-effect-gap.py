"""Local-only search/list comparison; never writes credentials to the report."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import urllib.request
import urllib.error
from loop_engine.core.service_runtime.http_test_fixtures import HttpDomainFixture, running_http
from loop_engine.core.harness_intelligence import HarnessIntelligenceDraft, item_from_body
from loop_engine.core.provisioning_server import ProvisioningGrant, ProvisioningItemBinding

with TemporaryDirectory(prefix="docs-search-effects-") as folder:
    fixture = HttpDomainFixture(Path(folder))
    item = item_from_body(HarnessIntelligenceDraft("docs.effect.example", "tool", "Zebrafish deterministic planner",
        "harness_local", "fixture:docs.effect.example/v1", "MIT", ("spawns_process",)), "Zebrafish deterministic planner")
    fixture.catalogue.register(item)
    fixture.bodies[item.identity] = "Zebrafish deterministic planner"
    fixture.bindings[item.identity] = ProvisioningItemBinding.from_item(item)
    fixture.runtime.set_grants("alpha", (ProvisioningGrant("alpha", fixture.bindings[item.identity], True),))
    with running_http(fixture) as (base, _):
        def call(address, body):
            request = urllib.request.Request(base+address, data=json.dumps(body).encode(),
                headers={**fixture.headers(), "Content-Type": "application/json"}, method="POST")
            try:
                with urllib.request.urlopen(request) as response:
                    return {"status": response.status, "body": json.load(response)}
            except urllib.error.HTTPError as error:
                return {"status": error.code, "body": json.load(error)}
        search = {"record_type":"service_retrieval_request/v1", "query":"Zebrafish deterministic planner", "mode":"lexical", "top_n":5}
        listing = {"record_type":"provisioning_request/v1", "operation":"list", "request_id":"docs-list-control", "authority_effects":["spawns_process"]}
        report = {"record_type":"documentation_search_effect_gap/v1", "scope":"local fixture only", "scenario":"search_can_select_an_authorized_effectful_item", "owner":"core service retrieval/provisioning boundary; root records S-6.40/44",
                  "plain_search":call("/api/v1/search",search), "search_with_authority":call("/api/v1/search",{**search,"authority_effects":["spawns_process"]}), "authorized_list":call("/api/v1/provisioning",listing)}
        # Request references are opaque diagnostic identifiers, not the fixture credential.
        print(json.dumps(report, indent=2))
