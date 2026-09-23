export const meta = {
  name: 'baltor-plan-validation',
  description: 'Several planners propose the ordered next work from different angles, independent judges score the plans against the evidence, and one synthesis keeps the best plan with the best ideas of the others',
  whenToUse: 'After a state review, before committing a session to an order of work',
  phases: [
    { title: 'Plan', detail: 'independent planners, one angle each' },
    { title: 'Judge', detail: 'independent judges score every plan' },
    { title: 'Synthesize', detail: 'winning plan plus grafted ideas' },
  ],
}

// args (all paths absolute):
//   repo, main_ref   checkout and main reference (roadmap at docs/roadmap/roadmap.yaml)
//   state            path of the current-state record to plan from
//   evidence         optional list of further report paths
//   out              folder for this run
//   angles           optional list of planner angles
//   judges           number of judges (default 3)
const A = args || {}
if (!A.repo || !A.main_ref || !A.state || !A.out) throw new Error('args.repo, args.main_ref, args.state and args.out are required')
const S = A.out
const ANGLES = A.angles || [
  'north star first: what makes harnesses and multi-agent systems most efficient on unseen tasks soonest',
  'customer journey first: what a paying developer must be able to do end to end this week',
  'risk first: what could lose work, leak data, break the live service or mislead a customer',
  'evidence first: which claims most need a measured result before anything else is built on them',
]
const J = A.judges || 3
const EVID = (A.evidence || []).join(', ')

const PRE = `You plan work for the Loop Engine repository (public brand Baltor). The task authority is docs/roadmap/roadmap.yaml on ${A.main_ref} (read with 'git -C ${A.repo} show ${A.main_ref}:<path>'); the rules are AGENTS.md. Read the current-state record ${A.state}${EVID ? ' and these reports: ' + EVID : ''}. Never modify any repository. Write only under ${S}/. Plain English, no em dashes.`

const PLAN = { type: 'object', properties: {
  angle: { type: 'string' }, plan_path: { type: 'string' },
  steps: { type: 'array', items: { type: 'object', properties: { step: { type: 'string' }, roadmap_ids: { type: 'string' }, owner: { type: 'string' }, acceptance: { type: 'string' }, effort: { type: 'string' }, risk: { type: 'string' }, depends_on: { type: 'string' } }, required: ['step', 'owner', 'acceptance'] } } },
  required: ['angle', 'plan_path', 'steps'] }

phase('Plan')
const plans = (await parallel(ANGLES.map((angle, i) => () => agent(`${PRE}\n\nPropose the ordered next 10 to 15 steps from this angle only: ${angle}. Each step names its roadmap identifiers, owner (engineering, a named agent session, or the owner for identity, legal, spending or destructive decisions only), acceptance check, effort, risk and dependencies. Write ${S}/plan-${i + 1}.md.`, { label: `plan:${i + 1}`, phase: 'Plan', schema: PLAN })))).filter(Boolean)

phase('Judge')
const SCORE = { type: 'object', properties: { scores: { type: 'array', items: { type: 'object', properties: { plan: { type: 'integer' }, north_star: { type: 'integer' }, feasibility: { type: 'integer' }, evidence: { type: 'integer' }, risk_control: { type: 'integer' }, total: { type: 'integer' }, flaws: { type: 'string' }, best_idea: { type: 'string' } }, required: ['plan', 'total', 'flaws', 'best_idea'] } } }, required: ['scores'] }
const judged = (await parallel(Array.from({ length: J }, (_, k) => () => agent(`${PRE}\n\nYou are judge ${k + 1}. Score every plan from 1 to 10 on north star value, feasibility with the current authority, grounding in evidence, and risk control; total them; name each plan's worst flaw and its best idea. Check at least three factual premises of each plan against the source.\nPlans: ${JSON.stringify(plans.map((p, i) => ({ plan: i + 1, angle: p.angle, steps: p.steps })))}`, { label: `judge:${k + 1}`, phase: 'Judge', schema: SCORE })))).filter(Boolean)

phase('Synthesize')
const final = await agent(`${PRE}\n\nSynthesize ${S}/VALIDATED-PLAN.md: take the plan with the highest summed score as the spine, graft the judges' best ideas from the others, remove every step the judges showed to rest on a false premise, and state for each step its acceptance check and owner. Add a short section on what the judges disagreed about.\nPlans: ${JSON.stringify(plans.map((p, i) => ({ plan: i + 1, angle: p.angle, path: p.plan_path })))}\nScores: ${JSON.stringify(judged)}`, { label: 'synthesize', phase: 'Synthesize' })
return { plans: plans.length, judges: judged.length, final }
