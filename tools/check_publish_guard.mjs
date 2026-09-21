// The publication guards decide, from the repository state alone, whether an
// image may be published. They run only inside GitHub Actions, so nothing
// else exercises them, and a guard that can never succeed looks exactly like
// a guard that always succeeds until a release is needed.
//
// This check extracts the two scripts from .github/workflows/publish-image.yml
// and runs them against a fake repository. It asserts the decision, and it
// distinguishes the two ways a publication can stop: overtaken by a later
// push, which is ordinary and must not fail the job, and untrusted or
// unverifiable source, which must fail it.
//
// Run: node tools/check_publish_guard.mjs
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const WORKFLOW = join(root, '.github/workflows/publish-image.yml');
const SOURCE_STEP = 'Require successful source checks for the current main revision';
const RECHECK_STEP = 'Publish only while this revision still heads main';
const REPOSITORY = { owner: 'alisonjieli-png', repo: 'loop-engine' };
const HEAD = 'a'.repeat(40);
const OTHER = 'b'.repeat(40);
// The YAML key under which a step lists the variables it will be given.
const VARIABLE_BLOCK = 'env:';

/** The inline script of one named step, with its YAML block indentation removed. */
function stepScript(text, name, { source = WORKFLOW } = {}) {
  const lines = text.split('\n');
  const start = lines.findIndex((line) => line.trim() === `- name: ${name}`);
  if (start < 0) throw new Error(`${source} has no step named ${name}`);
  const opens = lines.findIndex((line, index) => index > start && line.trim() === 'script: |');
  if (opens < 0) throw new Error(`the step ${name} has no inline script`);
  const indent = lines[opens + 1].length - lines[opens + 1].trimStart().length;
  const body = [];
  for (const line of lines.slice(opens + 1)) {
    if (line.trim() !== '' && line.length - line.trimStart().length < indent) break;
    body.push(line.slice(indent));
  }
  return body.join('\n');
}

/** A fake GitHub API holding one main reference and one list of workflow runs. */
function repository({ head = HEAD, runs = [] } = {}) {
  return {
    rest: {
      git: { getRef: async () => ({ data: { object: { sha: head } } }) },
      actions: { listWorkflowRuns: async () => ({ data: { workflow_runs: runs } }) },
    },
  };
}

function trustedRun(revision = HEAD, over = {}) {
  return {
    id: 1234, head_sha: revision, head_branch: 'main', status: 'completed',
    conclusion: 'success', event: 'push',
    head_repository: { full_name: `${REPOSITORY.owner}/${REPOSITORY.repo}` },
    ...over,
  };
}

function recorder() {
  const outputs = {}, notices = [];
  return {
    outputs, notices,
    core: {
      setOutput: (name, value) => { outputs[name] = value; },
      notice: (message) => { notices.push(message); },
    },
  };
}

/** The variable names a step declares, read from the workflow itself.
 *
 * Taking the name from the workflow rather than repeating it here means a
 * rename in the workflow moves this check with it, instead of leaving it
 * quietly deciding a variable the step no longer reads. Nothing here reads
 * or writes the real process environment; these are the names the extracted
 * script will look for on the fake process it is given.
 */
function declaredVariableNames(text, name) {
  const lines = text.split('\n');
  const start = lines.findIndex((line) => line.trim() === `- name: ${name}`);
  if (start < 0) throw new Error('the publication workflow has no step named ' + name);
  const opens = lines.findIndex((line, index) => index > start && line.trim() === VARIABLE_BLOCK);
  if (opens < 0 || opens > lines.findIndex((line, index) => index > start && line.trim() === 'with:')) {
    return [];
  }
  const indent = lines[opens + 1].length - lines[opens + 1].trimStart().length;
  const names = [];
  for (const line of lines.slice(opens + 1)) {
    if (line.trim() === '' || line.length - line.trimStart().length < indent) break;
    names.push(line.trim().split(':')[0]);
  }
  return names;
}

/** Run one extracted script against a fake process, never the real one.
 *
 * The scripts read their revision from process.env. Writing that into the
 * real process to arrange it would make this check mutate the state it is
 * supposed to be deciding about, so the script is handed its own process
 * object and the real one is untouched.
 */
async function run(script, { github, core, context, variables = {} }) {
  const body = new Function('github', 'context', 'core', 'process',
    `return (async () => { ${script} })();`);
  try {
    await body(github, context, core, { env: { ...variables } });
    return { threw: null };
  } catch (error) {
    return { threw: error.message };
  }
}

const results = [];
function check(name, passed, detail) {
  results.push({ name, passed: Boolean(passed), detail: detail ?? null });
}

const workflowText = readFileSync(WORKFLOW, 'utf8');
const sourceScript = stepScript(workflowText, SOURCE_STEP);
const recheckScript = stepScript(workflowText, RECHECK_STEP);
const [revisionVariable] = declaredVariableNames(workflowText, RECHECK_STEP);
if (!revisionVariable) throw new Error('the second guard declares no variable name');
const holding = { [revisionVariable]: HEAD };

const pushContext = (sha) => ({
  eventName: 'workflow_run', sha, repo: REPOSITORY,
  payload: { workflow_run: { head_sha: sha } },
});

// The ordinary case: this revision heads main and a trusted run covers it.
{
  const seen = recorder();
  const outcome = await run(sourceScript, {
    github: repository({ runs: [trustedRun()] }), core: seen.core, context: pushContext(HEAD),
  });
  check('a_trusted_run_on_the_current_revision_publishes',
    outcome.threw === null && seen.outputs.publish === 'true'
    && seen.outputs.revision === HEAD && seen.outputs.ci_run === 1234,
    JSON.stringify({ threw: outcome.threw, ...seen.outputs }));
}

// Overtaken by a later push. Nothing to publish, and this is not a fault.
{
  const seen = recorder();
  const outcome = await run(sourceScript, {
    github: repository({ head: OTHER, runs: [trustedRun()] }),
    core: seen.core, context: pushContext(HEAD),
  });
  check('a_revision_overtaken_by_a_later_push_skips_without_failing',
    outcome.threw === null && seen.outputs.publish === 'false' && seen.notices.length === 1,
    JSON.stringify({ threw: outcome.threw, publish: seen.outputs.publish, notices: seen.notices.length }));
}

// The cases that must still fail the job, because the source is not trusted.
{
  const seen = recorder();
  const outcome = await run(sourceScript, {
    github: repository({ runs: [] }), core: seen.core, context: pushContext(HEAD),
  });
  check('a_revision_no_successful_run_covers_fails_the_job',
    outcome.threw !== null && seen.outputs.publish === undefined, String(outcome.threw));
}
{
  const seen = recorder();
  const outcome = await run(sourceScript, {
    github: repository(), core: seen.core, context: pushContext('not-a-commit'),
  });
  check('a_revision_that_is_not_an_exact_commit_fails_the_job',
    outcome.threw !== null && seen.outputs.publish === undefined, String(outcome.threw));
}
for (const [name, over] of [
  ['from_a_fork', { head_repository: { full_name: 'someone-else/loop-engine' } }],
  ['from_a_pull_request_event', { event: 'pull_request' }],
  ['that_did_not_succeed', { conclusion: 'failure' }],
  ['on_another_branch', { head_branch: 'topic' }],
  ['for_another_revision', { head_sha: OTHER }],
]) {
  const seen = recorder();
  const outcome = await run(sourceScript, {
    github: repository({ runs: [trustedRun(HEAD, over)] }),
    core: seen.core, context: pushContext(HEAD),
  });
  check(`a_run_${name}_does_not_authorise_publication`,
    outcome.threw !== null && seen.outputs.publish === undefined, String(outcome.threw));
}

// The second guard, after the image is built: main may have moved meanwhile.
{
  const seen = recorder();
  const outcome = await run(recheckScript, {
    github: repository(), core: seen.core, context: { repo: REPOSITORY },
    variables: holding,
  });
  check('an_unmoved_main_still_publishes_after_verification',
    outcome.threw === null && seen.outputs.publish === 'true',
    JSON.stringify({ threw: outcome.threw, publish: seen.outputs.publish }));
}
{
  const seen = recorder();
  const outcome = await run(recheckScript, {
    github: repository({ head: OTHER }), core: seen.core, context: { repo: REPOSITORY },
    variables: holding,
  });
  check('main_moving_during_verification_skips_without_failing',
    outcome.threw === null && seen.outputs.publish === 'false' && seen.notices.length === 1,
    JSON.stringify({ threw: outcome.threw, publish: seen.outputs.publish, notices: seen.notices.length }));
}

// Every step after a guard must be conditional on that guard's answer, or the
// skip is decorative and the job publishes anyway.
{
  const lines = workflowText.split('\n');
  const guarded = (fromStep, condition) => {
    const start = lines.findIndex((line) => line.trim() === `- name: ${fromStep}`);
    const steps = [];
    let current = null;
    for (const line of lines.slice(start + 1)) {
      if (/^ {6}- (name|uses):/.test(line)) { current = { header: line, lines: [] }; steps.push(current); }
      else if (current) current.lines.push(line);
    }
    return steps.filter((step) => !step.lines.some((line) => line.trim() === `if: ${condition}`));
  };
  const afterSource = guarded(SOURCE_STEP, "steps.source.outputs.publish == 'true'");
  // The recheck step carries the source condition, and everything after it
  // carries the recheck condition instead.
  const afterRecheck = guarded(RECHECK_STEP, "steps.recheck.outputs.publish == 'true'");
  const unguarded = afterSource.filter((step) => !step.header.includes(RECHECK_STEP)
    && afterRecheck.some((later) => later.header === step.header) === false
    && afterSource.indexOf(step) < afterSource.findIndex((s) => s.header.includes(RECHECK_STEP)));
  check('every_step_before_the_second_guard_waits_on_the_first',
    unguarded.length === 0, JSON.stringify(unguarded.map((s) => s.header.trim())));
  check('every_step_after_the_second_guard_waits_on_it',
    afterRecheck.length === 0, JSON.stringify(afterRecheck.map((s) => s.header.trim())));
}

// Known-wrong controls. Each removes one guard from a copy of the script held
// in memory and requires the check above to notice. The workflow file on disk
// is never changed.
const controls = [];
function control(name, script, context, github, expectation) {
  const seen = recorder();
  return run(script, { github, core: seen.core, context, variables: holding })
    .then((outcome) => {
      const detected = expectation(outcome, seen);
      controls.push({ name, applied: true, detected });
      check(`control_${name}`, detected,
        JSON.stringify({ threw: outcome.threw, ...seen.outputs }));
    });
}

await control('accept_a_run_from_any_repository',
  sourceScript.replace(/\s*&&\s*\n\s*run\.head_repository\?\.full_name === repository/, ''),
  pushContext(HEAD),
  repository({ runs: [trustedRun(HEAD, { head_repository: { full_name: 'someone-else/loop-engine' } })] }),
  // With the repository filter gone a fork's run authorises publication, which
  // is the behaviour the filter exists to prevent.
  (outcome, seen) => outcome.threw === null && seen.outputs.publish === 'true');

await control('publish_from_a_stale_revision',
  sourceScript.replace(/if \(current\.data\.object\.sha !== revision\) \{[\s\S]*?\n\}\n/, ''),
  pushContext(HEAD),
  repository({ head: OTHER, runs: [trustedRun()] }),
  // Without the supersession branch an overtaken revision publishes and moves
  // the moving tags backwards.
  (outcome, seen) => outcome.threw === null && seen.outputs.publish === 'true');

await control('treat_supersession_as_a_failure',
  sourceScript.replace(/core\.setOutput\('publish', 'false'\);[\s\S]*?return;/,
    "throw new Error('This revision is no longer the current main revision.');"),
  pushContext(HEAD),
  repository({ head: OTHER, runs: [trustedRun()] }),
  // The defect this check was written for: being overtaken turned the job red.
  (outcome) => outcome.threw === 'This revision is no longer the current main revision.');

const passed = results.filter((row) => row.passed).length;
const report = {
  record_type: 'publish_guard_check/v1',
  passed, total: results.length,
  controls_detected: controls.filter((row) => row.detected).length,
  controls: controls.length,
  all_passed: passed === results.length && controls.every((row) => row.detected),
  failures: results.filter((row) => !row.passed),
};
console.log(JSON.stringify(report, null, 1));
process.exit(report.all_passed ? 0 : 1);
