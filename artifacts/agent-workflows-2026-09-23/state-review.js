export const meta = {
  name: 'baltor-state-review',
  description: 'Read-only review of the repository, the live service, the roadmap and every concurrent agent session, with adversarial verification, one synthesis and a completeness critic',
  whenToUse: 'At the start of a session, after a long gap, or when several agents have worked in parallel and nobody knows the true state',
  phases: [
    { title: 'Read', detail: 'parallel read-only readers' },
    { title: 'Verify', detail: 'one adversarial verifier per reader' },
    { title: 'Synthesize', detail: 'current state, comparison and next work' },
    { title: 'Critique', detail: 'completeness critic' },
  ],
}

// args (all paths absolute):
//   repo            shared checkout whose git database holds the fetched main reference
//   main_ref        the reference to treat as main, for example origin/main
//   out             folder for every report this run writes
//   sessions        plain-text description of the concurrent writers and where their transcripts are
//   extracted       optional path of a file with every owner prompt already extracted
//   live_hosts      optional list of public hostnames to probe read-only
//   extra_readers   optional list of {key, prompt} added to the default readers
const A = args || {}
if (!A.repo || !A.main_ref || !A.out || !A.sessions) throw new Error('args.repo, args.main_ref, args.out and args.sessions are required')
const OUT = A.out
const HOSTS = (A.live_hosts || []).join(', ') || 'none given; skip live probing'

const PREAMBLE = `You are one agent in a read-only review of the Loop Engine repository (public brand Baltor).

HARD RULES:
- Read-only toward every repository and worktree. No git command that changes a worktree, index or reference (no checkout, switch, stash, reset, restore, commit, merge, rebase, cherry-pick, apply, push, worktree add or remove, clean). Read main with 'git -C ${A.repo} show ${A.main_ref}:<path>'.
- Write only under ${OUT}/. Scratch experiments go under ${OUT}/lab/<your key>/.
- No deploys, no provider writes, no email, no model calls, no printing of secrets. Read-only HTTP GET or HEAD against these public hostnames only: ${HOSTS}. Web search and fetch of public pages are allowed.

CONCURRENT WRITERS AND TRANSCRIPTS: ${A.sessions}
${A.extracted ? `Every owner prompt and agent turn report is pre-extracted at ${A.extracted}; grep it before opening raw transcripts, and stream-parse raw transcripts with a script, never print them whole.` : ''}

EVIDENCE: label every fact verified, inferred, claimed-unverified, disputed or missing. Quote paths and commit identifiers. Plain English, no em dashes. Write the full report as Markdown to the path you are given, then return the structured summary.`

const READER = {
  type: 'object',
  properties: {
    report_path: { type: 'string' },
    summary: { type: 'string' },
    facts: { type: 'array', items: { type: 'object', properties: {
      claim: { type: 'string' },
      status: { type: 'string', enum: ['verified', 'inferred', 'claimed-unverified', 'disputed', 'missing'] },
      evidence: { type: 'string' } }, required: ['claim', 'status', 'evidence'] } },
    unfinished: { type: 'array', items: { type: 'object', properties: {
      item: { type: 'string' }, owner_now: { type: 'string' }, blocker: { type: 'string' },
      next_action: { type: 'string' }, collision_risk: { type: 'string' }, evidence: { type: 'string' } },
      required: ['item', 'owner_now', 'next_action', 'evidence'] } },
    new_topics: { type: 'array', items: { type: 'string' } },
    contradictions: { type: 'array', items: { type: 'string' } },
  },
  required: ['report_path', 'summary', 'facts', 'unfinished', 'new_topics', 'contradictions'],
}

const VERDICTS = {
  type: 'object',
  properties: {
    checked: { type: 'array', items: { type: 'object', properties: {
      claim: { type: 'string' }, verdict: { type: 'string', enum: ['confirmed', 'refuted', 'partly', 'unverifiable'] },
      correction: { type: 'string' }, evidence: { type: 'string' } }, required: ['claim', 'verdict', 'evidence'] } },
    missed: { type: 'array', items: { type: 'string' } },
  },
  required: ['checked', 'missed'],
}

const DEFAULT_READERS = [
  { key: 'main-live', prompt: `FOCUS: what is on main and what is live. Group recent commits on ${A.main_ref} by line of work with their continuous integration result (gh run list and gh run view, read-only). Check that the current deployment section of docs/architecture/MVP-CLIENT-SERVER.md records the newest release, its revision, image digest and rollback image. Probe the live hostnames read-only and compare them with the newest dated handoff's decisions.` },
  { key: 'roadmap', prompt: `FOCUS: the task authority. Load docs/roadmap/roadmap.yaml on ${A.main_ref} with a YAML parser; list every package and step that is not done, with status, owner, dependencies and evidence. Compare with the ordered work in the newest dated handoff under docs/context/ and decide for each item: done, in flight (by whom), not started, or blocked (on what). Diff the roadmap between ${A.main_ref} and any uncommitted copies named in the concurrent-writer description.` },
  { key: 'sessions', prompt: `FOCUS: every concurrent agent session. For each session named in the concurrent-writer description: the owner's requests in order, what the session did, decided and claimed, its current task and worktree, what it owns, its blockers, and which of its claims do not match verifiable state. Map every uncommitted path in the shared checkout ${A.repo} to the session that wrote it and classify it: already on main, worth carrying, conflicting, or obsolete.` },
  { key: 'docs', prompt: `FOCUS: documents and artifacts. Inventory records dated in the last three days on ${A.main_ref} and in uncommitted copies; mark each current, superseded or stale. Find contradictions across README.md, AGENTS.md, CLAUDE.md, ASTRA.md, docs/context/START-HERE.md, docs/context/CODEX-START-HERE.md, docs/README.md, the newest handoff and the current deployment section.` },
  { key: 'topics', prompt: `FOCUS: a register of every new topic, tool, repository, standard or idea the owner raised in the last three days, with who raised it and when, the existing research (paths), its depth (none, shallow, documentation only, hands-on trial), the recorded decision and the remaining gap. Do not do the research.` },
  { key: 'nomenclature', prompt: `FOCUS: naming decisions. List every naming decision or preference the owner made recently, with exact words and time; where it is recorded (terminology.yaml and src/loop_engine/data/terminology.yaml on ${A.main_ref} and uncommitted copies, AGENTS.md, docs/guides/developer-language.md, docs/guides/product-style-guide.md); whether the copies agree; where older terms remain; and one proposed resolution per conflict.` },
]
const READERS = DEFAULT_READERS.concat(A.extra_readers || [])

phase('Read')
const results = await pipeline(
  READERS,
  (r) => agent(`${PREAMBLE}\n\n${r.prompt}\nWrite the report to ${OUT}/${r.key}.md.`, { label: `read:${r.key}`, phase: 'Read', schema: READER }),
  (rep, r) => rep ? agent(`${PREAMBLE}

You are an adversarial verifier for the '${r.key}' reader, whose report is ${rep.report_path}. Pick the 12 to 18 claims that matter most for deciding what to do next (anything that says something is live, done, merged, passing, blocked, owned or absent) and try to refute each by checking the source yourself. Default to 'unverifiable' when you could not check. List important facts the reader missed.
Claims: ${JSON.stringify({ facts: rep.facts, unfinished: rep.unfinished, contradictions: rep.contradictions }).slice(0, 30000)}`, { label: `verify:${r.key}`, phase: 'Verify', schema: VERDICTS }).then(v => ({ key: r.key, rep, v })) : null,
)
const ok = results.filter(Boolean)
log(`${ok.length}/${READERS.length} readers finished with verification`)

phase('Synthesize')
const bundle = ok.map(x => JSON.stringify({ key: x.key, report_path: x.rep.report_path, summary: x.rep.summary, unfinished: x.rep.unfinished, contradictions: x.rep.contradictions, new_topics: x.rep.new_topics, verifier: x.v })).join('\n\n')
const synthesis = await agent(`${PREAMBLE}

You are the synthesizer. Read every reader report in full and the verifier verdicts, which override a reader where they refute or correct it. Write ONE record at ${OUT}/CURRENT-STATE-AND-NEXT.md with: a one-screen summary; what is live (verified) and the gaps against the owner's latest decisions; what is on main and its continuous integration state; who is doing what right now, as a comparison table of the sessions; where the sessions' decisions overlap or disagree, with a recommended resolution; the naming register; the ordered next work with the owner of record and a collision assessment for each item; research done, in progress elsewhere, and gaps; contradictions to fix; and questions only the owner can answer (identity or bank verification, legal commitments, spending, destructive operations; engineering decides everything else).
Reader bundle:
${bundle.slice(0, 120000)}`, { label: 'synthesize', phase: 'Synthesize' })

phase('Critique')
const critic = await agent(`${PREAMBLE}

You are the completeness critic. Read ${OUT}/CURRENT-STATE-AND-NEXT.md and every reader report in ${OUT}/. Which source was not read, which claim is presented as fact but unverified, which session's work is missing, which recent owner request has no status, and which proposed task would collide with another session? Write ${OUT}/CRITIC.md and return a short list of the gaps.`, { label: 'critic', phase: 'Critique' })

return { synthesis, critic, readers: ok.map(x => ({ key: x.key, report: x.rep.report_path, not_confirmed: (x.v?.checked || []).filter(c => c.verdict !== 'confirmed').length })) }
