"""Read-only corpus inspection with explicit coverage, never semantic approval."""
import ast
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path('/home/username/loop-engine')
OUT = Path('/tmp/loop-engine-architecture-audit.UBvdFH')
EXCLUDED = {'.git', 'node_modules', '.venv', 'venv', '__pycache__',
            '.pytest_cache', '.mypy_cache', '.ruff_cache', 'build', 'dist',
            '.cache', '.tox'}
PATTERNS = {
    'everything_loop': r'every(?:thing|\s+(?:operation|value|transformation|file|function)).{0,65}(?:loop|node)',
    'alternate_runtime': r'(?:class\s+\w*Node\b|LoopNode|LoopCell|SolverNode)',
    'new_layer_plane': r'(?:fifth|sixth|sixteen).{0,30}(?:layer|plane)|(?:Model Allocation|Fingerprint|Practitioner) [Pp]lane',
    'learning_closed': r'(?:learning|full|feedback) loop.{0,25}closed|close[sd]? the loop',
    'universal_claim': r'solve (?:any|every|all).{0,25}(?:task|problem)|AGI.level',
    'fixed_nine': r'(?:nine.step|9.step|reference_nine_step)',
    'maturity_claim': r'fully (?:implemented|verified|operational)|all gates (?:green|pass)|complete (?:loop|mesh)',
}

def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])

def digest(data):
    return hashlib.sha256(data).hexdigest()

def write_jsonl(name, rows):
    (OUT / name).write_text(''.join(json.dumps(r, sort_keys=True) + '\n' for r in rows))

started = datetime.datetime.now(datetime.timezone.utc).isoformat()
head = git('rev-parse', 'HEAD').decode().strip()
tracked = {p.decode() for p in git('ls-files', '-z').split(b'\0') if p}
files, excluded, errors = [], [], []
for folder, dirs, names in os.walk(ROOT, followlinks=False):
    kept=[]
    for name in sorted(dirs):
        p=Path(folder)/name
        if name in EXCLUDED or p.is_symlink():
            excluded.append({'path':str(p.relative_to(ROOT)), 'reason':'dependency_or_generated_directory' if name in EXCLUDED else 'symlink_not_followed'})
        else:
            kept.append(name)
    dirs[:]=kept
    for name in sorted(names):
        p=Path(folder)/name
        rel=p.relative_to(ROOT).as_posix()
        entry={'path':rel,'tracked':rel in tracked,'suffix':p.suffix.lower(),
               'coverage':'FULL_BYTE_READ_AND_AUTOMATED_CONTENT_INSPECTION',
               'semantic_review':'NOT_IMPLIED'}
        if p.is_symlink():
            entry.update(coverage='SYMLINK_METADATA_ONLY',target=os.readlink(p))
            files.append(entry); continue
        if name == '.env' or (name.startswith('.env.') and name != '.env.example') or name in {'credentials.json','kaggle.json'} or p.suffix in {'.pem','.key'}:
            entry.update(coverage='SENSITIVE_FILE_CONTENT_NOT_EXPORTED',bytes=p.stat().st_size)
            files.append(entry); continue
        try:
            before=p.stat()
            raw=p.read_bytes()
            after=p.stat()
            entry.update(bytes=len(raw),sha256=digest(raw),
                         stable_during_read=(before.st_mtime_ns==after.st_mtime_ns and before.st_size==after.st_size))
            text=raw.decode('utf-8')
            if '\0' in text:
                raise UnicodeDecodeError('utf-8',raw,0,1,'NUL data')
            entry['media']='text'
            entry['lines']=len(text.splitlines())
            entry['markers']={key:[text.count('\n',0,m.start())+1 for m in re.finditer(pattern,text,re.I)]
                              for key,pattern in PATTERNS.items()}
            if p.suffix.lower()=='.md':
                entry['headings']=[{'line':i,'title':line[:200]} for i,line in enumerate(text.splitlines(),1) if re.match(r'^#{1,4} ',line)]
            if p.suffix=='.py':
                try:
                    tree=ast.parse(text)
                    entry['python_parse']='VALID'
                    entry['classes']=[{'name':n.name,'line':n.lineno,'bases':[ast.unparse(b) for b in n.bases]} for n in ast.walk(tree) if isinstance(n,ast.ClassDef)]
                    entry['functions']=[{'name':n.name,'line':n.lineno} for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
                except (SyntaxError,ValueError) as exc:
                    entry['python_parse']='INVALID'
                    entry['parse_error']={'kind':type(exc).__name__,'line':getattr(exc,'lineno',None)}
            if p.suffix.lower()=='.json':
                try: json.loads(text); entry['json_parse']='VALID'
                except (ValueError,TypeError): entry['json_parse']='INVALID'
            if p.suffix.lower()=='.jsonl':
                bad=[]; count=0
                for line_number,line in enumerate(text.splitlines(),1):
                    if not line.strip(): continue
                    count+=1
                    try: json.loads(line)
                    except (ValueError,TypeError): bad.append(line_number)
                entry['jsonl_records']=count; entry['jsonl_invalid_lines']=bad
        except UnicodeDecodeError:
            entry['media']='binary'; entry['coverage']='FULL_BYTE_READ_HASH_ONLY'
        except OSError as exc:
            entry.update(coverage='READ_FAILED',error_type=type(exc).__name__)
            errors.append(rel)
        files.append(entry)
files.sort(key=lambda r:r['path'])
write_jsonl('files.jsonl',files)
write_jsonl('excluded.jsonl',excluded)

commits=[]
ref_commits=git('rev-list','--all','--reverse').decode().splitlines()
reflog_commits=git('rev-list','--all','--reflog','--reverse').decode().splitlines()
object_commits={line.split()[1] for line in git('cat-file','--batch-all-objects','--batch-check=%(objecttype) %(objectname)').decode().splitlines() if line.startswith('commit ')}
ordered_commits=ref_commits+[c for c in reflog_commits if c not in ref_commits]+sorted(object_commits-set(reflog_commits))
for oid in ordered_commits:
    metadata=git('show','-s','--format=%H%x00%P%x00%aI%x00%cI%x00%B',oid).decode('utf-8','replace').split('\0',4)
    patch=git('show','--format=','--no-ext-diff','--no-renames','--no-color',oid)
    decoded=patch.decode('utf-8','replace')
    numstat=git('show','--format=','--numstat','--no-renames',oid).decode('utf-8','replace')
    changes=[]
    for line in numstat.splitlines():
        parts=line.split('\t',2)
        if len(parts)==3: changes.append({'added':parts[0],'deleted':parts[1],'path':parts[2]})
    commits.append({'commit':metadata[0],'parents':metadata[1].split(),
                    'reachability':'REF' if oid in ref_commits else 'REFLOG_ONLY' if oid in reflog_commits else 'UNREACHABLE_LOCAL_OBJECT',
                    'author_time':metadata[2],'commit_time':metadata[3],
                    'message':metadata[4].strip(), 'changes':changes,
                    'patch_bytes':len(patch),'patch_sha256':digest(patch),
                    'coverage':'FULL_PATCH_AUTOMATED_INSPECTION',
                    'semantic_diff_review':'NOT_IMPLIED',
                    'markers':{k:len(re.findall(v,decoded,re.I)) for k,v in PATTERNS.items()}})
write_jsonl('commits.jsonl',commits)
textfiles=[f for f in files if f.get('media')=='text']
summary={
 'record_type':'repository_architecture_audit_inventory/v1','started_at':started,
 'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'repository':str(ROOT),'head':head,'head_after':git('rev-parse','HEAD').decode().strip(),
 'tracked_files':len(tracked),'files_enumerated':len(files),
 'text_files':len(textfiles),'markdown_files':sum(f['suffix']=='.md' for f in textfiles),
 'python_files':sum(f['suffix']=='.py' for f in textfiles),
 'text_lines':sum(f.get('lines',0) for f in textfiles),
 'bytes_read':sum(f.get('bytes',0) for f in files if 'sha256' in f),
 'excluded_directories':len(excluded),'read_errors':errors,
 'unstable_files':[f['path'] for f in files if f.get('stable_during_read') is False],
 'all_ref_commits':len(ref_commits),'reflog_union_commits':len(reflog_commits),
 'all_local_commit_objects':len(commits),'historical_patch_bytes':sum(c['patch_bytes'] for c in commits),
 'file_manifest_sha256':digest((OUT/'files.jsonl').read_bytes()),
 'commit_manifest_sha256':digest((OUT/'commits.jsonl').read_bytes()),
 'tracked_missing_from_walk':sorted(tracked-{f['path'] for f in files}),
 'by_root':dict(collections.Counter(f['path'].split('/')[0] for f in files)),
 'limitations':['Automated content inspection is not line-by-line semantic review.',
  'Dependency, cache, build, distribution, and Git internal directories are listed as excluded.',
  'Sensitive file contents are not exported; binary files are hashed only.',
  'All local commit objects were inspected, including reflog-only and unreachable objects; no remote fetch or object recovery was performed.']}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
print(json.dumps(summary,indent=2,sort_keys=True))
