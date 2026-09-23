export const meta = {
  name: 'baltor-harness-discovery',
  description: 'Find coding and agent harnesses round by round until a round finds almost nothing new, then write a verified profile of the files and settings each one reads',
  whenToUse: 'To refresh the Harness File Profile data behind the Harness Working Directory Compiler, and to decide which harnesses to support, wrap or fork',
  phases: [
    { title: 'Discover', detail: 'known list, then finder rounds until dry' },
    { title: 'Profile', detail: 'one profile per harness, verified when relevant' },
    { title: 'Synthesize', detail: 'landscape, profile data, fork-or-wrap' },
  ],
}

// args (all paths absolute):
//   repo, main_ref   checkout and main reference to read existing research from
//   out              folder for this run
//   known_sources    free text naming where existing harness research lives
//   cap              maximum number of harnesses to profile (default 60); the rest are logged, never silently dropped
//   max_rounds       maximum discovery rounds (default 3)
//   verify_from      minimum relevance (1 to 5) that gets an adversarial verifier (default 4)
const A = args || {}
if (!A.repo || !A.main_ref || !A.out) throw new Error('args.repo, args.main_ref and args.out are required')
const S = A.out
const CAP = A.cap || 60
const ROUNDS = A.max_rounds || 3
const VFROM = A.verify_from || 4

const PRE = `You work on the Loop Engine repository (public brand Baltor). Customers run their own harness; Baltor places the files each step needs into that harness's working directory through the Harness Working Directory Compiler, driven by one Harness File Profile per harness. Never modify any repository or worktree; read main with 'git -C ${A.repo} show ${A.main_ref}:<path>'. Write only under ${S}/. No provider writes, no model calls, no secrets. Web search and fetch are allowed; prefer primary sources and record versions and dates. Label findings ran, source or claim. Plain English, no em dashes.`

const CAND = { type: 'object', properties: { harnesses: { type: 'array', items: { type: 'object', properties: {
  name: { type: 'string' }, url: { type: 'string' }, kind: { type: 'string' }, one_line: { type: 'string' }, relevance: { type: 'integer', minimum: 1, maximum: 5 } },
  required: ['name', 'url', 'kind', 'one_line', 'relevance'] } } }, required: ['harnesses'] }
const norm = (s) => String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, '')

phase('Discover')
const known = await agent(`${PRE}\n\nList every harness the repository's research already covers, with the research path in one_line. ${A.known_sources ? 'Look in: ' + A.known_sources : 'Look in docs/research/ and docs/architecture/ on ' + A.main_ref + '.'}`, { label: 'discover:known', phase: 'Discover', schema: CAND })
const seen = new Map()
for (const h of (known?.harnesses || [])) seen.set(norm(h.name), { ...h, known: true })

const MODES = [
  'GitHub repository search, topics and recently active repositories for coding agents, terminal agents and agent clients',
  'package registries (npm, PyPI, crates.io, Homebrew, Go modules) and editor marketplaces',
  'registries and benchmarks that list agent harnesses: the Agent Client Protocol agent list, Harbor and Terminal-Bench integrations, SWE-bench scaffolds, MCP client lists, curated awesome lists',
  'recent announcements: vendor blogs and changelogs, forums, model vendors releasing their own harnesses, open-source forks of major harnesses',
]
let dry = 0, round = 0
while (dry < 1 && round < ROUNDS) {
  round++
  const names = [...seen.values()].map(h => h.name).join(', ')
  const found = (await parallel(MODES.map((m, i) => () => agent(`${PRE}\n\nFind coding or agent harnesses with this search mode only: ${m}. Exclude: ${names}. Return up to 25 real, current ones with a primary URL.`, { label: `discover:r${round}:m${i + 1}`, phase: 'Discover', schema: CAND })))).filter(Boolean).flatMap(r => r.harnesses)
  const fresh = found.filter(h => !seen.has(norm(h.name)))
  fresh.forEach(h => seen.set(norm(h.name), { ...h, known: false }))
  log(`round ${round}: ${found.length} found, ${fresh.length} new, ${seen.size} total`)
  if (fresh.length < 3) dry++
}
const all = [...seen.values()].sort((a, b) => (b.relevance || 0) - (a.relevance || 0))
if (all.length > CAP) log(`profiling the top ${CAP} of ${all.length}; not profiled: ${all.slice(CAP).map(h => h.name).join(', ')}`)

const PROFILE = { type: 'object', properties: {
  name: { type: 'string' }, repo_url: { type: 'string' }, docs_url: { type: 'string' }, license: { type: 'string' }, kind: { type: 'string' },
  latest_version: { type: 'string' }, last_activity: { type: 'string' }, headless_command: { type: 'string' }, event_stream: { type: 'string' },
  acp_support: { type: 'string' }, instruction_files: { type: 'string' }, skills: { type: 'string' }, subagents: { type: 'string' }, commands: { type: 'string' },
  hooks: { type: 'string' }, rules_files: { type: 'string' }, plugins: { type: 'string' }, mcp_config: { type: 'string' }, settings_and_permissions: { type: 'string' },
  local_models: { type: 'string' }, session_resume: { type: 'string' }, sandbox: { type: 'string' }, fork_notes: { type: 'string' },
  sources: { type: 'array', items: { type: 'string' } }, evidence_notes: { type: 'string' } },
  required: ['name', 'repo_url', 'license', 'kind', 'headless_command', 'instruction_files', 'skills', 'mcp_config', 'local_models', 'sources'] }

phase('Profile')
const profiles = (await pipeline(
  all.slice(0, CAP),
  (h) => agent(`${PRE}\n\nProfile '${h.name}' (${h.url}; ${h.one_line}) from its current documentation and source. Exact file names, paths and formats with the version read; 'none' for absent features and 'unknown' when not found. Save ${S}/harness-profiles/${norm(h.name)}.md.`, { label: `profile:${h.name}`.slice(0, 60), phase: 'Profile', schema: PROFILE }),
  (p, h) => (p && (h.relevance || 0) >= VFROM)
    ? agent(`${PRE}\n\nAdversarially verify this profile against the harness's own current documentation and source (instruction files, skills path, protocol server configuration path and key syntax, hooks, headless command, local models). Return the corrected profile; start evidence_notes with VERIFIED: or CORRECTED:.\n${JSON.stringify(p)}`, { label: `verify:${h.name}`.slice(0, 60), phase: 'Profile', schema: PROFILE })
    : (p ? { ...p, evidence_notes: 'UNVERIFIED: ' + (p.evidence_notes || '') } : null),
)).filter(Boolean)

phase('Synthesize')
const landscape = await agent(`${PRE}\n\nWrite ${S}/HARNESS-LANDSCAPE.md and ${S}/harness-profiles.json: a table of every harness, the groups that share conventions (which the compiler exploits), which to support first and why, and the Harness File Profile fields the compiler needs, checked against the compiler design on ${A.main_ref} (docs/architecture/HARNESS-WORKING-DIRECTORY-COMPILER-*.md).\nProfiles: ${JSON.stringify(profiles).slice(0, 150000)}`, { label: 'synth:landscape', phase: 'Synthesize' })
const fork = await agent(`${PRE}\n\nUsing ${S}/harness-profiles.json, write ${S}/FORK-OR-WRAP.md: which open-source harnesses Baltor should fork, wrap without forking, or support only through the compiler, judged on licence, fit for a fresh harness per step, injection points, local and cheap model support, code size, upstream release pace and fork maintenance cost, and security model; then what would falsify each recommendation.`, { label: 'synth:fork-or-wrap', phase: 'Synthesize' })
return { found: all.length, profiled: profiles.length, landscape, fork }
