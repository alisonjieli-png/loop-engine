"""Remove one check in memory, rerun its known-wrong case, retain detection evidence."""
import hashlib
import json
from pathlib import Path
import sys
import types
from unittest.mock import patch
import check_documentation_index as checker
from build_documentation_index import INDEX_FILE, BODY_DIRECTORY, PAGE_TABLE_MODULE
from test_documentation_index import DocumentationAgreement, ROOT

source = Path(checker.__file__).read_text()
read = lambda name: (ROOT / name).read_text()
guide = "docs/guides/service-troubleshooting.md"
cases = [
 ("coverage", 'if set(paths) != required:', 'if False:', {"docs/guides/README.md":read("docs/guides/README.md").replace("| [Your account]", "| [Absent](service-absent.md) | Missing |\n| [Your account]")}, "customer_coverage"),
 ("alias", 'if not page.get("body") and views.get(alias) != views.get(page["address"]):', 'if False:', {"src/loop_engine/core/service_runtime/web_assets/service.js":read("src/loop_engine/core/service_runtime/web_assets/service.js").replace('"/docs/getting-set-up":"setup"','"/docs/getting-set-up":"home"')},"alias_view"),
 ("route", 'if routes.get(address) != filename or not (root / WEB_ASSETS / filename).is_file():', 'if False:', {PAGE_TABLE_MODULE:read(PAGE_TABLE_MODULE).replace('"/docs/what-baltor-is"','"/docs/forgotten"')}, "route"),
 ("extra_route", 'if address.startswith(("/docs/", "/assets/docs/")) and address not in expected:', 'if False:', {PAGE_TABLE_MODULE:read(PAGE_TABLE_MODULE).replace('WEB_ASSETS = {','WEB_ASSETS = {"/docs/extra": ("index.html", HTML_MEDIA_TYPE),')}, "unlisted_route"),
 ("freshness", 'for path in differences(root, serialize(record), bodies):', 'for path in []:', {BODY_DIRECTORY+"/orphan.html":"<p>Unlisted</p>"},"stale_pages"),
 ("terminology", 'if expression.search(text):', 'if False:', {INDEX_FILE:read(INDEX_FILE).replace('"title": "Your account"','"title": "Private beta account"')},"terminology"),
 ("facts", 'for finding in source["findings"]:', 'for finding in []:', {guide:read(guide).replace('| `item_unavailable` | 404 |','| `item_unavailable` | 403 |')},"refusal_status"),
]
rows=[]
fixture=DocumentationAgreement()
for name, old,new,overrides,kind in cases:
    if source.count(old)!=1: raise AssertionError(name+" mutation anchor is not unique")
    positive=fixture.report(overrides)
    mutant=types.ModuleType("check_documentation_index")
    mutant.__file__=checker.__file__
    exec(compile(source.replace(old,new),checker.__file__,"exec"),mutant.__dict__)
    with patch.dict(sys.modules,{"check_documentation_index":mutant}):
        negative=fixture.report(overrides)
    detects=kind in {x['kind'] for x in positive['findings']} and kind not in {x['kind'] for x in negative['findings']}
    rows.append({"guard":name,"expected_finding":kind,"control_detected_removed_guard":detects})
print(json.dumps({"source_digest":hashlib.sha256(source.encode()).hexdigest(),"checks":rows,"passed":all(x['control_detected_removed_guard'] for x in rows)},indent=2))
