"""Discriminating offline generation checks with an injected gateway only."""
import json
import tempfile
import unittest
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from loop_engine.core.custom_endpoint import CustomEndpoint
from loop_engine.core.model_capabilities import ModelOutputCapability
from loop_engine.core.model_gateway import (
    GatewayAttempt,
    ModelGatewayResult,
    ProviderSpec,
    provider_spec_from_endpoint,
)
from tools import generate_original_native_candidates as generation
from tools.test_prepare_harness_candidates import _git


class FakeProvider:
    DEFAULT_MODEL = "fixture-model"

    def output_capability_for(self, _model):
        return ModelOutputCapability(8192, "offline fixture capacity")

    def verify(self, model=""):
        raise AssertionError("No provider probe")

    def live_models(self):
        raise AssertionError("No provider listing")

    def chat_maxout(self, *_args, **_kwargs):
        raise AssertionError("No provider call")


class FakeGateway:
    def __init__(self, change=None):
        self.calls = []
        self.change = change

    def invoke(self, request):
        self.calls.append(request)
        method = json.loads(request.prompt)["method"]
        draft = {"record_type": generation.DRAFT_TYPE, "method_id": method["id"], "files": [
            {"path": f["path"], "content": "# Original fixture instructions\nRead reference.md.\n" if f["path"] == "AGENTS.md"
             else "# Reference\nA bounded fixture with no execution.\n"} for f in method["files"]]}
        result = ModelGatewayResult(ok=True, text=json.dumps(draft), provider="ollama_cloud", model="fixture-model",
                                    input_tokens=100, output_tokens=50,
                                    attempts=[GatewayAttempt("ollama_cloud", "fixture-model", "original_native_generation",
                                                             "fixture-loop", True, input_tokens=100, output_tokens=50,
                                                             provider_physical_requests=1)])
        return self.change(result) if self.change else result


class GenerationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        _git(self.repo, "init", "-q")
        _git(self.repo, "config", "user.name", "Fixture")
        _git(self.repo, "config", "user.email", "fixture@example.invalid")
        (self.repo / "LICENSE").write_bytes((Path(__file__).resolve().parents[1] / "LICENSE").read_bytes())
        (self.repo / "source.py").write_text("def fixture(value):\n    return value\n")
        _git(self.repo, "add", ".")
        _git(self.repo, "commit", "-qm", "fixture")
        self.method = {"id": "inspect_fixture", "title": "Inspect fixture", "purpose": "Inspect one bounded input.",
                       "sources": ["source.py"], "layer": "context", "family": "native_instruction",
                       "search_tags": ["inspect fixture"], "tags": {"domain": ["software"], "language": ["en"]},
                       "symbols": [], "declared_effects": [], "kind": "instruction_file", "styles": ["codex"],
                       "dependencies": [], "brief": "Inspect the supplied value without mutation.",
                       "acceptance": ["Report unknown when the required value is absent."],
                       "opportunity": "Original fixture method for contract testing, not customer intelligence.",
                       "files": [{"path": "AGENTS.md", "role": "instruction_file", "media_type": "text/markdown", "purpose": "Native briefing"},
                                 {"path": "reference.md", "role": "skill_reference", "media_type": "text/markdown", "purpose": "Supporting checks"}]}
        self.plan = {"record_type": generation.PLAN_TYPE, "source_revision": _git(self.repo, "rev-parse", "HEAD"),
                     "license": {"expression": "MIT", "path": "LICENSE", "sha256": generation.digest((self.repo / "LICENSE").read_bytes())},
                     "sources": {"source.py": generation.digest((self.repo / "source.py").read_bytes())}, "methods": [self.method]}
        self.path = self.root / "plan.json"
        self.write_plan()
        self.spec = ProviderSpec("ollama_cloud", FakeProvider(), "fixture", "env:FIXTURE")

    def write_plan(self):
        self.path.write_text(json.dumps(self.plan))

    def request(self, **changes):
        request = generation.GenerationRequest(self.repo, self.path, generation.digest(self.path.read_bytes()),
            self.root / "run", "fixture-model", "fixture", 3, output_tokens=4096, allow_unbounded_total=True,
            calls_authorized=True, writes_authorized=True)
        return replace(request, **changes)

    def run_generation(self, gateway=None, **changes):
        return generation.generate(self.request(**changes), gateway=gateway or FakeGateway(), provider_spec=self.spec, fixture_run=True)

    def test_versioned_resource_preserves_exact_prior_prompt_bytes(self):
        gateway = FakeGateway()
        self.run_generation(gateway)
        self.assertEqual(generation.digest(gateway.calls[0].system.encode()),
                         "02436f583453916c23f9ab7c19bd1cd5a27afeb0ec475116920b27e2ceb2fe87")
        record = json.loads((self.root / "run/run.json").read_text())
        self.assertEqual(record["prompt_resource"]["record_type"], generation.PROMPT_RESOURCE_TYPE)
        self.assertEqual(record["prompt_resource"]["render"]["render_digest"],
                         generation.digest(gateway.calls[0].system.encode()))
        self.assertIn("prompt_fragments.py", record["implementations"])

    def test_changed_prompt_resource_refuses_resume_before_call(self):
        gateway = FakeGateway()
        self.run_generation(gateway)
        reader = generation.read_file
        def changed(path, maximum):
            raw = reader(path, maximum)
            return raw + b"\n" if Path(path) == generation.PROMPT_RESOURCE_PATH else raw
        with patch.object(generation, "read_file", side_effect=changed), \
                self.assertRaisesRegex(generation.GenerationError, "resume_binding_changed"):
            self.run_generation(gateway)
        self.assertEqual(len(gateway.calls), 1)

    def test_unsupported_prompt_resource_refuses_before_output_or_call(self):
        reader = generation.read_file
        def changed(path, maximum):
            raw = reader(path, maximum)
            if Path(path) == generation.PROMPT_RESOURCE_PATH:
                value = json.loads(raw); value["record_type"] = "original_native_generation_prompt/v999"
                return json.dumps(value).encode()
            return raw
        gateway = FakeGateway()
        with patch.object(generation, "read_file", side_effect=changed), \
                self.assertRaisesRegex(generation.GenerationError, "prompt_resource_version_unsupported"):
            self.run_generation(gateway)
        self.assertFalse(gateway.calls)
        self.assertFalse((self.root / "run").exists())

    def test_credential_presence_delegates_to_selected_adapter(self):
        class CredentialProvider(FakeProvider):
            def load_api_key(self):
                return "synthetic credential presence only"
        spec = replace(self.spec, adapter=CredentialProvider())
        with patch.object(generation.os, "environ", {}):
            generation.require_provider_credential(spec)

    def test_missing_credential_refuses_without_provider_verification(self):
        class MissingProvider(FakeProvider):
            def load_api_key(self):
                return None
        with self.assertRaisesRegex(generation.GenerationError, "provider_credential_unavailable"):
            generation.require_provider_credential(replace(self.spec, adapter=MissingProvider()))
        with self.assertRaisesRegex(generation.GenerationError, "provider_not_supported_for_generation"):
            generation.require_provider_credential(replace(self.spec, provider_id="another_provider"))

    def test_native_tree_prepared_with_controller_digests_and_no_approval(self):
        gateway = FakeGateway()
        result = self.run_generation(gateway)
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["approval_count"], 0)
        self.assertTrue(result["fixture_run"])
        proposal = json.loads((self.root / "run/inspect_fixture.attempt-1/proposals.json").read_text())
        self.assertEqual(proposal["record_type"], "harness_candidate_batch_proposals/v2")
        prepared = self.root / "run/inspect_fixture.attempt-1/candidates"
        self.assertEqual(json.loads((prepared / "items.json").read_text())["record_type"], "starter_catalogue_candidate_items/v3")
        self.assertFalse(gateway.calls[0].config.allow_failover)
        self.assertEqual(gateway.calls[0].config.max_route_attempts, 1)
        self.assertEqual(gateway.calls[0].config.output_allocation.requested_tokens, 4096)
        self.assertIsNone(gateway.calls[0].config.max_total_tokens)

    def test_success_resume_does_not_call_model_again_and_changed_payload_refuses(self):
        gateway = FakeGateway()
        self.run_generation(gateway)
        self.run_generation(gateway)
        self.assertEqual(len(gateway.calls), 1)
        p=self.root / "run/inspect_fixture.attempt-1/candidates/packages/inspect_fixture/AGENTS.md"
        p.write_text("changed")
        with self.assertRaises(ValueError):
            self.run_generation(gateway)
        self.assertEqual(len(gateway.calls), 1)

    def test_authority_source_plan_and_budget_binding_refuse_before_call(self):
        gateway = FakeGateway()
        for change in ({"calls_authorized": False}, {"writes_authorized": False}, {"call_ceiling": True},
                       {"allow_unbounded_total": False}, {"plan_sha256": "0"*64}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.run_generation(gateway, **change)
        self.assertFalse(gateway.calls)
        self.assertFalse((self.root / "run").exists())
        (self.repo / "source.py").write_text("changed")
        with self.assertRaises(ValueError):
            self.run_generation(gateway)
        self.assertFalse(gateway.calls)

    def test_call_ceiling_stops_without_generating_another_method(self):
        second = deepcopy(self.method); second["id"] = "second_fixture"
        self.plan["methods"].append(second); self.write_plan()
        gateway = FakeGateway()
        result = self.run_generation(gateway, call_ceiling=1)
        self.assertEqual(result["stop_reason"], "call_ceiling_reached")
        self.assertEqual(len(gateway.calls), 1)

    def test_missing_or_extra_path_and_wrapper_are_preserved_failures(self):
        def omit(result):
            draft=json.loads(result.text); draft["files"].pop(); result.text=json.dumps(draft); return result
        gateway = FakeGateway(omit)
        result = self.run_generation(gateway)
        self.assertEqual(result["candidate_count"], 0)
        self.assertTrue((self.root / "run/inspect_fixture.attempt-1/response.txt").exists())
        self.run_generation(gateway)
        self.assertEqual(len(gateway.calls), 1)
        self.run_generation(gateway, retry_failed=True)
        self.assertEqual(len(gateway.calls), 2)

    def test_nonmatching_model_never_generates_package(self):
        def wrong(result): result.model="unexpected"; return result
        result=self.run_generation(FakeGateway(wrong))
        self.assertEqual(result["candidate_count"],0)
        self.assertIn("model_identity_mismatch",(self.root/'run/journal.jsonl').read_text())

    def test_unknown_usage_is_not_zero(self):
        def unknown(result): result.input_tokens=None; return result
        result=self.run_generation(FakeGateway(unknown))
        self.assertFalse(result["usage_complete"])
        data=json.loads((self.root/'run/journal.jsonl').read_text().splitlines()[-1])["data"]
        self.assertIsNone(data["input_tokens"])
        self.assertIsNone(data["charged_tokens"])
        self.assertEqual(data["output_tokens"],50)

    def test_strict_total_requires_resolver_before_dispatch(self):
        gateway=FakeGateway()
        with self.assertRaisesRegex(ValueError,"token_bound_resolver_required"):
            self.run_generation(gateway, token_ceiling=1000, allow_unbounded_total=False)
        self.assertFalse(gateway.calls)

    def test_interrupted_dispatch_is_not_replayed(self):
        class Interrupted(FakeGateway):
            def invoke(self, request): raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.run_generation(Interrupted())
        gateway=FakeGateway(); result=self.run_generation(gateway)
        self.assertEqual(result["stop_reason"],"interrupted_dispatch_needs_reconciliation")
        self.assertFalse(gateway.calls)

    def test_duplicate_method_and_unknown_file_role_refuse_before_dispatch(self):
        self.plan["methods"].append(deepcopy(self.method)); self.write_plan()
        with self.assertRaises(ValueError): self.run_generation()
        self.plan["methods"].pop(); self.plan["methods"][0]["files"][1]["role"]="unknown"
        self.write_plan()
        gateway=FakeGateway()
        with self.assertRaises(ValueError): self.run_generation(gateway)
        self.assertFalse(gateway.calls)

    def test_changed_resume_budget_and_timeout_refuse(self):
        gateway=FakeGateway(); self.run_generation(gateway)
        for change in ({"call_ceiling":4},{"timeout_seconds":10}):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError,"resume_binding_changed"):
                self.run_generation(gateway,**change)
        self.assertEqual(len(gateway.calls),1)

    def test_identical_payloads_under_new_method_name_do_not_inflate_count(self):
        second=deepcopy(self.method);second["id"]="second_fixture"
        self.plan["methods"].append(second);self.write_plan()
        result=self.run_generation()
        self.assertEqual(result["candidate_count"],1)
        self.assertEqual(result["dispatches"],2)

    def test_secret_shaped_failed_output_is_redacted_and_never_prepared(self):
        secret="sk-"+"a"*40
        def poisoned(result): result.text=secret; return result
        result=self.run_generation(FakeGateway(poisoned))
        self.assertEqual(result["candidate_count"],0)
        self.assertNotIn(secret,(self.root/'run/inspect_fixture.attempt-1/response.txt').read_text())
        self.assertNotIn(secret,(self.root/'run/journal.jsonl').read_text())

    def test_torn_journal_and_unknown_completion_values_refuse_resume(self):
        gateway=FakeGateway();self.run_generation(gateway)
        p=self.root/'run/journal.jsonl';old=p.read_bytes();p.write_bytes(old[:-1])
        with self.assertRaisesRegex(ValueError,'journal_incomplete_line'):self.run_generation(gateway)
        self.assertEqual(len(gateway.calls),1)

    def test_call_failure_unknown_cannot_be_repeated_by_retry_failed(self):
        class Failed(FakeGateway):
            def invoke(self,request):raise RuntimeError('unsafe provider detail')
        result=self.run_generation(Failed())
        self.assertEqual(result['stop_reason'],'unknown_or_exceeded_accounting')
        gateway=FakeGateway();result=self.run_generation(gateway,retry_failed=True)
        self.assertEqual(result['stop_reason'],'interrupted_dispatch_needs_reconciliation')
        self.assertFalse(gateway.calls)

    def test_unbounded_mode_uses_full_capacity_if_no_allocation_supplied(self):
        gateway=FakeGateway();self.run_generation(gateway,output_tokens=None)
        self.assertIsNone(gateway.calls[0].config.output_allocation)
        self.assertEqual(json.loads((self.root/'run/run.json').read_text())['output_tokens'],8192)

    def test_symlink_output_root_refuses(self):
        target=self.root/'elsewhere';target.mkdir();(self.root/'run').symlink_to(target,target_is_directory=True)
        gateway=FakeGateway()
        with self.assertRaisesRegex(ValueError,'path_not_plain'):self.run_generation(gateway)
        self.assertFalse(gateway.calls)

    def test_strict_budget_reaches_gateway_and_unknown_usage_consumes_reservation(self):
        def unknown(result): result.input_tokens=None; return result
        gateway=FakeGateway(unknown)
        request=self.request(token_ceiling=10000,allow_unbounded_total=False)
        result=generation.generate(request,gateway=gateway,provider_spec=self.spec,
                                   token_bound_resolver=object(),fixture_run=True)
        self.assertEqual(gateway.calls[0].config.max_total_tokens,10000)
        self.assertEqual(result['stop_reason'],'unknown_or_exceeded_accounting')
        data=json.loads((self.root/'run/journal.jsonl').read_text().splitlines()[-1])['data']
        self.assertEqual(data['charged_tokens'],10000)
        self.assertEqual(data['charge_basis'],'reserved_remaining')
        self.assertIsNone(data['input_tokens'])

    def test_over_bound_usage_does_not_prepare_a_success(self):
        gateway=FakeGateway()
        result=generation.generate(self.request(token_ceiling=100,allow_unbounded_total=False),
                                   gateway=gateway,provider_spec=self.spec,token_bound_resolver=object(),fixture_run=True)
        self.assertEqual(result['candidate_count'],0)
        self.assertEqual(result['stop_reason'],'unknown_or_exceeded_accounting')

    def test_invalid_utf8_is_a_failure_even_if_replacement_would_parse(self):
        def invalid(result):
            value=json.loads(result.text);value['files'][0]['content']='invalid '+chr(0xD800)
            result.text=json.dumps(value,ensure_ascii=False);return result
        result=self.run_generation(FakeGateway(invalid))
        self.assertEqual(result['candidate_count'],0)
        self.assertIn('model_output_invalid_utf8',(self.root/'run/journal.jsonl').read_text())

    def test_changed_prepared_reference_refuses_resume(self):
        gateway=FakeGateway();self.run_generation(gateway)
        path=self.root/'run/inspect_fixture.attempt-1/candidates/items.json'
        value=json.loads(path.read_text());value['items'][0]['reference']['digest']='0'*64
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'saved_prepared_tree_changed'):self.run_generation(gateway)
        self.assertEqual(len(gateway.calls),1)

    def test_changed_prepared_metadata_or_specification_refuses_resume(self):
        changes = [('items.json',lambda v:v['items'][0]['producer'].update(family='different_family')),
                   ('items.json',lambda v:v['items'][0]['reference'].update(declared_effects=['network'])),
                   ('specifications-001.json',lambda v:v['specifications'][0].update(declared_effects=['network'])),
                   ('preparation-report.json',lambda v:v.update(approved=True))]
        for number,(name,mutate) in enumerate(changes):
            with self.subTest(name=name):
                output=self.root/f'run-{number}';gateway=FakeGateway();self.run_generation(gateway,output=output)
                p=output/'inspect_fixture.attempt-1/candidates'/name
                value=json.loads(p.read_text());mutate(value);p.write_text(json.dumps(value))
                with self.assertRaisesRegex(ValueError,'saved_prepared_tree_changed'):
                    self.run_generation(gateway,output=output)
                self.assertEqual(len(gateway.calls),1)

    def test_rejected_physical_attempt_identity_is_retained_without_requested_fallback(self):
        def mismatch(result):
            result.ok=False;result.model='';result.error_code='model_identity_mismatch'
            result.attempts=[replace(result.attempts[0],model='reported-other-model',ok=False,
                                    provider_request_digest='1'*64)]
            return result
        self.run_generation(FakeGateway(mismatch))
        data=json.loads((self.root/'run/journal.jsonl').read_text().splitlines()[-1])['data']
        self.assertIn('reported_model',data)
        self.assertEqual(data['reported_model'],'reported-other-model')
        self.assertEqual(data['attempt_provider'],'ollama_cloud')
        self.assertEqual(data['provider_request_digest'],'1'*64)
        self.assertEqual(data['input_tokens'],100)

    def test_old_run_contract_is_refused_without_reinterpretation(self):
        gateway=FakeGateway();self.run_generation(gateway)
        p=self.root/'run/run.json';value=json.loads(p.read_text())
        self.assertEqual(value['record_type'],'original_native_generation_run/v6')
        self.assertEqual(value['journal_record_type'],'original_native_generation_event/v3')
        self.assertIsNone(value['provider_binding'])
        self.assertEqual(value['draft_admission']['contract']['normalization']['allowed_strategies'],
                         ['strict_json','json_markdown_fence_removed'])
        value['record_type']='original_native_generation_run/v5';p.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'resume_binding_changed'):self.run_generation(gateway)
        self.assertEqual(len(gateway.calls),1)

    def test_persistent_model_identity_failure_stops_remaining_methods(self):
        second=deepcopy(self.method);second['id']='second_fixture'
        self.plan['methods'].append(second);self.write_plan()
        def wrong(result):result.model='unexpected';return result
        gateway=FakeGateway(wrong);result=self.run_generation(gateway)
        self.assertEqual(result['stop_reason'],'model_identity_mismatch')
        self.assertEqual(len(gateway.calls),1)

    def test_direct_gateway_and_adapter_implementations_are_bound_on_resume(self):
        gateway=FakeGateway();self.run_generation(gateway)
        meta=json.loads((self.root/'run/run.json').read_text())
        self.assertIn('model_gateway.py',meta['implementations'])
        self.assertIn(Path(__file__).name,meta['implementations'])
        changed=dict(meta['implementations']);changed['model_gateway.py']='0'*64
        with patch.object(generation,'implementation_digests',return_value=changed), \
                self.assertRaisesRegex(ValueError,'resume_binding_changed'):
            self.run_generation(gateway)
        self.assertEqual(len(gateway.calls),1)

    def test_class_adapter_hashes_owning_source_and_changed_source_refuses_resume(self):
        endpoint = CustomEndpoint(name="fixture_box", base_url="https://fixture.invalid/v1",
            model="fixture-model", auth_scheme="none",
            output_capability=ModelOutputCapability(8192, "offline fixture capacity"))
        self.spec = provider_spec_from_endpoint(endpoint)
        source = Path(generation.inspect.getfile(self.spec.adapter))
        bindings = generation.implementation_digests(self.spec)
        self.assertEqual(bindings[source.name], generation.digest(source.read_bytes()))

        def provider(result):
            result.provider = "fixture_box"
            result.attempts = [replace(result.attempts[0], provider="fixture_box")]
            return result

        gateway = FakeGateway(provider)
        self.assertEqual(self.run_generation(gateway)["candidate_count"], 1)
        read_file = generation.read_file

        def changed_adapter(path, maximum):
            raw = read_file(path, maximum)
            return raw + b"\n# changed adapter fixture\n" if Path(path) == source else raw

        with patch.object(generation, "read_file", side_effect=changed_adapter), \
                self.assertRaisesRegex(ValueError, "resume_binding_changed"):
            self.run_generation(gateway)
        self.assertEqual(len(gateway.calls), 1)

    def test_adapter_without_source_file_is_explicitly_unqualified(self):
        unavailable = type("SourceUnavailableAdapter", (FakeProvider,), {"__module__": "builtins"})
        with self.assertRaisesRegex(generation.GenerationError, "implementation_source_unavailable"):
            generation.implementation_digests(replace(self.spec, adapter=unavailable))


    def admission_of_last_completion(self):
        return json.loads((self.root/'run/journal.jsonl').read_text().splitlines()[-1])['data']

    def test_exact_markdown_json_fence_is_admitted_and_recorded_not_silent(self):
        def fenced(result): result.text='```json\n'+result.text+'\n```'; return result
        gateway=FakeGateway(fenced);result=self.run_generation(gateway)
        self.assertEqual(result['candidate_count'],1)
        data=self.admission_of_last_completion()
        self.assertEqual(data['response_admission']['strategy'],'json_markdown_fence_removed')
        self.assertEqual(data['response_admission']['transformation_trace'],['removed_exact_markdown_json_fence'])
        raw=(self.root/'run/inspect_fixture.attempt-1/response.txt').read_bytes()
        self.assertTrue(raw.startswith(b'```json'))
        self.assertEqual(data['response_sha256'],generation.digest(raw))

    def test_strict_json_draft_records_the_strict_strategy(self):
        self.run_generation()
        admission=self.admission_of_last_completion()['response_admission']
        self.assertEqual((admission['admitted'],admission['strategy'],admission['transformation_trace']),
                         (True,'strict_json',[]))

    def test_other_wrappers_and_invalid_or_extended_drafts_are_not_admitted(self):
        def text_outside(result): result.text='Here is the JSON:\n```json\n'+result.text+'\n```'; return result
        def two_fences(result): result.text='```json\n'+result.text+'\n```\n```json\n{}\n```'; return result
        def invalid_inside(result): result.text='```json\n'+result.text.replace('"content": "#','"content": [#',1)+'\n```'; return result
        def echoed_role(result):
            value=json.loads(result.text);value['files'][0]['role']='instruction_file';result.text=json.dumps(value);return result
        for number,change in enumerate((text_outside,two_fences,invalid_inside,echoed_role)):
            with self.subTest(change=change.__name__):
                output=self.root/f'refused-{number}';result=self.run_generation(FakeGateway(change),output=output)
                self.assertEqual(result['candidate_count'],0)
                data=json.loads((output/'journal.jsonl').read_text().splitlines()[-1])['data']
                self.assertEqual(data['error_code'],'draft_json_not_admitted')
                self.assertFalse(data['response_admission']['admitted'])

if __name__ == "__main__":
    unittest.main()
