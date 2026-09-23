"""Independent method oracles and hostile inputs, executed only through the existing bounded sandbox."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import math
import random
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

from jsonschema import Draft202012Validator

FACTORY = Path("/home/username/.le-codex-build/native-factory")
ARTIFACT = FACTORY / "artifacts/mixed-native-originals-2026-09-23"
PACKAGES = ARTIFACT / "prepared-final/packages"
sys.path.insert(0, str(FACTORY / "src"))
spec = importlib.util.spec_from_file_location("existing_bounded_sandbox", ARTIFACT / "verify_packages.py")
sandbox = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sandbox)
RANDOM = random.Random(20260923)


def dag_oracle(value):
    pending = {row["id"]: row for row in value["tasks"]}
    starts, ends = {}, {}
    for _ in range(len(pending)):
        for name, row in pending.items():
            if name not in ends and all(parent in ends for parent in row["depends_on"]):
                starts[name] = max([ends[parent] for parent in row["depends_on"]] or [0])
                ends[name] = starts[name] + row["duration"]
    return {"duration": max(ends.values()), "schedule": [
        {"id": name, "start": starts[name], "finish": ends[name]} for name in sorted(ends)]}


def scc_oracle(value):
    names = sorted(value["vertices"])
    reaches = {(a, b): a == b or [a, b] in value["edges"] for a in names for b in names}
    for middle in names:
        for a in names:
            for b in names:
                reaches[a, b] |= reaches[a, middle] and reaches[middle, b]
    groups = sorted({tuple(b for b in names if reaches[a, b] and reaches[b, a]) for a in names})
    cycles = [group for group in groups if len(group) > 1 or [group[0], group[0]] in value["edges"]]
    return {"components": [list(group) for group in groups], "cyclic_components": [list(group) for group in cycles]}


def pairwise_check(value, output):
    factors = value["factors"]
    required = {(a, av, b, bv) for a, b in itertools.combinations(sorted(factors), 2)
                for av in factors[a] for bv in factors[b]}
    actual = set()
    for row in output.get("cases", []):
        if set(row) != set(factors) or any(row[key] not in factors[key] for key in factors):
            return False
        actual.update((a, row[a], b, row[b]) for a, b in itertools.combinations(sorted(row), 2))
    return required == actual and output.get("total_pairs") == len(required) and output.get("covered_pairs") == len(required)


def accepts(contract, value):
    if not set(contract["required"]) <= set(value):
        return False
    if not contract["allow_extra"] and set(value) - set(contract["fields"]):
        return False
    kinds = {"string": lambda x: type(x) is str, "integer": lambda x: type(x) is int,
             "number": lambda x: type(x) in (int, float), "boolean": lambda x: type(x) is bool,
             "null": lambda x: x is None}
    return all(key not in value or kinds[kind](value[key]) for key, kind in contract["fields"].items())


def contract_check(value, output):
    representatives = [None, False, True, 0, 0.5, "x", [], {}]
    names = sorted(set(value["old"]["fields"]) | set(value["new"]["fields"]) | {"extra"})
    compatible = True
    for included in itertools.product((False, True), repeat=len(names)):
        present = [name for name, selected in zip(names, included) if selected]
        for values in itertools.product(representatives, repeat=len(present)):
            candidate = dict(zip(present, values))
            if accepts(value["old"], candidate) and not accepts(value["new"], candidate):
                compatible = False
                break
        if not compatible:
            break
    return output.get("compatible") is compatible and bool(output.get("breaking_changes")) is not compatible


def bins_check(value, output):
    bins = output.get("bins", [])
    items = {row["id"]: row["size"] for row in value["items"]}
    flattened = [name for row in bins for name in row["item_ids"]]
    if sorted(flattened) != sorted(items):
        return False
    if any(row["used"] != sum(items[name] for name in row["item_ids"]) or row["used"] > value["capacity"] for row in bins):
        return False
    # Reconstruct the first-fit obligation from reported bin membership.
    remaining = [value["capacity"] for _ in bins]
    assigned = {name: number for number, row in enumerate(bins) for name in row["item_ids"]}
    for name in sorted(items, key=lambda key: (-items[key], key)):
        number = assigned[name]
        if any(free >= items[name] for free in remaining[:number]):
            return False
        remaining[number] -= items[name]
    return True


def fd_oracle(value):
    def typed(values):
        return tuple((type(v).__name__, repr(v)) for v in values)
    groups, seen = [], set()
    for index, row in enumerate(value["rows"]):
        determinant = [row[key] for key in value["determinants"]]
        key = typed(determinant)
        if key in seen:
            continue
        seen.add(key)
        indices = [i for i, candidate in enumerate(value["rows"])
                   if typed([candidate[k] for k in value["determinants"]]) == key]
        variants, keys = [], set()
        for i in indices:
            values = [value["rows"][i][k] for k in value["dependents"]]
            if typed(values) not in keys:
                keys.add(typed(values)); variants.append(values)
        if len(variants) > 1:
            groups.append({"determinant": determinant, "dependent_variants": variants, "row_indices": indices})
    return {"violations": groups}


def token_oracle(value):
    units, at, decisions = value["initial_tokens"] * 1000, 0, []
    for row in value["requests"]:
        units = min(value["capacity"] * 1000, units + (row["at_ms"] - at) * value["refill_per_second"])
        allowed = units >= row["tokens"] * 1000
        units -= row["tokens"] * 1000 if allowed else 0
        divisor = math.gcd(units, 1000)
        decisions.append({"id": row["id"], "allowed": allowed,
                          "tokens_after": {"numerator": units // divisor, "denominator": 1000 // divisor}})
        at = row["at_ms"]
    return {"decisions": decisions}


def boolean_oracle(value):
    variables = sorted(value["variables"])
    uncovered, conflicts, clear = [], [], 0
    for bits in range(2 ** len(variables)):
        assignment = {key: bool(bits & (1 << (len(variables) - index - 1))) for index, key in enumerate(variables)}
        matches = []
        for rule in value["rules"]:
            if not any(assignment[key] != expected for key, expected in rule["when"].items()):
                matches.append(rule)
        if not matches:
            uncovered.append(assignment)
        elif len({row["decision"] for row in matches}) > 1:
            conflicts.append({"assignment": assignment, "rule_ids": sorted(row["id"] for row in matches)})
        else:
            clear += 1
    return {"unambiguous_count": clear, "uncovered": uncovered, "conflicts": conflicts}


def rational_expression(depth=0):
    if depth == 2 or RANDOM.random() < 0.35:
        number = RANDOM.randint(-20, 20)
        return str(number), Fraction(number)
    left, lv = rational_expression(depth + 1); right, rv = rational_expression(depth + 1)
    operator = RANDOM.choice(["+", "-", "*", "/"] if rv else ["+", "-", "*"])
    result = {"+": lambda: lv + rv, "-": lambda: lv - rv, "*": lambda: lv * rv, "/": lambda: lv / rv}[operator]()
    return f"({left} {operator} {right})", result


def cases():
    out = {folder.name: [] for folder in PACKAGES.iterdir() if folder.is_dir()}
    def add(name, value, expected=None, check=None, label="independent_generated", reject=False):
        out[name].append({"input": value, "expected": expected, "check": check, "label": label, "reject": reject})
    for run in range(16):
        names = [f"v{i}" for i in range(RANDOM.randint(1, 8))]
        tasks = [{"id": name, "duration": RANDOM.randint(0, 100),
                  "depends_on": [parent for parent in names[:i] if RANDOM.random() < 0.4]} for i, name in enumerate(names)]
        RANDOM.shuffle(tasks); value = {"tasks": tasks}; add("schedule_dag_earliest_times", value, dag_oracle(value))
        value = {"vertices": names, "edges": [[a,b] for a in names for b in names if RANDOM.random() < 0.2]}
        add("find_strongly_connected_components", value, scc_oracle(value))
        value = {"factors": {f"f{i}": [f"x{j}" for j in range(RANDOM.randint(1,3))] for i in range(RANDOM.randint(2,6))}}
        add("cover_pairwise_configuration_values", value, check=pairwise_check)
        value = {key: {"fields": {name: RANDOM.choice(["string","integer","number","boolean","null"])
                                  for name in ["a","b"] if RANDOM.random()<0.65}, "required": [],
                       "allow_extra": RANDOM.choice([False,True])} for key in ("old","new")}
        for contract in value.values(): contract["required"] = [name for name in contract["fields"] if RANDOM.random()<0.4]
        add("compare_primitive_object_contracts", value, check=contract_check)
        capacity = RANDOM.randint(1,50)
        value = {"capacity": capacity, "items": [{"id": f"i{i}","size": RANDOM.randint(1,capacity)} for i in range(RANDOM.randint(0,50))]}
        add("pack_first_fit_decreasing_batches", value, check=bins_check)
        value = {"determinants":["a"],"dependents":["b"],"rows":[{"a":RANDOM.choice([0,False,"0",None]),
                    "b":RANDOM.choice([1,True,"1",None])} for _ in range(RANDOM.randint(0,35))]}
        add("audit_functional_dependency_rows", value, fd_oracle(value))
        capacity = RANDOM.randint(1,50); at = 0; requests=[]
        for i in range(RANDOM.randint(0,30)):
            at += RANDOM.randint(0,1500); requests.append({"id":f"r{i}","at_ms":at,"tokens":RANDOM.randint(1,capacity*2)})
        value={"capacity":capacity,"initial_tokens":RANDOM.randint(0,capacity),"refill_per_second":RANDOM.randint(0,20),"requests":requests}
        add("simulate_exact_token_bucket",value,token_oracle(value))
        variables=[f"x{i}" for i in range(RANDOM.randint(1,6))]
        value={"variables":variables,"rules":[{"id":f"r{i}","when":{v:RANDOM.choice([False,True]) for v in variables if RANDOM.random()<0.5},"decision":RANDOM.choice(["allow","deny","review"])} for i in range(RANDOM.randint(0,15))]}
        add("audit_boolean_rule_coverage",value,boolean_oracle(value))
        frames=[bytes(RANDOM.randrange(256) for _ in range(RANDOM.randint(0,30))) for _ in range(RANDOM.randint(0,20))]
        raw=b"".join(len(frame).to_bytes(2,"big")+frame for frame in frames)
        add("decode_u16_length_prefixed_frames",{"hex":raw.hex().upper()},{"count":len(frames),"frames_hex":[frame.hex() for frame in frames]})
        expression, result = rational_expression()
        add("evaluate_bounded_rational_expression",{"expression":expression},{"numerator":result.numerator,"denominator":result.denominator})
        first,second=RANDOM.choice(["plain","${unexpanded}","$(not-a-command)","é"]),str(run)
        add("resolve_literal_named_template",{"template":"A:${a}|${b}|${a}","variables":{"a":first,"b":second}}, {"text":f"A:{first}|{second}|{first}"})
        document={"a/b":{"~key":[run,False,None]},"":run,"é":first,"é":second}
        add("project_json_pointer_values",{"document":document,"pointers":["/a~1b/~0key/0","/a~1b/~0key/1","/","/é","/é"]},{"values":[run,False,run,first,second]})
    add("schedule_dag_earliest_times",{"tasks":[{"id":f"v{i}","duration":10**9,"depends_on":[f"v{i-1}"] if i else []} for i in range(60)]},check=lambda v,o:o["duration"]==60*10**9,label="maximum_duration_chain")
    add("find_strongly_connected_components",{"vertices":[f"v{i}" for i in range(60)],"edges":[[f"v{i}",f"v{(i+1)%60}"] for i in range(60)]},check=lambda v,o:len(o["components"])==1 and len(o["components"][0])==60,label="maximum_vertex_cycle")
    add("cover_pairwise_configuration_values",{"factors":{f"f{i}":["a","b","c"] for i in range(6)}},check=pairwise_check,label="maximum_factor_grid")
    for expression in ("__import__('os').system('echo unsafe')","9**999999999", "(1).__class__", "1/0", "[1 for x in []]", "True", "1.5"):
        add("evaluate_bounded_rational_expression",{"expression":expression},reject=True,label="hostile_or_unsupported_expression")
    for pointer in ("/a/01","/a/-","/a/+0","/a/1","/a/~2", "#/a/0"):
        add("project_json_pointer_values",{"document":{"a":[1]},"pointers":[pointer]},reject=True,label="invalid_pointer")
    for stream in ("ff", "0002ff", "0401"+"00"*1025, "0000"*257):
        add("decode_u16_length_prefixed_frames",{"hex":stream},reject=True,label="bad_or_excessive_framing")
    add("resolve_literal_named_template",{"template":"${a}","variables":{"a":"${b}"}},{"text":"${b}"},label="replacement_is_literal")
    add("resolve_literal_named_template",{"template":"${a}"*2048,"variables":{"a":"x"*2048}},reject=True,label="bounded_output_expansion")
    for template in ("${}","${bad-name}","${x", "${x}}"):
        # An extra ordinary closing brace after a valid token is literal text, not malformed syntax.
        if template == "${x}}":
            add("resolve_literal_named_template",{"template":template,"variables":{"x":"a"}},{"text":"a}"},label="literal_extra_brace")
        else:
            add("resolve_literal_named_template",{"template":template,"variables":{}},reject=True,label="invalid_placeholder")
    return out


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--report",type=Path,required=True);args=parser.parse_args()
    if args.report.exists(): raise ValueError("Use a new report name")
    population=cases();rows=[]
    inventory=json.loads((ARTIFACT/'prepared-final/items.json').read_text())
    digests={row['reference']['identity']:row['reference']['digest'] for row in inventory['items']}
    raw_invalid=[b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":1e309}',b'\xff',b'{}'+b' '*32768,b'['*100+b'0'+b']'*100,b'{']
    with tempfile.TemporaryDirectory(prefix="independent-native-qa-") as directory:
        directory=Path(directory); input_path=directory/'input.json';runner_path=directory/'runner.py';runner_path.write_text(sandbox.RUNNER)
        for identity, tests in sorted(population.items()):
            package=PACKAGES/identity;script=package/'tools'/f'{identity}.py'
            before=hashlib.sha256(script.read_bytes()).hexdigest()
            input_validator=Draft202012Validator(json.loads((package/'contracts/input.schema.json').read_text()))
            output_validator=Draft202012Validator(json.loads((package/'contracts/output.schema.json').read_text()))
            checks=[]
            for number,test in enumerate(tests):
                payload=json.dumps(test['input'],ensure_ascii=False).encode()
                input_path.write_bytes(payload)
                result=sandbox.run_command(sandbox.command(script,input_path,runner_path),timeout_seconds=4,
                    maximum_output_bytes=65537,environment={'PATH':'/usr/bin:/bin'})
                try: output=json.loads(result.stdout)
                except (ValueError,UnicodeError): output=None
                expected_exit=2 if test['reject'] else 0
                semantic=(output=={'error':'invalid_input'} if test['reject'] else
                          test['check'](test['input'],output) if test['check'] and isinstance(output,dict) else output==test['expected'])
                schema_ok=test['reject'] or output_validator.is_valid(output)
                checks.append({'case':number,'label':test['label'],'input':test['input'],'expected_exit':expected_exit,
                    'input_schema_valid':input_validator.is_valid(test['input']),'actual_exit':result.exit_code,
                    'output':output,'semantic_match':semantic,'output_schema_valid':schema_ok,
                    'elapsed_ms':result.elapsed_ms,'timed_out':result.timed_out,'truncated':result.truncated,
                    'stderr':result.stderr_tail,'passed':result.exit_code==expected_exit and semantic and schema_ok
                                                   and not result.timed_out and not result.truncated})
            for number,payload in enumerate(raw_invalid):
                input_path.write_bytes(payload)
                result=sandbox.run_command(sandbox.command(script,input_path,runner_path),timeout_seconds=4,
                    maximum_output_bytes=65537,environment={'PATH':'/usr/bin:/bin'})
                try: output=json.loads(result.stdout)
                except (ValueError,UnicodeError): output=None
                checks.append({'label':f'hostile_raw_json_{number}','input_sha256':hashlib.sha256(payload).hexdigest(),
                    'input_bytes':len(payload),'actual_exit':result.exit_code,'output':output,'elapsed_ms':result.elapsed_ms,
                    'timed_out':result.timed_out,'truncated':result.truncated,
                    'passed':result.exit_code==2 and output=={'error':'invalid_input'} and not result.timed_out and not result.truncated})
            rows.append({'identity':identity,'package_digest':digests[identity],'script_sha256':before,
                'script_unchanged':hashlib.sha256(script.read_bytes()).hexdigest()==before,
                'payload_digests':{str(file.relative_to(package)):hashlib.sha256(file.read_bytes()).hexdigest() for file in package.rglob('*') if file.is_file()},
                'checks':checks})
            print(identity,len(checks),'checks',sum(not case['passed'] for case in checks),'failures',flush=True)
    record={'seed':20260923,'packages':rows,'model_calls':0,'independent_approval':False,
        'sandbox':'existing bubblewrap command, no network, no host home, clear environment, CPU2s RAM256MiB wall4s',
        'runner_sha256':hashlib.sha256((ARTIFACT/'verify_packages.py').read_bytes()).hexdigest(),
        'all_behavior_checks_passed':all(case['passed'] for row in rows for case in row['checks']),
        'limits':'Fixed seeded sample and explicit boundaries. Schema-contract findings are separately recorded. No native harness loading or three-family approval.'}
    args.report.write_text(json.dumps(record,indent=2,ensure_ascii=True)+'\n')
    print(json.dumps({'packages':len(rows),'cases':sum(len(row['checks']) for row in rows),'failures':sum(not case['passed'] for row in rows for case in row['checks'])}))
    return 0 if record['all_behavior_checks_passed'] else 1


if __name__=='__main__': raise SystemExit(main())
