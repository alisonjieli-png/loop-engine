"""Remove one owning search guard in memory and run its named regression."""
import hashlib
import inspect
import io
import json
import textwrap
import unittest
from unittest.mock import patch
from loop_engine.core.service_runtime import http
from test_search_effect_authority import SearchEffectAuthority

cases = [
    ("selection_forwarding", "_search", 'authority_effects=fields.get("authority_effects", ())',
     'authority_effects=()', "test_search_can_select_an_authorized_effectful_item"),
    ("default_effects", "_search", 'fields.get("authority_effects", ())',
     'fields.get("authority_effects", EFFECTS)', "test_omitted_empty_or_insufficient_effects_remain_withheld"),
    ("shape_validation", "_validate_search", 'if "authority_effects" in payload:',
     'if False:', "test_unknown_and_malformed_effects_refuse_before_indexing"),
    ("record_version", "_validate_search", 'if versioned and payload.get("record_type") != RETRIEVAL_REQUEST_VERSION:',
     'if False:', "test_request_version_is_advertised_and_old_or_future_requests_refuse"),
    ("final_authority", "_search", 'self._verify_search_snapshot(authentication, current, grant_guard)',
     'None', "test_inflight_grant_change_still_refuses_selected_metadata"),
]
rows=[]
for name,method,old,new,test in cases:
    source=textwrap.dedent(inspect.getsource(getattr(http.ServiceHttpApplication,method)))
    if source.count(old)!=1:raise AssertionError(name+" anchor is not unique")
    space=dict(vars(http))
    exec(compile(source.replace(old,new),"<search-guard-mutant>","exec"),space)
    captured=io.StringIO()
    with patch.object(http.ServiceHttpApplication,method,space[method]):
        result=unittest.TextTestRunner(stream=captured).run(unittest.TestSuite([SearchEffectAuthority(test)]))
    rows.append({"name":name,"named_check":test,"detected":not result.wasSuccessful(),"report":captured.getvalue()})
print(json.dumps({"record_type":"search_effect_guard_mutations/v1","source_sha256":hashlib.sha256(inspect.getsource(http).encode()).hexdigest(),"checks":rows,"passed":all(row['detected'] for row in rows)},indent=2))
