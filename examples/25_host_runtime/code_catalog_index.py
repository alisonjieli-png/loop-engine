"""Index explicit source files and CLI declarations without importing code.

Git remains source authority. These are source-linked candidate descriptors,
not an executable registry. Mutations use the managed record service; source
bodies use immutable artifacts. AST relationships are descriptive, not routing.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
from pathlib import Path, PurePosixPath
import tomllib

from loop_engine.core.record_operations_records import content_digest


@dataclass(frozen=True)
class SourceIndexRequest:
    repository_root: str
    source_revision: str
    paths: tuple[str, ...]
    maximum_file_bytes: int = 2000000

    def __post_init__(self):
        object.__setattr__(self, 'paths', tuple(self.paths))
        if (not self.source_revision or not self.paths or len(set(self.paths)) != len(self.paths)
                or type(self.maximum_file_bytes) is not int or self.maximum_file_bytes < 1):
            raise ValueError('explicit source identity, paths, and size bound are required')


def index_sources(request, catalog, artifact_store, authorize):
    if type(request) is not SourceIndexRequest:
        raise TypeError('typed source inventory request required')
    root = Path(request.repository_root).absolute()
    if not root.is_dir() or any(path.is_symlink() for path in (root, *root.parents)):
        raise ValueError('source root must be an explicit non-symlink directory')
    sources = []
    for relative in request.paths:
        parsed = PurePosixPath(relative)
        path = root / relative
        if (parsed.is_absolute() or '..' in parsed.parts or str(parsed) != relative or '\\' in relative
                or any(item.is_symlink() for item in (path, *path.parents))
                or path.suffix not in ('.py', '.toml') or path.stat().st_size > request.maximum_file_bytes):
            raise ValueError('source inventory path or size refused')
        body = path.read_bytes()
        if len(body) > request.maximum_file_bytes:
            raise ValueError('source grew beyond its bound')
        sources.append((relative, body))
    tree_digest = content_digest([(name, hashlib.sha256(body).hexdigest()) for name, body in sources])
    results = []
    for relative, body in sources:
        if relative.endswith('.py'):
            tree = ast.parse(body.decode('utf-8'), filename=relative)
            symbols = [{'name': item.name, 'line': item.lineno, 'kind': type(item).__name__}
                       for item in tree.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
            imports = [{'module': item.module or '', 'level': item.level,
                        'names': [alias.name for alias in item.names]}
                       if isinstance(item, ast.ImportFrom) else {'module': alias.name, 'level': 0, 'names': []}
                       for item in ast.walk(tree) if isinstance(item, (ast.Import, ast.ImportFrom))
                       for alias in (item.names if isinstance(item, ast.Import) else [None])]
            entrypoints, package_version, kind = [], '', 'module'
            description = 'Source module ' + relative + ' with symbols ' + ', '.join(item['name'] for item in symbols)
        else:
            project = tomllib.loads(body.decode('utf-8')).get('project', {})
            entrypoints = [{'command': name, 'target': target} for name, target in project.get('scripts', {}).items()]
            package_version = project.get('version', '')
            symbols, imports, kind = [], [], 'command_line_tool'
            description = 'Package CLI declarations ' + ', '.join(item['command'] + ' ' + item['target'] for item in entrypoints)
        reference = artifact_store.put(body, media_type='text/plain', artifact_kind='source_inventory')
        identity = 'source.' + hashlib.sha256(relative.encode()).hexdigest()[:24]
        version = reference.digest
        document = {'resource_id': identity, 'version': version, 'kind': kind,
            'relative_path': relative, 'artifact_ref': reference.to_dict(),
            'reference': identity + '@' + version + '#sha256:' + reference.digest,
            'description': description[:4000], 'source_metadata': {
                'authority': 'git_source', 'source_revision_label': request.source_revision,
                'source_tree_digest': tree_digest, 'package_version': package_version,
                'entrypoints': entrypoints, 'symbols': symbols, 'imports': imports,
                'license': 'not_evaluated', 'executable': False,
                'static_imports_are_not_complete_runtime_dependencies': True}}
        written = catalog.publish(document, authorize)
        results.append({'reference': document['reference'], 'source_path': relative,
                        'record': written.records[0], 'source_metadata': document['source_metadata']})
    # Detect accidental concurrent changes. Never relabel a mixed capture as current.
    if any((root / name).read_bytes() != body for name, body in sources):
        raise RuntimeError('source changed during indexing; retained candidates are not a current snapshot')
    return {'record_type': 'source_intelligence_index/v1', 'source_tree_digest': tree_digest,
            'records': results, 'source_files_edited': False, 'code_imported': False,
            'execution_authorized': False, 'projection_not_source_authority': True}
