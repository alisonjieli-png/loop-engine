"""Read exact peer records and recheck the exported warm packages without a model."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
LAB = Path('/home/username/solver-lab')
PAIRS = (
    ('opencode-portable-atomic', '20260908-205423-ef244f', '20260908-212007-d55609'),
    ('pi-portable-atomic', '20260908-210843-acf150', '20260908-212008-d8a9aa'),
)


def gate_passed(gate: dict) -> bool:
    return gate.get('exit_code') == 0 and gate.get('integrity_ok') is True and not gate.get('timed_out')


if __name__ == '__main__':
    out = HERE / 'cold-warm-proof.json'
    if out.exists():
        raise SystemExit('Refusing to replace evidence')
    rows = []
    for peer, cold_id, warm_id in PAIRS:
        root = LAB / peer
        cold_path = root / 'runs' / cold_id / 'result.json'
        warm_path = root / 'runs' / warm_id / 'result.json'
        cold, warm = [json.loads(p.read_text()) for p in (cold_path, warm_path)]
        attempts = [a for step in cold['steps'] for a in step['attempts']]
        usage = [u for a in attempts for u in a['receipt']['usage']]
        package = Path(warm['package'])
        start = time.monotonic()
        run = subprocess.run(['/usr/bin/bash', 'run.sh'], cwd=package,
                             env={'PATH': '/usr/bin:/bin', 'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1'},
                             capture_output=True, text=True, timeout=90)
        replay_seconds = time.monotonic() - start
        (HERE / f'{peer}-export-replay.log').write_text(run.stdout + run.stderr)
        same_fingerprints = ([s['fingerprint']['key'] for s in cold['steps']]
                             == [s['fingerprint']['key'] for s in warm['steps']])
        warm_checks = all(s['reused'] and not s['attempts'] and gate_passed(s['replay_gate']) for s in warm['steps'])
        rows.append({'peer': peer, 'cold_record': str(cold_path), 'warm_record': str(warm_path),
                     'cold_record_sha256': hashlib.sha256(cold_path.read_bytes()).hexdigest(),
                     'warm_record_sha256': hashlib.sha256(warm_path.read_bytes()).hexdigest(),
                     'model': cold['model'], 'cold_status': cold['status'], 'warm_status': warm['status'],
                     'cold_seconds': cold['duration'], 'warm_seconds': warm['duration'],
                     'cold_harness_instances': cold['llm_instances'], 'warm_harness_instances': warm['llm_instances'],
                     'cold_usage_records': len(usage),
                     'cold_input_tokens_known_sum': sum(u.get('input', 0) for u in usage),
                     'cold_output_tokens_known_sum': sum(u.get('output', 0) for u in usage),
                     'cold_failed_proposals': sum(not gate_passed(a.get('gate', {})) for a in attempts),
                     'physical_model_requests': None, 'provider_cost': None,
                     'different_full_source_digest': cold['source_sha256'] != warm['source_sha256'],
                     'same_fingerprints': same_fingerprints, 'all_warm_method_gates_pass': warm_checks,
                     'export_replay_exit': run.returncode, 'export_replay_seconds': replay_seconds,
                     'proof_scope': 'two authored method-repair responsibilities; unchanged target ASTs and declared bindings; unrelated full-file changes',
                     'zero_model_warm_evidence': 'no live flag, no credentials, empty attempt arrays, no new harness instances; lookup miss is refused',
                     'not_proven': ['novel semantic generalization', 'canonical Loop Engine integration', 'full graph dataflow', 'frontier parity', 'macOS or Windows execution', 'independent persistent promotion authority']})
    with out.open('x') as stream:
        json.dump({'record_type': 'cold_warm_audit/v1', 'pairs': rows}, stream, indent=2)
        stream.write('\n')
    print(json.dumps(rows, indent=2))
