"""Runtime probe of the sealed novel population: spec-faithful solutions vs. the cases."""
import json, subprocess, sys, hashlib
from pathlib import Path
sys.path.insert(0, 'examples/25_host_runtime')
import generalization_probe as probe
from novel_task_population import task_population
import novel_task_offline_check as offline

S = Path(sys.argv[1]); RUNS = S / 'novel_runs'
tasks = {t.task_id: t for t in task_population()}

def local_runner(run_root, image):
    r = subprocess.run([sys.executable, '-B', 'probe.py'], cwd=run_root, capture_output=True, text=True, timeout=120)
    return {'ok': r.returncode == 0, 'exit_code': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr,
            'error_code': None, 'output_truncated': False, 'image': image, 'backend': 'local-host-python'}

def run_solution(task, source, label):
    root = RUNS / (task.task_id + '-' + label); root.mkdir(parents=True, exist_ok=True)
    (root / 'solution.py').write_text(source); (root / 'probe.py').write_text(probe.WORKER)
    (root / 'probe-input.json').write_text(probe.canonical({'entrypoint': task.entrypoint, 'cases': [
        {k: c[k] for k in ('case_id', 'arguments', 'python_constants') if k in c} for c in task.cases]}))
    ex = local_runner(root, probe.IMAGE); comp = probe.evaluate(task, ex)
    failed = [c['case_id'] for c in comp['checks'] if not c['passed']]
    print(f"  {task.task_id:18s} [{label:28s}] passed={comp['passed']!s:5s} kind={comp['failure_kind'] or '-':18s} failed={failed}")
    if comp['failure_kind'] == 'execution_failed': print('    stderr:', ex['stderr'][-400:])
    return comp

GRID = '''import heapq
def path_cost(grid_text):
    if not isinstance(grid_text, str) or not grid_text: raise ValueError
    rows = [line.split(SEP) for line in grid_text.split('\\n')]
    w = len(rows[0])
    if any(len(r) != w for r in rows): raise ValueError
    grid = []
    for r in rows:
        cells = []
        for c in r:
            if c == 'X': cells.append(None)
            elif c.isascii() and c.isdigit(): cells.append(int(c))
            else: raise ValueError
        grid.append(cells)
    if grid[0][0] is None and grid[-1][-1] is None: raise ValueError
    if grid[0][0] is None or grid[-1][-1] is None: return None
    h = len(grid); best = set(); heap = [(grid[0][0], 0, 0)]
    while heap:
        cost, r, c = heapq.heappop(heap)
        if (r, c) in best: continue
        best.add((r, c))
        if (r, c) == (h - 1, w - 1): return cost
        for dr, dc in ((0, 1), (1, 0)):
            nr, nc = r + dr, c + dc
            if nr < h and nc < w and grid[nr][nc] is not None and (nr, nc) not in best:
                heapq.heappush(heap, (cost + grid[nr][nc], nr, nc))
    return None
'''
CAL = '''import json, re
def free_minutes(busy_text):
    if not isinstance(busy_text, str): raise ValueError
    try: pairs = json.loads(busy_text)
    except ValueError: raise ValueError
    if not isinstance(pairs, list): raise ValueError
    covered = [False] * 1440
    for pair in pairs:
        if not isinstance(pair, list) or len(pair) != 2: raise ValueError
        vals = []
        for v in pair:
            if not isinstance(v, str) or not re.fullmatch(r'[0-9]{2}:[0-9]{2}', v): raise ValueError
            h, m = int(v[:2]), int(v[3:])
            if h > 23 or m > 59: raise ValueError  # "minutes 0 through 1439"; "times outside the day" -> ValueError
            vals.append(h * 60 + m)
        if vals[1] < vals[0]: raise ValueError
        for i in range(vals[0], vals[1]): covered[i] = True
    return 1440 - sum(covered)
'''
STATE = '''import re
def final_state(text):
    if not isinstance(text, str) or not text: raise ValueError
    if text != text.strip(' ') or '  ' in text: raise ValueError
    acc = 0
    for cmd in text.split(' '):
        if cmd == 'd': acc *= 2
        elif cmd == 'r': acc = 0
        elif re.fullmatch(r'[+-]?[0-9]+', cmd): acc += int(cmd)  # "optionally signed ASCII decimal integer"
        else: raise ValueError
    return acc
'''
FLAT = '''def spiral_sum(matrix):
    if not isinstance(matrix, list): raise ValueError
    if not matrix: return 0
    if any(not isinstance(r, list) for r in matrix): raise ValueError
    w = len(matrix[0])
    if any(len(r) != w for r in matrix): raise ValueError
    for r in matrix:
        for v in r:
            if type(v) is not int: raise ValueError
    return sum(v for r in matrix for v in r)   # no spiral walk at all
'''
print('== A. spec-faithful vs case-faithful solutions ==')
run_solution(tasks['grid_path_cost'], GRID.replace('SEP', "'.'"), 'period_split_per_prompt')
run_solution(tasks['grid_path_cost'], GRID.replace('SEP', "','"), 'comma_split_per_cases')
run_solution(tasks['calendar_slots'], CAL, 'reject_2400_per_prompt')
run_solution(tasks['state_machine'], STATE, 'accept_leading_zero_per_prompt')
run_solution(tasks['matrix_spiral'], FLAT, 'flat_sum_no_spiral')

print('== B. reference-implementation defects (offline check oracles) ==')
try:
    print('  ref_path_cost("X,1\\n1,1") ->', offline.ref_path_cost('X,1\n1,1'))
except Exception as e:
    print('  ref_path_cost("X,1\\n1,1") raised', type(e).__name__, '(prompt says: no path -> return None)')
print('  ref_free_minutes("[[\\"09:00\\",\\"09:00\\"]]") ->', end=' ')
try: print(offline.ref_free_minutes('[["09:00","09:00"]]'))
except Exception as e: print('raised', type(e).__name__, '(prompt only forbids end BEFORE start)')
print('  ref_final_state("+5") ->', end=' ')
try: print(offline.ref_final_state('+5'))
except Exception as e: print('raised', type(e).__name__, '(prompt: "optionally signed")')

print('== C. poly_hash "unicode" case actually hashes an ASCII escape sequence ==')
uc = [c for c in tasks['poly_hash'].cases if c['case_id'] == 'unicode'][0]
arg = uc['arguments'][0]
print('  argument repr:', repr(arg), 'len:', len(arg), 'code points:', [ord(ch) for ch in arg], 'expected:', uc['expected'])
print('  ref_poly_hash(arg, 97) =', offline.ref_poly_hash(arg, 97), '| ref_poly_hash("\\u00e9", 97) =', offline.ref_poly_hash('é', 97))

print('== D. word_square duplicate / misnamed cases ==')
ws = {c['case_id']: c for c in tasks['word_square'].cases}
print('  three_by_three_square:', ws['three_by_three_square']['arguments'], '->', ws['three_by_three_square']['expected'])
print('  false_case           :', ws['false_case']['arguments'], '->', ws['false_case']['expected'])
print('  identical arguments+expected:', ws['three_by_three_square']['arguments'] == ws['false_case']['arguments'] and ws['three_by_three_square']['expected'] == ws['false_case']['expected'])
print('  a real 3x3 word square ["cat","are","ted"] ->', offline.ref_is_word_square(['cat', 'are', 'ted']), '(no positive 3x3 case exists in the population)')

print('== E. provenance: what the campaign manifest digest-binds ==')
import novel_task_campaign as camp
m = camp.campaign_manifest(tuple(tasks.values()), model_route='cloud.default', model_id='deepseek-v4-flash:0731')
print('  manifest.source_digest is sha256 of:', 'generalization_probe.py' if m['source_digest'] == hashlib.sha256(Path(probe.__file__).read_bytes()).hexdigest() else 'UNKNOWN')
print('  novel_task_population.py digest recorded anywhere in manifest:', hashlib.sha256(Path('examples/25_host_runtime/novel_task_population.py').read_bytes()).hexdigest() in probe.canonical(m))
print('  novel_task_campaign.py digest recorded anywhere in manifest:', hashlib.sha256(Path('examples/25_host_runtime/novel_task_campaign.py').read_bytes()).hexdigest() in probe.canonical(m))
print('  RUNNER_DIGEST_NOTE used anywhere in manifest:', camp.RUNNER_DIGEST_NOTE in probe.canonical(m))
print('  case counts per task:', {t: len(x.cases) for t, x in tasks.items()}, 'total', sum(len(x.cases) for x in tasks.values()))
