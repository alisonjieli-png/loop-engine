"""Bounded local file verification inside the existing catalogue reconciliation owner.

Workers are clean-spawn native operations, not Loop runtimes. Only explicit
volume roots and digest/size batches cross the process boundary. Results carry
counts or typed refusals, never payloads, catalogues or traceback frames.
"""
from __future__ import annotations

from collections import deque
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from enum import Enum
import multiprocessing
from pathlib import Path

from loop_engine.core.service_runtime.catalogue_packages import (
    MAXIMUM_FILE_BYTES, MAXIMUM_PACKAGE_BYTES, VolumeBodyStore, exact_digest,
)
from loop_engine.core.service_runtime.records import ServiceRuntimeError

MAXIMUM_WORKERS = 8
MAXIMUM_BATCH_FILES = 64
MAXIMUM_ROOTS = 128
BATCH_VERSION = 'catalogue_file_verification_batch/v1'
RESULT_VERSION = 'catalogue_file_verification_result/v1'
ERROR_VERSION = 'catalogue_file_verification_error/v1'


@dataclass(frozen=True, slots=True)
class VerificationLimits:
    """The caller selects concurrency; fixed task and byte ceilings bound the queue."""
    workers: int = 1

    def __post_init__(self):
        if type(self.workers) is not int or not 1 <= self.workers <= MAXIMUM_WORKERS:
            raise ValueError(f'verification workers must be a whole number from 1 to {MAXIMUM_WORKERS}')

    @property
    def pending_batches(self):
        return self.workers * 2

    @property
    def pending_bytes(self):
        return self.workers * MAXIMUM_FILE_BYTES


@dataclass(frozen=True, slots=True)
class VerificationRoot:
    """Read-only volume configuration; no store object or catalogue is serialized."""
    root: str
    maximum_file_bytes: int

    def validate(self):
        if (not isinstance(self.root, str) or not self.root or len(self.root) > 4096
                or not Path(self.root).is_absolute() or type(self.maximum_file_bytes) is not int
                or not 1 <= self.maximum_file_bytes <= MAXIMUM_PACKAGE_BYTES):
            raise ValueError('invalid verification root configuration')


def validate_file(file):
    """Validate the complete metadata population before any body is read."""
    exact_digest(file.digest)
    if type(file.size_bytes) is not int or file.size_bytes < 0:
        raise ServiceRuntimeError('body_size_mismatch', 'a read names the exact size it expects')
    if file.size_bytes > MAXIMUM_FILE_BYTES:
        raise ServiceRuntimeError('body_too_large', "the object is larger than this store's file allowance")


@dataclass(frozen=True, slots=True)
class VerificationFile:
    """One body reference, without payload or catalogue metadata."""
    digest: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class VerificationBatch:
    """An ordered window whose declared bytes fit one file allowance."""
    sequence: int
    files: tuple[VerificationFile, ...]
    record_type: str = BATCH_VERSION

    @property
    def size_bytes(self):
        return sum(file.size_bytes for file in self.files)

    def validate(self):
        if (self.record_type != BATCH_VERSION or type(self.sequence) is not int or self.sequence < 0
                or type(self.files) is not tuple or not 1 <= len(self.files) <= MAXIMUM_BATCH_FILES):
            raise ValueError('invalid verification batch')
        for file in self.files:
            if type(file) is not VerificationFile:
                raise ValueError('invalid verification file record')
            validate_file(file)
        if self.size_bytes > MAXIMUM_FILE_BYTES:
            raise ValueError('verification batch exceeds its byte ceiling')


class VerificationFailureKind(str, Enum):
    """The three native refusal forms the worker can return."""
    SERVICE = 'service'
    VALUE = 'value'
    FILESYSTEM = 'os'


@dataclass(frozen=True, slots=True)
class VerificationFailure:
    """A scalar body-store refusal, never an exception or traceback object."""
    kind: VerificationFailureKind
    message: str
    code: str | None = None
    errno: int | None = None
    filename: str | None = None
    record_type: str = ERROR_VERSION

    def validate(self):
        if (self.record_type != ERROR_VERSION or type(self.kind) is not VerificationFailureKind
                or not isinstance(self.message, str) or len(self.message) > 4096):
            raise ValueError('invalid verification failure record')
        if self.kind == VerificationFailureKind.SERVICE:
            if not isinstance(self.code, str) or not self.code or len(self.code) > 200 or self.errno is not None or self.filename is not None:
                raise ValueError('invalid verification service refusal')
        elif self.kind == VerificationFailureKind.VALUE:
            if any(value is not None for value in (self.code, self.errno, self.filename)):
                raise ValueError('invalid verification value refusal')
        elif (self.code is not None or type(self.errno) is not int
              or (self.filename is not None and (not isinstance(self.filename, str) or len(self.filename) > 4096))):
            raise ValueError('invalid verification filesystem refusal')

    def raise_error(self):
        self.validate()
        if self.kind == VerificationFailureKind.SERVICE:
            raise ServiceRuntimeError(self.code, self.message)
        if self.kind == VerificationFailureKind.FILESYSTEM:
            raise OSError(self.errno, self.message, self.filename)
        raise ValueError(self.message)


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """The checked prefix of one exact batch and its first refusal, if any."""
    sequence: int
    verified: int
    failure: VerificationFailure | None = None
    record_type: str = RESULT_VERSION

    def validate(self, batch):
        if (self.record_type != RESULT_VERSION or type(self.sequence) is not int or self.sequence != batch.sequence
                or type(self.verified) is not int or not 0 <= self.verified <= len(batch.files)):
            raise ValueError('invalid verification result')
        if self.failure is None:
            if self.verified != len(batch.files):
                raise ValueError('incomplete verification result')
        elif type(self.failure) is not VerificationFailure or self.verified >= len(batch.files):
            raise ValueError('invalid verification refusal position')
        else:
            self.failure.validate()


def read_payload(file, stores):
    """Use declared stores in order; only a missing body permits the next root."""
    for store in stores:
        try:
            return store.read(file.digest, file.size_bytes)
        except ServiceRuntimeError as error:
            if error.code != 'body_missing':
                raise
    raise ValueError('a required baseline or update blob is missing; supply explicit body roots')


def _failure(error):
    if isinstance(error, ServiceRuntimeError):
        return VerificationFailure(VerificationFailureKind.SERVICE, str(error), code=error.code)
    if isinstance(error, OSError):
        return VerificationFailure(VerificationFailureKind.FILESYSTEM, error.strerror, errno=error.errno, filename=error.filename)
    return VerificationFailure(VerificationFailureKind.VALUE, str(error))


_worker_stores = ()
_worker_initialization_failure = None


def _initialize_worker(roots):
    global _worker_stores, _worker_initialization_failure
    _worker_stores, _worker_initialization_failure = (), None
    try:
        if type(roots) is not tuple or len(roots) > MAXIMUM_ROOTS:
            raise ValueError('invalid verification root population')
        for root in roots:
            if type(root) is not VerificationRoot:
                raise ValueError('invalid verification root record')
            root.validate()
        _worker_stores = tuple(VolumeBodyStore(root.root, maximum_file_bytes=root.maximum_file_bytes) for root in roots)
    except (ValueError, OSError) as error:
        _worker_initialization_failure = _failure(error)


def _verify_batch(batch):
    if type(batch) is not VerificationBatch:
        raise ValueError('typed verification batch required')
    batch.validate()
    if _worker_initialization_failure is not None:
        return VerificationResult(batch.sequence, 0, _worker_initialization_failure)
    for index, file in enumerate(batch.files):
        try:
            # Do not return or retain a payload in a result or exception record.
            read_payload(file, _worker_stores)
        except (ValueError, OSError) as error:
            return VerificationResult(batch.sequence, index, _failure(error))
    return VerificationResult(batch.sequence, len(batch.files))


def _batches(files):
    entries, size, sequence = [], 0, 0
    for file in files:
        if entries and (len(entries) == MAXIMUM_BATCH_FILES or size + file.size_bytes > MAXIMUM_FILE_BYTES):
            yield VerificationBatch(sequence, tuple(entries))
            entries, size, sequence = [], 0, sequence + 1
        entries.append(VerificationFile(file.digest, file.size_bytes))
        size += file.size_bytes
    if entries:
        yield VerificationBatch(sequence, tuple(entries))


def verify_parallel(files, stores, limits):
    """Bound submitted metadata and bytes; observe results in serial file order."""
    if type(limits) is not VerificationLimits:
        raise ValueError('typed verification limits required')
    limits.__post_init__()
    if len(stores) > MAXIMUM_ROOTS or any(type(store) is not VolumeBodyStore for store in stores):
        raise ValueError('parallel verification requires bounded explicit volume body roots')
    roots = tuple(VerificationRoot(str(store.root), store.maximum_file_bytes) for store in stores)
    for root in roots:
        root.validate()
    batches = iter(_batches(files))
    first = next(batches, None)
    if first is None:
        return
    pending, in_flight_bytes = deque(), 0

    def consume():
        batch, future = pending.popleft()
        try:
            result = future.result()
        except Exception as error:
            raise ServiceRuntimeError('catalogue_verification_worker_failed', 'a verification worker failed; no complete byte proof is available') from error
        try:
            if type(result) is not VerificationResult:
                raise ValueError('untyped verification result')
            result.validate(batch)
        except ValueError as error:
            raise ServiceRuntimeError('catalogue_verification_result_invalid', 'a verification worker returned an invalid result') from error
        if result.failure is not None:
            result.failure.raise_error()
        return batch.size_bytes

    # Spawn cannot inherit the caller's already-loaded catalogue as fork would.
    with ProcessPoolExecutor(max_workers=limits.workers, mp_context=multiprocessing.get_context('spawn'),
                             initializer=_initialize_worker, initargs=(roots,)) as pool:
        try:
            batch = first
            while batch is not None:
                batch.validate()
                while pending and (len(pending) >= limits.pending_batches or in_flight_bytes + batch.size_bytes > limits.pending_bytes):
                    in_flight_bytes -= consume()
                try:
                    future = pool.submit(_verify_batch, batch)
                except Exception as error:
                    raise ServiceRuntimeError('catalogue_verification_worker_failed', 'a verification worker failed; no complete byte proof is available') from error
                pending.append((batch, future))
                in_flight_bytes += batch.size_bytes
                batch = next(batches, None)
            while pending:
                in_flight_bytes -= consume()
        finally:
            for _batch, future in pending:
                future.cancel()
