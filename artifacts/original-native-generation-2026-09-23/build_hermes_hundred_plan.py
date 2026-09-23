"""Freeze ten original method requests with one hundred useful payload paths.

This creates a plan, not intelligence, approvals, implementations or model calls.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

repository, output = map(Path, sys.argv[1:])
revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repository, text=True).strip()
source_paths = (
    'tools/install_selected_material.py',
    'src/loop_engine/core/instance_instructions.py',
    'src/loop_engine/core/service_runtime/catalogue_packages.py',
    'src/loop_engine/core/harness_fresh_instances.py',
)
sources = {}
for name in (*source_paths, 'LICENSE'):
    raw = (repository / name).read_bytes()
    if raw != subprocess.check_output(['git','show',f'{revision}:{name}'],cwd=repository):
        raise SystemExit('Source is not the committed version: '+name)
    sources[name] = hashlib.sha256(raw).hexdigest()

methods = [
('plan_workspace_file_transitions', 'Plan workspace file transitions',
 'Given base/current/desired inventories keyed by safe relative path and SHA256, emit create, update, noop, delete or conflict without touching the filesystem. Missing is an explicit null value. Permit updates/deletes only if current equals base; changed or foreign current bytes are conflicts. Never infer ownership from a filename. Current=desired is noop even when base differs. Include expected existing digest with each mutation. Reject unsafe paths, duplicates and file-directory/case-fold collisions.',
 'A base=A,current=B,desired=C file is conflict; base=A,current=A,desired=C is update; base=null,current=B,desired=C is conflict; base=A,current=B,desired=B is noop. Never erase an independently modified stale file.', 0),
('assemble_bounded_instruction_sections', 'Assemble bounded instruction sections',
 'Assemble supplied uniquely identified text sections with integer unit costs, mandatory flags, integer priorities and before/after constraints. Validate acyclic precedence. Refuse when mandatory closure exceeds the supplied unit budget; do not truncate essential instructions. Add eligible optional sections by descending priority and input order, only with complete prerequisite closure fitting the budget. Render selected sections in stable topological input order. Unit counts are caller-supplied estimates, never claimed exact model tokens. Return selected, omitted, total units and text with per-section byte ranges.',
 'A mandatory section cost6 with required predecessor cost5 under budget10 must refuse. Unicode byte offsets must reproduce exact section text. Unknown dependency, duplicate identity and cyclic constraints must refuse.', 1),
('resolve_exact_package_dependency_closure', 'Resolve exact package dependency closure',
 'Resolve a bounded supplied package dependency graph from requested package identities. Each dependency includes exact id, revision and digest. Reject missing or mismatched records, identity collisions, cycles and conflicting versions of one logical identity. Return dependencies before consumers in stable input order, complete required effects, aggregate unique-file byte size and unresolved errors. Never fetch or install. File bodies are not supplied; size/hash declarations are inventory data only.',
 'A depends on B, B depends on C must include C,B,A. A supplied same-name B at a different digest must refuse. A dependency effect of network must remain in the output even if the root declares only reads_fs.', 2),
('query_codegraph_change_impact', 'Query code graph change impact',
 'Given a bounded graph snapshot of unique symbol ids, source file digests/ranges and directed depends_on edges (consumer to dependency), report reverse-reachable consumers of changed symbols using breadth-first traversal. Include shortest distance, one deterministic shortest witness path, and evidence for each edge. Validate dangling edges, duplicate symbols, malformed hashes and nonnegative source ranges. Track supplied graph completeness and depth/node limits; truncated output must explicitly report incompleteness. Do not infer absent relationships or claim a parser ran.',
 'If A depends on B and B on C, changing C must affect B then A. A cycle must terminate. Reverse direction must not affect unrelated dependencies. A depth limit1 must mark omitted A rather than claim complete impact.', 2),
('build_permission_scoped_lexical_index', 'Build a permission-scoped lexical index',
 'Build or query a bounded in-memory lexical index from supplied documents with ids, exact text, source hashes and tenant scope. Normalize text with Unicode NFKC and casefold, split on whitespace, and use exact normalized term matches. Query ranking uses number of distinct matched query terms, then total occurrences of matched terms, then lexical document id. Filter tenant scope before ranking/snippets. A caller-supplied minimum distinct-match floor controls abstention. Return index metadata including tokenizer identity and corpus digest. This is a lexical reference engine, no embeddings, semantic similarity or production benchmark claims.',
 'A forbidden tenant document with all query terms must never appear in result ids/snippets/counts. Empty/no-match queries return zero results. Changing source text invalidates a supplied corpus digest. Stable ties sort by id.', 2),
('validate_focused_attempt_handoff', 'Validate a focused attempt handoff',
 'Validate a supplied handoff containing task id, attempt id, objective, first actions, immutable inputs, required output paths, authority reference and ordered event records. Events carry contiguous sequence numbers and explicit running, failed, cancelled, candidate or accepted state. Accepted requires a validator identity and evidence digest; candidates cannot self-accept. Return a concise explicit startup briefing and validated passive state. Do not resume native conversations, create a new runtime class, grant effects or infer successful external actions from timeout. Unknown effects remain unknown.',
 'Reject a sequence gap, duplicate sequence and accepted state without validator evidence. Preserve unknown external-effect outcome. Repeated attempt id cannot become a new attempt. Briefing must contain the first action and output contract.', 1),
('render_secret_reference_connections', 'Render secret-reference connections',
 'Render a narrow supplied HTTPS remote MCP connection profile for Codex project TOML and Claude project JSON. Input contains server id, HTTPS URL, environment variable NAME and target profile. Never accept secret values. Codex uses bearer_token_env_var; Claude uses an Authorization Bearer ${NAME} environment reference. Use safe serialization rather than textual interpolation into JSON/TOML syntax. Do not connect, authenticate, enable trust, start a server, promise protocol support or emit all profiles at once. Validate URL with no userinfo, fragment or non-HTTPS scheme; restrict ids and environment names. Credentials are resolved only by the selected native host at runtime.',
 'The output must contain the supplied variable name but no secret value. A URL with userinfo and newline-bearing variable name must refuse. Parsing emitted JSON/TOML must reproduce the exact URL. Unsupported profile must refuse.', 3),
('check_tabular_transformation_invariants', 'Check tabular transformation invariants',
 'Check a supplied before/after dataset and explicit contract for id field, preserved fields, allowed changed fields and integer total fields. Require unique nonempty string ids and exact id-set/cardinality preservation. Compare preserved values recursively using JSON type-aware equality so true does not equal1. Sum declared integral fields with arbitrary precision and reject nonintegral values/booleans. Return structured violations with row ids and field names but no echoed private field values. Do not claim complete semantic correctness beyond declared invariants.',
 'A missing row, duplicate id, unauthorized field mutation or changed integer sum must reject. Reordering rows alone passes. Preserved true changed to1 must reject. Negative integers are valid totals.', 2),
('select_traceable_context_evidence', 'Select traceable context evidence',
 'Create a real Agent Skill that helps a harness select traceable evidence for a focused question. Include a deterministic supplied-record helper that validates source ids, revisions/digests, exact supporting spans and explicit contradiction groups, then chooses records within a declared byte budget by required flag, priority and stable input order. An unresolved contradiction must remain visible in the result; no factual claim is automatically proved by a source link. The skill guides model-led relevance decisions separately from deterministic integrity checks and states first actions, limits, output contract and abstention. Do not auto-read unrelated repository data.',
 'Required evidence over budget refuses. A quote not matching the supplied exact source span refuses. Selecting only one side of a declared contradiction must mark the missing side unresolved. Skill metadata is valid and references existing bundled files.', 1),
('review_json_with_native_claude_plugin', 'Review JSON through a native Claude plugin',
 'Create a candidate Claude Code plugin named baltor-json-review. Manifest at .claude-plugin/plugin.json, command at commands/review-json.md, native agent at agents/json-reviewer.md, and a complete scripts/check_json.py helper. The helper reads one bounded JSON value on stdin, rejects duplicate object keys/nonfinite numbers/depth>32 and reports structure counts (objects, arrays, strings, numbers, booleans, nulls) and maximum depth. It never reads paths, writes, calls network or executes subprocesses. Command/agent explain explicit plugin installation, read-only review and invocation using caller-authorized input; no automatic installation or permission bypass. AGENTS.md describes the package and every first step. Plugin activation is explicit and version-qualified, not promised by a bare directory copy.',
 'A nested object with array [true,null,2,"x"] must count each type correctly and treat boolean separately. Duplicate JSON keys and depth33 must refuse. Plugin references only bundled files, excludes hook side effects and does not claim independent approval.', 3),
]

common = ' All implementations use Python3.10+ standard library only, no eval/exec, dynamic imports, network, filesystem mutation or subprocesses inside the helper. Read a maximum1MiB UTF-8 JSON request from stdin with duplicate-key and nonfinite-number refusal. Emit one bounded JSON success/refused object, stable error codes and no tracebacks. Reject booleans where integers are required. Tests may launch this exact helper in a caller-supplied sandbox. Write complete useful original contents, no placeholders or invented results. Keep examples small and independently calculable.'
def file(path,role,purpose,media=None):
    return {'path':path,'role':role,'media_type':media or ('text/x-python' if path.endswith('.py') else 'application/json' if path.endswith('.json') else 'text/markdown'),'purpose':purpose}
rows=[]
for identity,title,brief,acceptance,source_index in methods:
    helper=f'tools/{identity}.py'
    files=[file('AGENTS.md','instruction_file','Focused task, exact first action, helper invocation, contract and refusal rules; this file guides but never grants permissions.'),
           file(helper,'executable_tool','Complete deterministic helper. '+brief+common),
           file('contracts/input.schema.json','configuration','Closed JSON Schema2020-12 for the exact input contract, bounded sizes, no remote refs.'),
           file('contracts/output.schema.json','configuration','Closed JSON Schema2020-12 for success/refusal and all output fields; no remote refs.'),
           file('examples/input.json','skill_asset','Small valid request with an independently understandable answer.'),
           file('examples/output.json','skill_asset','Exact expected response to the bundled input, obtained from reasoning, not a claim that it was executed.'),
           file('fixtures/acceptance.json','skill_asset','Structured positive/negative cases with expected outputs or error codes, including supplied counterexamples.'),
           file(f'tests/test_{identity}.py','executable_tool','Meaningful unittest checks using bundled fixture cases, invalid inputs and a known-wrong implementation case; do not install dependencies.'),
           file('references/method.md','skill_reference','Explain algorithm, conventions, bounds, first actions, known-wrong approach, and limitations. No performance or independent-review claims.'),
           file('references/compatibility.json','configuration','Passive metadata: exact intended host entrypoint, explicit/helper discovery, Python requirement, requested effects, automatic discovery limits and status candidate. Do not claim unperformed native tests.')]
    kind='tool'
    styles=['codex','claude','opencode','pi']
    if identity=='select_traceable_context_evidence':
        kind='skill'
        skill='.agents/skills/select-traceable-context-evidence'
        files[1]['path']=f'{skill}/scripts/select_evidence.py'
        files[-1]=file(f'{skill}/SKILL.md','skill_definition','Valid Agent Skills metadata name select-traceable-context-evidence, precise applicability and workflow. Reference bundled scripts/select_evidence.py and package-root contracts/examples with correct relative paths. Explain model-led relevance versus deterministic checks; no effects granted by prose.')
    if identity=='review_json_with_native_claude_plugin':
        styles=['claude']
        files=[files[0],file('.claude-plugin/plugin.json','plugin_manifest','Valid minimal Claude plugin manifest: name baltor-json-review, version0.1.0, accurate description; only supported fields, no secrets.'),
               file('commands/review-json.md','command','Native command with valid description frontmatter, explicit read-only validation procedure, approved input handling and scripts/check_json.py reference.'),
               file('agents/json-reviewer.md','subagent_definition','Native subagent with valid name/description and read-only tools; no bypassPermissions; describe helper and scope.'),
               file('scripts/check_json.py','executable_tool','Complete helper. '+brief+common), files[2],files[3],files[6],files[7],files[8]]
    rows.append({'id':identity,'title':title,'purpose':brief.split('. ')[0]+'.','sources':[source_paths[source_index]],'layer':'code','family':'original_native_tool','search_tags':[title.lower(),'harness workspace','native package','python'],'tags':{'domain':['software'],'language':['en']},'symbols':[identity],'declared_effects':['reads_fs','spawns_process'],'kind':kind,'styles':styles,'dependencies':['python>=3.10'],'brief':brief+common,'acceptance':[acceptance,'All references and helpers are present. Candidate-only; no automatic promotion or external effect.','Every file has a useful declared role. No duplicate filler, pseudocode, credentials, external runtime downloads or unverified benchmark claims.'],'files':files,'opportunity':'Original method responding to the owner\'s September23 request for flexible harness directories, compiler engines, tool/context distinction, code graphs, indexes and100 useful files. The first-party source records the relevant existing boundary; it is not proof that this newly generated implementation works.'})
assert len(rows)==10 and sum(len(row['files']) for row in rows)==100
plan={'record_type':'original_native_generation_plan/v1','source_revision':revision,'license':{'expression':'MIT','path':'LICENSE','sha256':sources.pop('LICENSE')},'sources':sources,'methods':rows}
raw=(json.dumps(plan,indent=2,ensure_ascii=False)+'\n').encode()
output.parent.mkdir(parents=True,exist_ok=True)
with output.open('xb') as stream: stream.write(raw)
print(json.dumps({'path':str(output),'sha256':hashlib.sha256(raw).hexdigest(),'source_revision':revision,'logical_packages_planned':10,'payload_files_planned':100,'generated':0}))
