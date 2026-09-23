// No models, CLI sessions, packages, extensions, or native configuration changes.
// Inspect the already installed resource loader against disposable synthetic files.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { pathToFileURL } from 'node:url';

const [installedRoot, resultPath] = process.argv.slice(2);
if (!installedRoot || !resultPath || fs.existsSync(resultPath)) {
  throw new Error('Supply installed package root and a new result path');
}
const modulePath = path.join(installedRoot, 'dist/core/resource-loader.js');
const { loadProjectContextFiles } = await import(pathToFileURL(modulePath));
const { loadSkills } = await import(pathToFileURL(path.join(installedRoot, 'dist/core/skills.js')));
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'baltor-pi-loader-'));
const work = path.join(root, 'parent', 'work');
const agentDir = path.join(root, 'agent');
const write = (p, s) => { fs.mkdirSync(path.dirname(p), {recursive: true}); fs.writeFileSync(p, s); };
fs.mkdirSync(work, {recursive: true});
fs.mkdirSync(agentDir);
const rows = [];
const inspect = () => loadProjectContextFiles({cwd: work, agentDir});
const record = (name, condition, files) => rows.push({name, passed: Boolean(condition), sources: files.map(f => ({path: f.path.replace(root, '<temporary>'), content: f.content}))});
try {
  write(path.join(work, 'node_context.md'), 'AUXILIARY_ONLY_MARKER');
  write(path.join(work, 'run-state.json'), '{"marker":"STATE_ONLY_MARKER"}');
  let result = inspect();
  record('arbitrary_context_and_state_not_auto_loaded', !result.some(f => /AUXILIARY_ONLY|STATE_ONLY/.test(f.content)), result);
  write(path.join(work, 'AGENTS.md'), 'TASK_MARKER first action: inspect input.json');
  write(path.join(work, 'CLAUDE.md'), 'CLAUDE_MARKER');
  result = inspect();
  record('agents_wins_over_claude_same_directory', result.some(f => f.content.includes('TASK_MARKER')) && !result.some(f => f.content.includes('CLAUDE_MARKER')), result);
  write(path.join(work, 'AGENTS.override.md'), 'OVERRIDE_MARKER');
  result = inspect();
  record('installed_0731_does_not_load_override_name', !result.some(f => f.content.includes('OVERRIDE_MARKER')) && result.some(f => f.content.includes('TASK_MARKER')), result);
  write(path.join(root, 'parent', 'AGENTS.md'), 'ANCESTOR_MARKER');
  fs.mkdirSync(path.join(work, '.git'));
  result = inspect();
  record('git_root_does_not_block_parent_context', result.some(f => f.content.includes('ANCESTOR_MARKER')), result);
  write(path.join(agentDir, 'AGENTS.md'), 'GLOBAL_MARKER');
  result = inspect();
  record('global_then_parent_then_work_order', result.filter(f => /GLOBAL_MARKER|ANCESTOR_MARKER|TASK_MARKER/.test(f.content)).map(f => f.content.split(' ')[0]).join(',') === 'GLOBAL_MARKER,ANCESTOR_MARKER,TASK_MARKER', result);
  fs.unlinkSync(path.join(work, 'AGENTS.md'));
  result = inspect();
  record('missing_agents_activates_claude_fallback', result.some(f => f.content.includes('CLAUDE_MARKER')) && !result.some(f => f.content.includes('TASK_MARKER')), result);
  const a = path.join(root, 'skills-a', 'reconcile');
  const b = path.join(root, 'skills-b', 'reconcile');
  const skill = marker => `---\nname: reconcile\ndescription: ${marker}\n---\n# Reconcile\n`;
  write(path.join(a, 'SKILL.md'), skill('FIRST_SKILL_MARKER'));
  write(path.join(b, 'SKILL.md'), skill('SECOND_SKILL_MARKER'));
  const skills = loadSkills({cwd: work, agentDir, skillPaths: [a, b], includeDefaults: false});
  rows.push({name:'same_name_first_explicit_skill_wins_with_diagnostic', passed: skills.skills.length === 1 && skills.skills[0].description === 'FIRST_SKILL_MARKER' && skills.diagnostics.length > 0, skills: skills.skills.map(s => ({name:s.name, description:s.description, filePath:s.filePath.replace(root, '<temporary>')})), diagnostics: skills.diagnostics.map(d=>JSON.parse(JSON.stringify(d).replaceAll(root, '<temporary>')))});
  const output = {kind:'native_resource_loader_observation', at:new Date().toISOString(), package: JSON.parse(fs.readFileSync(path.join(installedRoot,'package.json'),'utf8')).name, version:JSON.parse(fs.readFileSync(path.join(installedRoot,'package.json'),'utf8')).version, moduleSha256:crypto.createHash('sha256').update(fs.readFileSync(modulePath)).digest('hex'), scope:'Direct installed module invocation; not a full CLI session or a model call.', modelCalls:0, nativeConfigurationChanges:0, cases:rows, passed:rows.every(r=>r.passed)};
  fs.writeFileSync(resultPath, JSON.stringify(output,null,2)+'\n');
  console.log(JSON.stringify({passed:output.passed,cases:rows.length,version:output.version,resultPath}));
  if (!output.passed) process.exitCode = 1;
} finally {
  fs.rmSync(root,{recursive:true,force:true});
}
