export const meta = {
  name: 'baltor-library-wave',
  description: 'Generate, precheck, independently critique and repair a wave of multi-file harness working directory component packages as candidates; nothing is approved or published',
  whenToUse: 'To grow the harness intelligence library toward the 10,000 and 100,000 package milestones; the independent review panel admits packages afterwards',
  phases: [
    { title: 'Scout', detail: 'format specification, coverage gap matrix, assignments' },
    { title: 'Generate', detail: 'packages per assignment with executable pre-checks' },
    { title: 'Critique', detail: 'producer-independent critique' },
    { title: 'Repair', detail: 'apply findings, rerun pre-checks' },
    { title: 'Assemble', detail: 'manifest, retrieval probes, proposals draft' },
  ],
}

// args (all paths absolute):
//   repo          checkout whose git database holds main_ref
//   main_ref      for example origin/main
//   out           folder for the wave (created by the agents)
//   wave          wave name, for example wave-6
//   assignments   number of assignments (default 15)
//   per           packages per assignment (default 5)
//   focus         optional free text that steers the gap choice
//   sources       optional free text naming extra specification sources (other worktrees, research folders)
const A = args || {}
if (!A.repo || !A.main_ref || !A.out || !A.wave) throw new Error('args.repo, args.main_ref, args.out and args.wave are required')
const N = A.assignments || 15
const PER = A.per || 5
const S = A.out

const PRE = `You work on the Loop Engine repository (public brand Baltor). Baltor serves harness intelligence: any file a coding or agent harness picks up from its working directory or step configuration (instruction files such as AGENTS.md and CLAUDE.md, skills with scripts, references and assets, tools and reusable code, subagent and command definitions, hooks, plugin declarations, protocol server configurations, rules files, task packets). The backend name for the concrete files is Harness Working Directory Component Files; the component that places them is the Harness Working Directory Compiler. By default every small step runs in its own freshly started harness holding only that step's context, so a small or cheap model can finish it. A package must tell a fresh harness what to do first, what to check and when it is done.

HARD RULES:
- Work only under ${S}/. Read main with 'git -C ${A.repo} show ${A.main_ref}:<path>'; never modify any repository or worktree and run no git command that changes one.
- Every package is original text and code, licensed like the repository (MIT). Outside material may only inspire an original rewrite.
- No network calls from package code, no secret values in any file (environment variable names only), no destructive commands, no model calls. Scripts declare their effects.
- Nothing here is approved, staged in the service or published. The repository's independent review panel (at least three approving reviewers from three model families, none from the producer's family) decides later.
- Plain English for second-language readers, no em or en dashes, no hype, no invented facts.`

phase('Scout')
const scout = await agent(`${PRE}

You are the scout for ${A.wave}. Read on ${A.main_ref}: artifacts/first-party-harness-candidates-*/ (GENERATION-GUIDE.md, READMEs, manifests), artifacts/harness-intelligence-format-pilot-*/, tools/PREPARE-HARNESS-CANDIDATES.md, tools/prepare_harness_candidates.py, tools/candidate_review/ (README, pre-checks, written review criteria), examples/29_intelligence_service/starter-catalogue/ (record versions, families, kinds), and any generation guide under tools/. ${A.sources ? 'Also read: ' + A.sources : ''}
1. Write ${S}/SPEC.md: the package layout the existing tools accept (manifest fields, per-file placement paths per target harness, sha256, file mode, declared effects, licence, targets, search tags), naming rules, size limits, and the exact pre-check commands every generator must run (parsers for JSON, TOML and YAML; the Agent Skills validator if available; every script run against its own test; a secret scan; a network-use scan; hooks executed in a temporary folder). Follow the newest record version; say where you extended it and why.
2. Count the library and every candidate wave by family, kind, file class and domain; write ${S}/GAP-MATRIX.md. Write every existing identity to ${S}/existing-identities.txt.
3. Choose exactly ${N} assignments that fill the biggest gaps and matter most to the north star and its use cases${A.focus ? ' (steer: ' + A.focus + ')' : ''}. Spread them across file classes. Each names ${PER} distinct packages (identity, title, one-sentence purpose) and at least two target harnesses.`, { label: 'scout', phase: 'Scout', schema: {
  type: 'object', properties: {
    spec_path: { type: 'string' }, gap_matrix_path: { type: 'string' }, existing_identities_path: { type: 'string' },
    assignments: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, file_class: { type: 'string' }, domain: { type: 'string' }, harness_targets: { type: 'array', items: { type: 'string' } },
      packages: { type: 'array', items: { type: 'object', properties: { identity: { type: 'string' }, title: { type: 'string' }, purpose: { type: 'string' } }, required: ['identity', 'title', 'purpose'] } } },
      required: ['id', 'file_class', 'domain', 'harness_targets', 'packages'] } } },
  required: ['spec_path', 'gap_matrix_path', 'existing_identities_path', 'assignments'] } })
if (!scout) return { error: 'scout failed' }

const GEN = { type: 'object', properties: { packages: { type: 'array', items: { type: 'object', properties: {
  identity: { type: 'string' }, path: { type: 'string' }, files: { type: 'integer' }, prechecks_passed: { type: 'boolean' }, precheck_log: { type: 'string' }, notes: { type: 'string' } },
  required: ['identity', 'path', 'files', 'prechecks_passed', 'precheck_log'] } } }, required: ['packages'] }
const CRIT = { type: 'object', properties: { verdicts: { type: 'array', items: { type: 'object', properties: {
  identity: { type: 'string' }, recommendation: { type: 'string', enum: ['forward_to_panel', 'repair', 'drop'] }, problems: { type: 'array', items: { type: 'string' } }, strengths: { type: 'string' } },
  required: ['identity', 'recommendation', 'problems'] } } }, required: ['verdicts'] }

const results = await pipeline(
  scout.assignments,
  (a) => agent(`${PRE}

You are generator ${a.id}. Read ${scout.spec_path} and ${scout.gap_matrix_path}; avoid every identity in ${scout.existing_identities_path}. File class '${a.file_class}', domain '${a.domain}', targets ${JSON.stringify(a.harness_targets)}. Build these packages in ${S}/packages/<identity>/ exactly as the specification says: ${JSON.stringify(a.packages)}. Include working scripts and tests where the class calls for them and per-harness placement variants where formats differ. Run every pre-check, save output to PRECHECKS.txt in each package, fix failures and rerun.`, { label: `gen:${a.id}`, phase: 'Generate', schema: GEN }),
  (g, a) => g ? agent(`${PRE}

You are an independent critic for assignment ${a.id}; you did not write these packages. Using ${scout.spec_path} and the written review criteria in tools/candidate_review/ on ${A.main_ref}, open every file, rerun the pre-checks, and judge correctness, safety (effects, secrets, destructive commands, prompt-injection risk), usefulness to a small model in a fresh harness, originality, accuracy of every harness-specific path and format (check current official documentation when unsure), and findability. Recommend 'drop' for anything generic or duplicative. Packages: ${JSON.stringify(g.packages)}`, { label: `critic:${a.id}`, phase: 'Critique', schema: CRIT }).then(c => ({ g, c })) : null,
  (gc, a) => gc ? agent(`${PRE}

You are the repairer for assignment ${a.id}. Apply the critic's findings to the packages in ${S}/packages/; move dropped packages to ${S}/dropped/<identity>/ with a DROPPED.txt reason instead of deleting them; rerun every pre-check. Never argue with a safety finding: fix it or drop the package. Verdicts: ${JSON.stringify(gc.c.verdicts)}`, { label: `repair:${a.id}`, phase: 'Repair', schema: GEN }).then(r => ({ id: a.id, critic: gc.c, repaired: r })) : null,
)
const ok = results.filter(Boolean)
const pkgs = ok.flatMap(r => r.repaired?.packages || [])
log(`${ok.length}/${scout.assignments.length} assignments finished; ${pkgs.length} packages; ${pkgs.filter(p => p.prechecks_passed).length} pass pre-checks`)

phase('Assemble')
const assembled = await agent(`${PRE}

You are the assembler for ${A.wave}. Build ${S}/manifest.json (every package with identity, family, kind, file class, targets and the sha256 of every file) in the structure of the newest existing wave manifest on ${A.main_ref}; write three realistic customer queries per package to ${S}/search-probes.json and measure top-5 findability together with the existing library using the repository's own search evaluation scripts (copies under ${S}/probe/, never the originals), saving ${S}/SEARCH-EVALUATION.json; write ${S}/README.md with counts, pre-check, critique and retrieval results and what remains before admission, plus a proposals.json draft in the shape tools/PREPARE-HARNESS-CANDIDATES.md requires where it fits.
Results: ${JSON.stringify(ok.map(r => ({ id: r.id, packages: r.repaired?.packages?.map(p => ({ identity: p.identity, ok: p.prechecks_passed })), critic: r.critic?.verdicts?.map(v => ({ identity: v.identity, rec: v.recommendation })) }))).slice(0, 60000)}`, { label: 'assemble', phase: 'Assemble' })

return { spec: scout.spec_path, assignments: ok.length, packages: pkgs.length, passing: pkgs.filter(p => p.prechecks_passed).length, assembled }
