export const meta = {
  name: 'baltor-research-sweep',
  description: 'Run several hands-on research lines in parallel, adversarially re-check each line, and write one successor research record draft',
  whenToUse: 'When the owner names new projects, standards or tools to evaluate, or when a research record marks lines as not verified',
  phases: [
    { title: 'Research', detail: 'one agent per line, trials in its own lab folder' },
    { title: 'Verify', detail: 'adversarial re-check of the decisive findings' },
    { title: 'Write', detail: 'one successor record draft' },
  ],
}

// args (all paths absolute):
//   repo, main_ref   checkout and main reference
//   out              folder for this run; each line works in <out>/lab/<key>/
//   frame            free text: what the research is for and the rules candidates must respect
//   lines            list of {key, prompt}
//   record_name      file name for the successor record draft, for example SOMETHING-2026-10-01.md
//   predecessor      optional repository path of the record this one continues
//   model_calls      optional free text describing allowed model calls and their ceiling; default is none
const A = args || {}
if (!A.repo || !A.main_ref || !A.out || !A.lines || !A.record_name) throw new Error('args.repo, args.main_ref, args.out, args.lines and args.record_name are required')
const S = A.out

const PRE = `You are one agent in a research program for the Loop Engine repository (public brand Baltor).
FRAME: ${A.frame || 'Every outside project or standard sits behind one of the fixed, typed, versioned engine slots in src/loop_engine/data/engine_slots.yaml as an engine, or as a field or export format of Baltor\'s own record, never as a replacement. One Loop runtime; an engine is an adapter, never a second scheduler. Effects need typed authority; discovery is effect-free; secrets never land in files, events, reports or telemetry; imported material stays a candidate until independent review; configured, loaded, used and verified are separate facts.'}
HARD RULES: Never modify any repository or worktree and run no git command that changes one; read main with 'git -C ${A.repo} show ${A.main_ref}:<path>'. Work only in your lab folder. Name any container you start with the prefix 'sweep-<your key>-' and remove only your own. No deploys, no provider writes, no spending, no email, no signing with a real identity, no printing of secrets. Model calls: ${A.model_calls || 'none'}. Web search and fetch are allowed; prefer primary sources and record versions and dates. Label each finding ran (with the command and output saved), source or claim, and keep failed trials beside successes. Plain English, no em dashes.`

const OUT = { type: 'object', properties: {
  report_path: { type: 'string' }, summary: { type: 'string' },
  findings: { type: 'array', items: { type: 'object', properties: { subject: { type: 'string' }, finding: { type: 'string' }, evidence: { type: 'string', enum: ['ran', 'source', 'claim'] }, detail: { type: 'string' } }, required: ['subject', 'finding', 'evidence', 'detail'] } },
  slot_decisions: { type: 'array', items: { type: 'object', properties: { slot: { type: 'string' }, candidate: { type: 'string' }, decision: { type: 'string', enum: ['adopt', 'adapt', 'watch', 'reject', 'native'] }, reason: { type: 'string' } }, required: ['slot', 'candidate', 'decision', 'reason'] } },
  next_tests: { type: 'array', items: { type: 'string' } } },
  required: ['report_path', 'summary', 'findings', 'slot_decisions', 'next_tests'] }
const VERD = { type: 'object', properties: {
  checked: { type: 'array', items: { type: 'object', properties: { finding: { type: 'string' }, verdict: { type: 'string', enum: ['confirmed', 'refuted', 'partly', 'unverifiable'] }, correction: { type: 'string' }, evidence: { type: 'string' } }, required: ['finding', 'verdict', 'evidence'] } },
  missed: { type: 'array', items: { type: 'string' } } }, required: ['checked', 'missed'] }

phase('Research')
const res = (await pipeline(
  A.lines,
  (l) => agent(`${PRE}\n\nLINE '${l.key}'. Lab: ${S}/lab/${l.key}/. Report: ${S}/${l.key}.md.\n${l.prompt}`, { label: `research:${l.key}`, phase: 'Research', schema: OUT }),
  (r, l) => r ? agent(`${PRE}\n\nAdversarially verify line '${l.key}' (report ${r.report_path}, lab ${S}/lab/${l.key}/). Pick the 8 to 14 findings that decide its slot decisions, especially every 'ran' finding, and try to refute each: re-run cheap commands in ${S}/lab/${l.key}-verify/, re-read primary sources, check versions. No model calls. Default to 'unverifiable'.\n${JSON.stringify({ findings: r.findings, slot_decisions: r.slot_decisions }).slice(0, 25000)}`, { label: `verify:${l.key}`, phase: 'Verify', schema: VERD }).then(v => ({ key: l.key, r, v })) : null,
)).filter(Boolean)

phase('Write')
const draft = await agent(`${PRE}\n\nYou are the writer. Read every line report and the verifier verdicts (which override a report where they refute it). Write ${S}/${A.record_name}${A.predecessor ? ', a successor to ' + A.predecessor + ' on ' + A.main_ref + ' whose voice, structure and evidence labels you match' : ''}, following AGENTS.md public-writing rules and humanizer-context.md. For each line: what was run, what was read, what stays a claim, failures beside successes, and slot decisions with reasons. End with the next discriminating tests.\n${res.map(d => JSON.stringify({ key: d.key, report: d.r.report_path, summary: d.r.summary, slot_decisions: d.r.slot_decisions, next_tests: d.r.next_tests, verifier: d.v })).join('\n\n').slice(0, 110000)}`, { label: 'write', phase: 'Write' })
return { draft, lines: res.map(d => ({ key: d.key, report: d.r.report_path, refuted: (d.v?.checked || []).filter(c => c.verdict === 'refuted').length })) }
