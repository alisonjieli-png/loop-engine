"""Known-wrong adapted reference inputs must fail before catalogue writes."""
import hashlib
import tempfile
import unittest
from contextlib import closing
from copy import deepcopy
from pathlib import Path

from loop_engine.catalog.stores.sqlite_store import SQLiteRecordStore
from loop_engine.core.library_ingestion.licences import LicenceFile, decide_licence
from loop_engine.core.service_runtime.catalogue_packages import (
    CataloguePackage,
    CataloguePackageFile,
)
from tools.adapted_reference_candidates import (
    ADAPTED_SPECIFICATIONS,
    compile_adapted_candidates,
)
from tools.stage_intelligence_candidates import (
    CandidateStageRequest,
    compile_candidates,
    stage_candidates,
)

ROOT = Path(__file__).resolve().parents[1]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class AdaptedReferenceChecks(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.package_root = self.root / 'prepared'
        self.source_root = self.root / 'sources'
        self.source_root.mkdir()
        self.source = b'{"openapi":"3.1.0","info":{"title":"Fixture","version":"1"},"paths":{}}'
        (self.source_root / 'source.json').write_bytes(self.source)
        licence = (ROOT / 'LICENSE').read_bytes()
        proof = decide_licence('spec.json', {'LICENSE': LicenceFile('LICENSE', sha(licence), licence.decode(), 'MIT')}, root_path='LICENSE')
        self.provenance = {'record_type': 'outside_source_provenance/v1', 'origin': 'github_repository',
            'origin_host': 'github.com', 'repository': 'fixture/reference', 'immutable_revision': 'a' * 40,
            'path': 'spec.json', 'source_digest': sha(self.source), 'source_size_bytes': len(self.source),
            'git_blob_sha': hashlib.sha1(b'blob ' + str(len(self.source)).encode() + b'\0' + self.source).hexdigest(),
            'fetch_digest': 'b' * 64, 'request_digest': 'c' * 64, 'fetched_at': '2026-09-26T00:00:00Z',
            'licence_evidence': proof}
        body = '# Inspect an API reference\n\nPlan a request from supplied facts; do not contact a service.\n'
        self.files = {'AGENTS.md': (body.encode(), 'instruction_file', 'text/markdown'),
                      'references/endpoint.json': (b'{"method":"GET","live_tested":false}', 'other', 'application/json'),
                      'references/UPSTREAM-LICENSE.txt': (licence, 'skill_reference', 'text/plain'),
                      'LICENSE': (licence, 'other', 'text/plain')}
        self.row = {'id': 'inspect_api_reference', 'layer': 'context', 'family': 'adapted_reference',
            'title': 'Inspect an API reference', 'purpose': 'Plan an API request using a documented source.',
            'text': body, 'tags': ['api', 'reference'], 'kind': 'instruction_file',
            'component_type': 'api_operation_reference', 'styles': ['codex'], 'dependencies': [],
            'producer': {'producer_identity': 'Fixture compiler author', 'family': 'openai',
                         'method_identity': 'reference_authoring/v1'}, 'declared_effects': ['reads_fs'],
            'package_root': 'packages/inspect_api_reference', 'body_path': 'bodies/inspect_api_reference.package.json',
            'outside_provenance': [deepcopy(self.provenance)],
            'source_blobs': [{'source_index': 0, 'snapshot_path': 'source.json'}],
            'license': {'expression': 'MIT', 'original_text_path': 'LICENSE',
                        'upstream_texts': [{'source_index': 0, 'path': 'references/UPSTREAM-LICENSE.txt'}]},
            'adaptation': {'record_type': 'reference_adaptation/v1', 'method_identity': 'operation_reference/v1',
                'compiler_sha256': 'd' * 64, 'parameters': {'operation_id': 'fixture_get'},
                'source_digests': [sha(self.source)], 'description': 'Original guide derived from source facts.'}}
        self.freeze()

    def freeze(self):
        package = CataloguePackage(tuple(CataloguePackageFile(path, sha(raw), len(raw), media, role)
                                         for path, (raw, role, media) in self.files.items()))
        for path, (raw, _role, _media) in self.files.items():
            target = self.package_root / self.row['package_root'] / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        body = self.package_root / self.row['body_path']
        body.parent.mkdir(exist_ok=True)
        body.write_bytes(package.document())
        self.row.update(package=package.to_dict(), package_digest=package.package_digest)
        self.row['adaptation']['target_package_digest'] = package.package_digest

    def request(self, **changes):
        values = {'repository': ROOT, 'namespace': 'fixture.adapted', 'writes_authorized': True,
                  'package_root': self.package_root, 'source_root': self.source_root}
        values.update(changes)
        return CandidateStageRequest(**values)

    def compile(self, row=None):
        return compile_adapted_candidates([row or self.row], self.request())

    def test_adapted_origin_is_preserved_and_staged_only_as_candidate(self):
        records = compile_candidates({'record_type': ADAPTED_SPECIFICATIONS, 'specifications': [self.row]}, self.request())
        self.assertEqual(records[0]['payload']['authoring'], 'adapted_reference_under_permissive_licence')
        self.assertEqual(records[0]['payload']['producer']['family'], 'openai')
        self.assertEqual(records[0]['lifecycle'], 'candidate')
        self.assertFalse(records[0]['payload']['execution_available'])
        self.assertEqual(records[0]['payload']['transformation_fidelity'], 'pending_independent_review')
        with closing(SQLiteRecordStore(str(self.root / 'candidates.db'))) as store:
            self.assertTrue(stage_candidates(store, records, self.request()).committed)
            self.assertEqual(store.get(records[0]['record_id']), records[0])

    def test_a_current_native_reader_does_not_reinterpret_the_new_shape(self):
        with self.assertRaises(ValueError):
            compile_candidates({'record_type': 'candidate_intelligence_specifications/v3', 'specifications': [self.row]}, self.request())

    def test_unknown_specification_version_refuses(self):
        with self.assertRaises(ValueError):
            compile_candidates({'record_type': 'candidate_intelligence_specifications/v99', 'specifications': [self.row]}, self.request())

    def test_changed_source_bytes_refuse(self):
        (self.source_root / 'source.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError, 'source_blob_mismatch'):
            self.compile()

    def test_git_blob_identity_is_not_replaced_by_sha256_alone(self):
        self.row['outside_provenance'][0]['git_blob_sha'] = 'f' * 40
        with self.assertRaisesRegex(ValueError, 'source_blob_mismatch'):
            self.compile()

    def test_every_source_needs_a_snapshot(self):
        self.row['source_blobs'] = []
        with self.assertRaisesRegex(ValueError, 'source_blob_population'):
            self.compile()

    def test_restricted_rights_do_not_become_adaptation_rights(self):
        self.row['outside_provenance'][0]['licence_evidence']['decision'] = 'outline_only'
        with self.assertRaisesRegex(ValueError, 'adaptation_rights'):
            self.compile()

    def test_source_licence_notice_must_be_carried_exactly(self):
        self.row['outside_provenance'][0]['licence_evidence']['governing_file']['sha256'] = 'f' * 64
        with self.assertRaisesRegex(ValueError, 'upstream_licence'):
            self.compile()

    def test_changed_package_byte_refuses(self):
        (self.package_root / self.row['package_root'] / 'AGENTS.md').write_text('changed')
        with self.assertRaises(ValueError):
            self.compile()

    def test_unlisted_extra_file_refuses(self):
        (self.package_root / self.row['package_root'] / 'extra.txt').write_text('unreviewed')
        with self.assertRaises(ValueError):
            self.compile()

    def test_source_snapshot_symlink_and_traversal_refuse(self):
        path = self.source_root / 'linked.json'
        path.symlink_to(self.source_root / 'source.json')
        for unsafe in ['linked.json', '../sources/source.json']:
            self.row['source_blobs'][0]['snapshot_path'] = unsafe
            with self.assertRaises(ValueError):
                self.compile()

    def test_reference_profile_cannot_smuggle_an_executable(self):
        self.files['tools/run.py'] = (b'print(1)', 'executable_tool', 'text/x-python')
        self.freeze()
        with self.assertRaisesRegex(ValueError, 'reference_file_kind'):
            self.compile()

    def test_transform_must_bind_sources_and_result(self):
        for key in ['source_digests', 'target_package_digest']:
            row = deepcopy(self.row)
            row['adaptation'][key] = ['e' * 64] if key == 'source_digests' else 'e' * 64
            with self.assertRaisesRegex(ValueError, 'adaptation_binding'):
                self.compile(row)

    def test_metadata_cannot_replace_the_actual_instruction_text(self):
        self.row['text'] += 'Unbound search claim.'
        with self.assertRaisesRegex(ValueError, 'instruction_text'):
            self.compile()

    def test_extra_approval_field_and_effect_broadening_refuse(self):
        row = deepcopy(self.row)
        row['approved'] = True
        with self.assertRaises(ValueError):
            self.compile(row)
        self.row['declared_effects'] = ['reads_fs', 'network']
        with self.assertRaisesRegex(ValueError, 'reference_effects'):
            self.compile()

    def test_source_root_is_required(self):
        with self.assertRaisesRegex(ValueError, 'source_root_required'):
            compile_adapted_candidates([self.row], self.request(source_root=None))


if __name__ == '__main__':
    unittest.main()
