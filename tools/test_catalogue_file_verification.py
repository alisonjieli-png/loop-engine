"""Serial/process parity, resource bounds and wrong results at the local byte-verification edge."""
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
import hashlib
import io
import json
import os
from pathlib import Path
import pickle
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock
import weakref

import catalogue_file_verification as verification
import reconcile_catalogue_bundle as reconcile
from loop_engine.core.service_runtime.catalogue_packages import MAXIMUM_FILE_BYTES, VolumeBodyStore
from loop_engine.core.service_runtime.records import ServiceRuntimeError
from tools.test_reconcile_catalogue_bundle import bundle, line, observation, request


_native_worker = verification._verify_batch


def delayed_native_worker(batch):
    if batch.sequence == 0:
        time.sleep(.15)
    return _native_worker(batch)


def crashed_worker(_batch):
    os._exit(17)


class UnpicklableCatalogue:
    def __reduce__(self):
        raise AssertionError('the catalogue or store object was serialized')


def inventory(store, files):
    return SimpleNamespace(blobs=lambda: store, catalogue=UnpicklableCatalogue(),
                           items=(SimpleNamespace(package=SimpleNamespace(files=tuple(files))),))


class ProcessVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / 'first').mkdir()
        (self.root / 'second').mkdir()
        self.first = VolumeBodyStore(str(self.root / 'first'), writes_authorized=True)
        self.second = VolumeBodyStore(str(self.root / 'second'), writes_authorized=True)
        self.first.catalogue = UnpicklableCatalogue()

    def file(self, payload, store=None):
        (store or self.first).put(payload)
        return verification.VerificationFile(hashlib.sha256(payload).hexdigest(), len(payload))

    def error(self, action):
        try:
            action()
        except (ValueError, OSError) as error:
            return type(error), getattr(error, 'code', None), str(error)
        self.fail('a refused read was accepted')

    def test_serial_default_and_empty_parallel_population_open_no_pool(self):
        file = self.file(b'bytes')
        with mock.patch.object(verification, 'ProcessPoolExecutor', side_effect=AssertionError('unexpected pool')):
            self.assertEqual(list(reconcile.verify_files(inventory(self.first, [file, file]))), [file.digest])
            for workers in (1, 4, 8):
                self.assertEqual(reconcile.verify_files(inventory(None, []), workers=workers), {})

    def test_all_metadata_is_validated_and_deduplicated_before_reads(self):
        valid = self.file(b'valid')
        wrong = replace(valid, size_bytes=valid.size_bytes + 1)
        invalid = replace(valid, digest='bad digest')
        for workers in (1, 4, 8):
            for files in ([valid, wrong], [valid, invalid]):
                with self.subTest(workers=workers, files=files), \
                        mock.patch.object(reconcile, '_payload', side_effect=AssertionError('early read')), \
                        mock.patch.object(verification, 'ProcessPoolExecutor', side_effect=AssertionError('early pool')), \
                        self.assertRaises(ValueError):
                    reconcile.verify_files(inventory(self.first, files), workers=workers)

    def test_worker_limits_are_typed_and_refused_before_store_access(self):
        source = SimpleNamespace(blobs=mock.Mock(side_effect=AssertionError('unexpected access')))
        for workers in (True, False, 0, -1, 9, 4.0, '4', None):
            with self.subTest(workers=workers), self.assertRaisesRegex(ValueError, 'verification workers'):
                reconcile.verify_files(source, workers=workers)
        source.blobs.assert_not_called()
        with self.assertRaises(ValueError):
            verification.verify_parallel([], (), SimpleNamespace(workers=4))

    def test_real_spawn_preserves_inventory_without_pickling_catalogue_or_store(self):
        files = [self.file(('fixture-' + str(index)).encode()) for index in range(150)]
        expected = reconcile.verify_files(inventory(self.first, files + files))
        for workers in (4, 8):
            with self.subTest(workers=workers):
                self.assertEqual(reconcile.verify_files(inventory(self.first, files + files), workers=workers), expected)

    def test_explicit_fallback_only_for_missing_bytes(self):
        file = self.file(b'second only', self.second)
        for workers in (1, 4, 8):
            with self.subTest(workers=workers):
                self.assertEqual(list(reconcile.verify_files(inventory(self.first, [file]), (self.second.root,), workers=workers)), [file.digest])
                error = self.error(lambda: reconcile.verify_files(inventory(self.first, [file]), workers=workers))
                self.assertEqual(error[0], ValueError)
                self.assertIn('missing', error[2])

    def test_corrupt_first_root_refuses_even_when_second_copy_is_good(self):
        file = self.file(b'correct')
        self.second.put(b'correct')
        target = self.first.root / VolumeBodyStore.object_key(file.digest)
        target.chmod(0o600)
        target.write_bytes(b'corrupt')
        errors = [self.error(lambda count=count: reconcile.verify_files(inventory(self.first, [file]), (self.second.root,), workers=count)) for count in (1, 4, 8)]
        self.assertTrue(all(error == errors[0] for error in errors))
        self.assertEqual(errors[0][1], 'body_digest_mismatch')

    def test_size_and_file_ceiling_preserve_refusals(self):
        file = self.file(b'correct')
        for size, code in ((file.size_bytes + 1, 'body_size_mismatch'), (MAXIMUM_FILE_BYTES + 1, 'body_too_large'), (True, 'body_size_mismatch')):
            wrong = replace(file, size_bytes=size)
            errors = [self.error(lambda count=count: reconcile.verify_files(inventory(self.first, [wrong]), workers=count)) for count in (1, 4, 8)]
            self.assertTrue(all(error == errors[0] for error in errors))
            self.assertEqual(errors[0][1], code)

    def test_object_prefix_and_root_symlinks_never_escape(self):
        file = self.file(b'outside', self.second)
        prefix = self.first.root / 'sha256' / file.digest[:2]
        prefix.mkdir(parents=True)
        target = prefix / file.digest
        target.symlink_to(self.second.root / VolumeBodyStore.object_key(file.digest))
        for workers in (1, 4, 8):
            error = self.error(lambda: reconcile.verify_files(inventory(self.first, [file]), workers=workers))
            self.assertEqual(error[1], 'body_path_unsafe')
        target.unlink(); prefix.rmdir()
        prefix.symlink_to(self.second.root / 'sha256' / file.digest[:2], target_is_directory=True)
        alias = self.root / 'alias'; alias.symlink_to(self.second.root, target_is_directory=True)
        for workers in (1, 4, 8):
            self.assertEqual(self.error(lambda: reconcile.verify_files(inventory(self.first, [file]), workers=workers))[1], 'body_path_unsafe')
            self.assertEqual(self.error(lambda: reconcile.verify_files(inventory(self.second, [file]), (alias,), workers=workers))[1], 'body_store_root_invalid')

    def test_first_input_error_wins_when_a_later_batch_finishes_first(self):
        files = [self.file(('original-' + str(index)).encode()) for index in range(65)]
        files[0] = replace(files[0], size_bytes=files[0].size_bytes + 1)
        last = self.first.root / VolumeBodyStore.object_key(files[-1].digest)
        last.chmod(0o600); last.write_bytes(b'x' * files[-1].size_bytes)
        serial = self.error(lambda: reconcile.verify_files(inventory(self.first, files)))
        self.assertEqual(serial[1], 'body_size_mismatch')
        with mock.patch.object(verification, '_verify_batch', delayed_native_worker):
            for workers in (4, 8):
                self.assertEqual(self.error(lambda: reconcile.verify_files(inventory(self.first, files), workers=workers)), serial)

    def test_batch_limits_and_internal_records_refuse_malformed_values(self):
        file = self.file(b'body')
        batch = verification.VerificationBatch(0, (file,))
        for invalid in (replace(batch, sequence=True), replace(batch, files=()), replace(batch, files=(file,) * 65),
                        replace(batch, files=(replace(file, size_bytes=MAXIMUM_FILE_BYTES), file)), replace(batch, record_type='unknown')):
            with self.assertRaises(ValueError):
                invalid.validate()
        failure = verification.VerificationFailure(verification.VerificationFailureKind.SERVICE, 'refused', code='body_digest_mismatch')
        self.assertLess(len(pickle.dumps(verification.VerificationResult(0, 0, failure))), 512)
        for invalid in (replace(failure, record_type='unknown'), replace(failure, kind='network'), replace(failure, code=None),
                        verification.VerificationFailure(verification.VerificationFailureKind.FILESYSTEM, 'refused', errno=True),
                        replace(failure, kind='service'), replace(failure, message=b'payload')):
            with self.assertRaises(ValueError):
                invalid.validate()

    def test_batches_bound_record_count_and_declared_bytes(self):
        files = [verification.VerificationFile(f'{index:064x}', MAXIMUM_FILE_BYTES // 3) for index in range(200)]
        batches = list(verification._batches(files))
        self.assertEqual([file for batch in batches for file in batch.files], files)
        for index, batch in enumerate(batches):
            batch.validate()
            self.assertEqual(batch.sequence, index)
            self.assertLessEqual(batch.size_bytes, MAXIMUM_FILE_BYTES)
            self.assertLessEqual(len(batch.files), verification.MAXIMUM_BATCH_FILES)

    def test_worker_payloads_are_discarded_and_failures_keep_no_traceback(self):
        class Payload:
            pass
        references = []
        def read(*_args):
            if references:
                self.assertIsNone(references[-1](), 'the previous payload remains held')
            value = Payload(); references.append(weakref.ref(value))
            return value
        files = tuple(verification.VerificationFile(f'{index:064x}', 10) for index in range(4))
        batch = verification.VerificationBatch(0, files)
        with mock.patch.object(verification, 'read_payload', side_effect=read), \
                mock.patch.object(verification, '_worker_initialization_failure', None):
            result = verification._verify_batch(batch)
        self.assertEqual(result, verification.VerificationResult(0, 4))
        self.assertTrue(all(reference() is None for reference in references))
        for refused in (ServiceRuntimeError('body_unreadable', 'refused'), ValueError('missing'),
                        FileNotFoundError(2, 'fixture missing', '/fixture/body')):
            with mock.patch.object(verification, 'read_payload', side_effect=refused), \
                    mock.patch.object(verification, '_worker_initialization_failure', None):
                result = verification._verify_batch(batch)
            result.validate(batch)
            self.assertEqual(result.verified, 0)
            self.assertFalse(hasattr(result.failure, '__traceback__'))
            self.assertEqual(self.error(result.failure.raise_error), (type(refused), getattr(refused, 'code', None), str(refused)))

    def test_worker_root_records_are_bounded_and_read_only(self):
        with mock.patch.object(verification, '_worker_stores', ()), \
                mock.patch.object(verification, '_worker_initialization_failure', None):
            for roots in ([verification.VerificationRoot(str(self.first.root), MAXIMUM_FILE_BYTES)],
                          (verification.VerificationRoot(str(self.first.root), MAXIMUM_FILE_BYTES),) * 129,
                          (SimpleNamespace(root=str(self.first.root)),),
                          (verification.VerificationRoot('relative', MAXIMUM_FILE_BYTES),),
                          (verification.VerificationRoot(str(self.first.root), True),)):
                verification._initialize_worker(roots)
                self.assertIsNotNone(verification._worker_initialization_failure)
                self.assertEqual(verification._worker_stores, ())
            verification._initialize_worker((verification.VerificationRoot(str(self.first.root), MAXIMUM_FILE_BYTES),))
            self.assertIsNone(verification._worker_initialization_failure)
            self.assertEqual(len(verification._worker_stores), 1)
            with self.assertRaises(ServiceRuntimeError):
                verification._worker_stores[0].put(b'no worker write authority')

    def test_pending_tasks_and_bytes_are_bounded_with_clean_spawn(self):
        limits = verification.VerificationLimits(4)
        counts = dict(pending=0, bytes=0, peak_pending=0, peak_bytes=0, submitted=0)
        contexts, arguments = [], []
        class Deferred:
            def __init__(self, batch): self.batch = batch
            def result(self):
                counts['pending'] -= 1; counts['bytes'] -= self.batch.size_bytes
                return verification.VerificationResult(self.batch.sequence, len(self.batch.files))
            def cancel(self): return True
        class Pool:
            def __init__(self, **kwargs):
                contexts.append(kwargs['mp_context'].get_start_method()); arguments.append(kwargs['initargs'])
                self.workers = kwargs['max_workers']
            def __enter__(self): return self
            def __exit__(self, *_args): pass
            def submit(self, _function, batch):
                counts['submitted'] += 1; counts['pending'] += 1; counts['bytes'] += batch.size_bytes
                counts['peak_pending'] = max(counts['peak_pending'], counts['pending'])
                counts['peak_bytes'] = max(counts['peak_bytes'], counts['bytes'])
                return Deferred(batch)
        # Large bodies exercise the byte ceiling first; tiny/zero bodies exercise
        # the independent task-count ceiling instead. Neither guard is redundant.
        for population, size, submitted in ((100, 3 * 1024**2, 50), (2048, 1, 32), (2048, 0, 32)):
            counts.update(pending=0, bytes=0, peak_pending=0, peak_bytes=0, submitted=0)
            contexts.clear(); arguments.clear()
            files = [verification.VerificationFile(f'{index:064x}', size) for index in range(population)]
            with self.subTest(size=size), mock.patch.object(verification, 'ProcessPoolExecutor', Pool):
                verification.verify_parallel(files, (self.first,), limits)
            self.assertEqual(contexts, ['spawn'])
            self.assertEqual(arguments, [((verification.VerificationRoot(str(self.first.root), MAXIMUM_FILE_BYTES),),)])
            self.assertLessEqual(counts['peak_pending'], limits.pending_batches)
            self.assertLessEqual(counts['peak_bytes'], limits.pending_bytes)
            self.assertEqual(counts['submitted'], submitted)
            self.assertEqual((counts['pending'], counts['bytes']), (0, 0))

    def test_untyped_incomplete_wrong_sequence_and_failed_replies_cannot_pass(self):
        file = self.file(b'body'); batch = verification.VerificationBatch(0, (file,))
        refusals = [None, True, {'verified': 1}, verification.VerificationResult(0, 0),
                    verification.VerificationResult(1, 1), verification.VerificationResult(0, True),
                    verification.VerificationResult(0, 1, record_type='unknown'),
                    verification.VerificationResult(0, 1, verification.VerificationFailure(verification.VerificationFailureKind.VALUE, 'failure'))]
        for answer in refusals:
            class Future:
                def result(self): return answer
                def cancel(self): return True
            class Pool:
                def __init__(self, **_kwargs): pass
                def __enter__(self): return self
                def __exit__(self, *_args): pass
                def submit(self, *_args): return Future()
            with self.subTest(answer=answer), mock.patch.object(verification, 'ProcessPoolExecutor', Pool):
                error = self.error(lambda: verification.verify_parallel(batch.files, (self.first,), verification.VerificationLimits(4)))
                self.assertEqual(error[1], 'catalogue_verification_result_invalid')

    def test_worker_crash_refuses_without_output_or_serial_fallback(self):
        base = bundle(self.root / 'base', [line('old', 'old')], ['old'])
        update = bundle(self.root / 'update', [line('new', 'new')], ['new'])
        with mock.patch.object(verification, '_verify_batch', crashed_worker), \
                mock.patch.object(reconcile, '_payload', side_effect=AssertionError('implicit serial fallback')):
            error = self.error(lambda: reconcile.write_reconciled(base, (update,), request(base, additions=('new',)),
                                                                 self.root / 'refused', observation(base), verification_workers=4))
        self.assertEqual(error[1], 'catalogue_verification_worker_failed')
        self.assertFalse((self.root / 'refused').exists())

    def test_corrupt_bytes_refuse_before_any_output(self):
        base = bundle(self.root / 'base', [line('old', 'old')], ['old'])
        update = bundle(self.root / 'update', [line('new', 'new')], ['new'])
        file = update.items[0].package.files[0]
        target = update.folder / 'blobs' / VolumeBodyStore.object_key(file.digest)
        target.chmod(0o600); target.write_bytes(b'bad')
        for form_index, form in enumerate(reconcile.BUNDLE_FORMATS):
            for workers in (1, 4, 8):
                output = self.root / f'refused-{form_index}-{workers}'
                error = self.error(lambda: reconcile.write_reconciled(base, (update,), request(base, additions=('new',)), output,
                                                                     observation(base), bundle_format=form, verification_workers=workers))
                self.assertEqual(error[1], 'body_digest_mismatch')
                self.assertFalse(output.exists())

    def test_both_native_bundle_versions_keep_exact_serial_process_proofs(self):
        base = bundle(self.root / 'base', [line('old', 'old')], ['old'])
        update = bundle(self.root / 'update', [line('new', 'new')], ['new'])
        change = request(base, additions=('new',))
        for form_index, form in enumerate(reconcile.BUNDLE_FORMATS):
            results, proofs = [], []
            for workers in (1, 4, 8):
                output = self.root / f'proof-{form_index}-{workers}'
                results.append(reconcile.write_reconciled(base, (update,), change, output, observation(base),
                                                         bundle_format=form, verification_workers=workers))
                proofs.append((output / reconcile.PROOF_FILE).read_bytes())
            self.assertTrue(all(result == results[0] for result in results))
            self.assertTrue(all(proof == proofs[0] for proof in proofs))
            # Read each native output version as the next baseline; the empty
            # update path still checks all old bytes from its explicit root.
            next_base = reconcile.load_bundle(output, ('MIT',))
            empty_results, empty_proofs = [], []
            for workers in (1, 4, 8):
                empty_output = self.root / f'empty-update-{form_index}-{workers}'
                empty_results.append(reconcile.write_reconciled(next_base, (), request(next_base), empty_output,
                    observation(next_base), extra_roots=(base.folder / 'blobs',), bundle_format=form, verification_workers=workers))
                empty_proofs.append((empty_output / reconcile.PROOF_FILE).read_bytes())
            self.assertTrue(all(result == empty_results[0] for result in empty_results))
            self.assertTrue(all(proof == empty_proofs[0] for proof in empty_proofs))

    def test_cli_workers_are_opt_in_and_metadata_mode_reads_no_bodies(self):
        base = bundle(self.root / 'base', [line('old', 'old')], ['old'])
        update = bundle(self.root / 'update', [line('new', 'new')], ['new'])
        change = request(base, additions=('new',)); control = self.root / 'changes.json'
        control.write_text(json.dumps(change.to_dict()))
        common = ['--base-bundle', str(base.folder), '--update-bundle', str(update.folder), '--changes', str(control),
                  '--output', str(self.root / 'written'), '--verification-workers', '4']
        with mock.patch('publish_catalogue_delta.active_catalogue', return_value=observation(base)), \
                mock.patch.object(reconcile, 'verify_files', side_effect=AssertionError('metadata mode read bodies')), redirect_stdout(io.StringIO()):
            self.assertEqual(reconcile.main(common), 0)
        self.assertFalse((self.root / 'written').exists())
        with mock.patch('publish_catalogue_delta.active_catalogue', return_value=observation(base)), \
                mock.patch.object(reconcile, 'verify_files', wraps=reconcile.verify_files) as verify, redirect_stdout(io.StringIO()):
            self.assertEqual(reconcile.main(common + ['--write']), 0)
        self.assertEqual([call.kwargs['workers'] for call in verify.call_args_list], [4, 4])
        for bad in ('0', '9', 'true'):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                reconcile.main(common[:-1] + [bad])
            self.assertEqual(caught.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
