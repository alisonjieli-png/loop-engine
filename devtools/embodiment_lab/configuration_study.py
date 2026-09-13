"""Frozen real-provider configuration comparisons through existing Loop contracts.

This application owns experimental selection and derived records only. Every
assignment uses the canonical Loop and gateway, with separate task evaluation.
No live answer is injected, repaired by inventing data, or silently replaced.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
import random
import uuid
import zipfile

from loop_engine.core.model_response_admission import ModelResponseAdmissionPolicy
from .systematic_records import CampaignProjection, digest
from .systematic_runtime import ROOT, SemanticStepSession, configure_environment


@dataclass(frozen=True)
class AdmissionConfiguration:
    harness_id: str
    normalization: str
    temperature: float = 0.0
    output_allocation_tokens: int = 4096
    version: str = '1.0.0'

    def __post_init__(self):
        if self.harness_id not in ('native_gateway', 'pi', 'opencode', 'codex'):
            raise ValueError('unregistered comparison harness')
        if self.normalization not in ('strict_json', 'meaning_preserving'):
            raise ValueError('unregistered response policy')
        if self.version != '1.0.0' or type(self.output_allocation_tokens) is not int:
            raise ValueError('invalid version or response allocation')
        if self.output_allocation_tokens <= 0:
            raise ValueError('response allocation must be positive')

    def policy(self):
        return (ModelResponseAdmissionPolicy(allowed_strategies=('strict_json',),
                    report_required_field_names=True)
                if self.normalization == 'strict_json' else
                ModelResponseAdmissionPolicy(report_required_field_names=True))


def freeze_sources(destination):
    """Keep an immutable source artifact, including scripts used inside sandboxes."""
    candidates = set()
    for directory in (ROOT/'src/loop_engine', ROOT/'devtools/embodiment_lab'):
        candidates.update(p for p in directory.rglob('*') if p.is_file()
                          and '__pycache__' not in p.parts
                          and p.suffix in ('.py', '.yaml', '.json', '.jsonl', '.md', '.toml', '.txt'))
    candidates.update(ROOT/'embodiments'/name/'harness.json'
                      for name in ('pi', 'opencode', 'codex'))
    manifest = []
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(candidates):
            body = path.read_bytes()
            relative = str(path.relative_to(ROOT))
            archive.writestr(relative, body)
            manifest.append({'path': relative, 'sha256': hashlib.sha256(body).hexdigest(),
                             'bytes': len(body)})
    return manifest


def source_changes(manifest):
    return [item['path'] for item in manifest if not (ROOT/item['path']).is_file()
            or hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest() != item['sha256']]


def admission_comparison(study_root):
    root = Path(study_root).resolve()
    phase = root/('admission-' + uuid.uuid4().hex[:12])
    phase.mkdir(exist_ok=False)
    projection = CampaignProjection(phase/'projection.duckdb')
    sources = freeze_sources(phase/'source-files.zip')
    configs = [AdmissionConfiguration(harness, policy)
               for harness in ('native_gateway','pi','opencode','codex')
               for policy in ('strict_json','meaning_preserving')]
    random.Random(9122601).shuffle(configs)
    marker = uuid.uuid4().hex
    packet = {'marker': marker, 'requested_action': 'return the marker and ready=true'}
    schema = {'type':'object','properties':{'marker':{'const':marker},'ready':{'const':True}},
              'required':['marker','ready'],'additionalProperties':False}
    manifest = {'record_type':'admission_configuration_comparison/v1',
                'phase_id':phase.name,'selection_rule':'all four named harnesses crossed with both response policies',
                'population':'one synthetic packet-delivery assignment, not task solving',
                'configs':[asdict(c) for c in configs], 'packet':packet,'schema':schema,
                'sources':sources, 'provider_configuration_digest':hashlib.sha256((root/'provider.yaml').read_bytes()).hexdigest(),
                'automatic_provider_failover':False,'total_call_limit':None,
                'total_token_limit':None,'harness_process_lifetime':'fresh_per_semantic_attempt'}
    projection.record('manifest',phase.name,manifest)
    projection.export_object(phase/'manifest.json',manifest)
    configure_environment()
    results = []
    try:
        for index, config in enumerate(configs):
            cell_id = f'{index:02d}-{config.harness_id}-{config.normalization}-{uuid.uuid4().hex[:8]}'
            print('START',cell_id,flush=True)
            started = {'cell_id':cell_id,'configuration':asdict(config),'status':'started',
                       'model_calls':None,'accounting_complete':False}
            projection.record('cell',cell_id,started)
            try:
                session = SemanticStepSession(root,config.harness_id,phase/cell_id)
                observation = session.invoke('Return the exact assigned marker',packet,schema,
                    temperature=config.temperature,output_allocation_tokens=config.output_allocation_tokens,
                    response_policy=config.policy())
                result = {**started,'status':'completed','observation':observation,
                          'source_changes':source_changes(sources)}
            except Exception as error:
                result = {**started,'status':'setup_failed','error_type':type(error).__name__}
            results.append(result)
            projection.record('cell',cell_id,result)
            projection.export_object(phase/(cell_id+'.json'),result)
            projection.refresh_export(phase/'summary.json',{
                'record_type':'admission_configuration_comparison_summary/v1',
                'manifest_digest':digest(manifest),'planned':len(configs),'finished':len(results),
                'results':results,'live_provider':True,'full_system_benchmark':False})
            observation = result.get('observation',{})
            print('RESULT',cell_id,'admitted',observation.get('accepted_response'),
                  'calls',observation.get('model_calls'),'policy',config.normalization,
                  'error',observation.get('error') or result.get('error_type'),flush=True)
    finally:
        projection.close()
    print('PHASE_COMPLETE',phase,flush=True)
    return phase


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',required=True)
    admission_comparison(parser.parse_args().root)
