"""Exercise installed additional CLIs through the same production process boundary."""
from dataclasses import asdict
import json
from pathlib import Path
import sys
import argparse
from loop_engine.core.harness_configuration import load_harness_binding
from loop_engine.core.harness_process import HarnessProcessRequest, run_harness_process

ROOT = Path('/home/username/loop-engine')
parser = argparse.ArgumentParser()
parser.add_argument('--out', type=Path, default=Path(__file__).resolve().parent / 'additional-core')
parser.add_argument('harnesses', nargs='+')
args = parser.parse_args()
OUT = args.out.resolve()
if not OUT.is_relative_to(ROOT):
    raise SystemExit('all trial outputs must be inside loop-engine')
OUT.mkdir(exist_ok=True)
for name in args.harnesses:
    work = OUT / name
    work.mkdir(exist_ok=False)
    binding = load_harness_binding(str(ROOT / 'embodiments' / name / 'harness.json'),
        work_root=str(work), socket_directory=str(ROOT / '.loop-engine-dev/hs'))
    calls = []
    def broker(payload):
        calls.append(payload)
        return {'id':'actual-protocol-fixture','object':'chat.completion','created':1,
            'model':payload['model'],'choices':[{'index':0,'message':{'role':'assistant',
                'content':'{"answer":42}'},'finish_reason':'stop'}],
            'usage':{'prompt_tokens':11,'completion_tokens':5,'total_tokens':16}}
    observed = run_harness_process(HarnessProcessRequest(binding._adapter.spec,
        'Return exactly the JSON object {"answer":42}. Do not call tools.',
        'fixture-model', 4096, 1024, 60, str(work), context_capacity=131072,
        socket_directory=str(ROOT / '.loop-engine-dev/hs')), broker)
    value = {'harness':name,'result':asdict(observed),'local_requests':calls,
             'live_provider_calls':0,'ok':observed.ok}
    (OUT / (name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({'harness':name,'ok':observed.ok,'errors':observed.errors,
                      'requests':len(calls),'output':observed.output}), flush=True)
