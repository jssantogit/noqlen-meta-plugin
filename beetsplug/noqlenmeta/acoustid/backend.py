from __future__ import annotations

import json
import math
import os
import stat
import subprocess
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from .domain import (
    AcoustIDEvidenceReason,
    AcoustIDFingerprintMaterial,
    AcoustIDFingerprintOrigin,
    AcoustIDSourceSnapshot,
    FingerprintBackendResult,
    FingerprintPreparationResult,
    SelectedAcoustIDItem,
)
from .settings import AcoustIDSettings

FPCALC_LENGTH_SECONDS = 120
STDOUT_LIMIT_BYTES = 1_048_576
STDERR_LIMIT_BYTES = 65_536
_TERMINATION_GRACE_SECONDS = 0.5
_READER_CLEANUP_GRACE_SECONDS = 0.5
_POLL_INTERVAL_SECONDS = 0.01
_CREDENTIAL_ENVIRONMENT_KEY = "NOQLENMETA_ACOUSTID_API_KEY"
_READER_THREAD_NAME_PREFIX = "noqlen-acoustid-pipe-reader-"


class SourceSnapshotError(Exception):
    def __init__(self) -> None:
        super().__init__("source snapshot unavailable")


class FingerprintBackendUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("fingerprint backend unavailable")


class FingerprintBackendFailure(Exception):
    def __init__(self) -> None:
        super().__init__("fingerprint backend failed")


class _ProcessUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("fingerprint process unavailable")


class _ProcessFailure(Exception):
    def __init__(self) -> None:
        super().__init__("fingerprint process failed")


@dataclass(frozen=True, slots=True)
class _ProcessResult:
    stdout: bytes = field(repr=False)
    stderr: bytes = field(repr=False)


class FingerprintBackend(Protocol):
    def fingerprint(self, path: bytes | str) -> FingerprintBackendResult: ...


class _Runner(Protocol):
    def __call__(
        self, argv: Sequence[bytes | str], timeout_seconds: float
    ) -> _ProcessResult: ...


def acquire_source_snapshot(
    path: bytes | str,
    *,
    stat_function: Callable[..., os.stat_result] = os.stat,
) -> AcoustIDSourceSnapshot:
    if not isinstance(path, (bytes, str)) or not path:
        raise SourceSnapshotError
    try:
        result = stat_function(path, follow_symlinks=False)
        mode = result.st_mode
        if isinstance(mode, bool) or not isinstance(mode, int) or not stat.S_ISREG(mode):
            raise SourceSnapshotError
        values = (result.st_dev, result.st_ino, result.st_size, result.st_mtime_ns)
        if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
            raise SourceSnapshotError
        return AcoustIDSourceSnapshot(*values)
    except SourceSnapshotError:
        raise
    except (AttributeError, NotImplementedError, OSError, TypeError, ValueError):
        raise SourceSnapshotError from None


def verify_source_snapshot(
    path: bytes | str,
    expected: AcoustIDSourceSnapshot,
    *,
    snapshot_function: Callable[[bytes | str], AcoustIDSourceSnapshot] = acquire_source_snapshot,
) -> bool:
    if not isinstance(expected, AcoustIDSourceSnapshot):
        raise SourceSnapshotError
    try:
        return snapshot_function(path) == expected
    except SourceSnapshotError:
        return False


def prepare_fingerprint(
    selected: SelectedAcoustIDItem,
    settings: AcoustIDSettings,
    invocation_allows_missing_calculation: bool,
    backend_factory: Callable[[], FingerprintBackend],
    *,
    snapshot_function: Callable[[bytes | str], AcoustIDSourceSnapshot] = acquire_source_snapshot,
) -> FingerprintPreparationResult:
    if type(selected) is not SelectedAcoustIDItem:
        raise ValueError("fingerprint preparation requires a selected Item")
    if not isinstance(settings, AcoustIDSettings):
        raise ValueError("fingerprint preparation requires AcoustID settings")
    if not isinstance(invocation_allows_missing_calculation, bool):
        raise ValueError("fingerprint calculation authority must be boolean")
    existing = selected.existing_values
    fingerprint = existing._reusable_fingerprint()
    if settings.reuse_existing and fingerprint is not None:
        assert existing.duration_seconds is not None
        material = AcoustIDFingerprintMaterial(
            selected.local_key,
            fingerprint,
            existing.duration_seconds,
            AcoustIDFingerprintOrigin.EXISTING,
        )
        return FingerprintPreparationResult(
            selected.local_key, material, AcoustIDEvidenceReason.FINGERPRINT_REUSED
        )
    if not (settings.compute_missing or invocation_allows_missing_calculation):
        return FingerprintPreparationResult(
            selected.local_key, None, AcoustIDEvidenceReason.FINGERPRINT_MISSING
        )
    try:
        before = snapshot_function(selected.media_path)
    except SourceSnapshotError:
        return FingerprintPreparationResult(
            selected.local_key, None, AcoustIDEvidenceReason.STALE_SOURCE_FILE
        )
    try:
        backend = backend_factory()
        generated = backend.fingerprint(selected.media_path)
    except FingerprintBackendUnavailable:
        return FingerprintPreparationResult(
            selected.local_key,
            None,
            AcoustIDEvidenceReason.FINGERPRINT_BACKEND_UNAVAILABLE,
        )
    except FingerprintBackendFailure:
        return FingerprintPreparationResult(
            selected.local_key, None, AcoustIDEvidenceReason.FINGERPRINT_FAILED
        )
    if not isinstance(generated, FingerprintBackendResult):
        raise TypeError("fingerprint backend returned an unsupported result")
    try:
        after = snapshot_function(selected.media_path)
    except SourceSnapshotError:
        return FingerprintPreparationResult(
            selected.local_key, None, AcoustIDEvidenceReason.STALE_SOURCE_FILE
        )
    if before != after:
        return FingerprintPreparationResult(
            selected.local_key, None, AcoustIDEvidenceReason.STALE_SOURCE_FILE
        )
    material = AcoustIDFingerprintMaterial(
        selected.local_key,
        generated._fingerprint_text(),
        generated.duration_seconds,
        AcoustIDFingerprintOrigin.GENERATED,
        after,
    )
    return FingerprintPreparationResult(
        selected.local_key, material, AcoustIDEvidenceReason.FINGERPRINT_GENERATED
    )


@dataclass(frozen=True, slots=True)
class FpcalcFingerprintBackend:
    executable: str = field(repr=False)
    timeout_seconds: float
    runner: _Runner = field(default=None, repr=False, compare=False)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if not isinstance(self.executable, str) or not self.executable.strip():
            raise ValueError("fpcalc backend configuration is invalid")
        try:
            timeout_seconds = _validated_timeout(self.timeout_seconds)
        except _ProcessFailure:
            raise ValueError("fpcalc backend configuration is invalid") from None
        object.__setattr__(self, "timeout_seconds", timeout_seconds)
        object.__setattr__(
            self,
            "runner",
            self.runner if self.runner is not None else run_bounded_process,
        )

    @classmethod
    def from_settings(
        cls, settings: AcoustIDSettings, *, runner: _Runner | None = None
    ) -> FpcalcFingerprintBackend:
        if not isinstance(settings, AcoustIDSettings):
            raise ValueError("fpcalc backend requires AcoustID settings")
        return cls(
            settings.fpcalc,
            settings.timeout_seconds,
            runner if runner is not None else run_bounded_process,
        )

    def fingerprint(self, path: bytes | str) -> FingerprintBackendResult:
        if not isinstance(path, (bytes, str)) or not path:
            raise FingerprintBackendFailure
        argv: tuple[bytes | str, ...] = (
            self.executable,
            "-json",
            "-length",
            str(FPCALC_LENGTH_SECONDS),
            "--",
            path,
        )
        try:
            result = self.runner(argv, self.timeout_seconds)
        except _ProcessUnavailable:
            raise FingerprintBackendUnavailable from None
        except _ProcessFailure:
            raise FingerprintBackendFailure from None
        return _parse_fpcalc_json(result.stdout)


def run_bounded_process(
    argv: Sequence[bytes | str],
    timeout_seconds: float,
    *,
    popen_factory: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
) -> _ProcessResult:
    timeout_seconds = _validated_timeout(timeout_seconds)
    environment = os.environ.copy()
    environment.pop(_CREDENTIAL_ENVIRONMENT_KEY, None)
    try:
        process = popen_factory(
            tuple(argv),
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )
    except FileNotFoundError:
        raise _ProcessUnavailable from None
    except (OSError, ValueError):
        raise _ProcessFailure from None
    if process.stdout is None or process.stderr is None:
        try:
            _terminate_and_reap(process)
        finally:
            _close_streams(process.stdout, process.stderr)
        raise _ProcessFailure
    try:
        stdout_descriptor = _nonblocking_descriptor(process.stdout)
        stderr_descriptor = _nonblocking_descriptor(process.stderr)
    except _ProcessFailure:
        try:
            _terminate_and_reap(process)
        finally:
            _close_streams(process.stdout, process.stderr)
        raise

    overflow = threading.Event()
    read_error = threading.Event()
    stdout = bytearray()
    stderr = bytearray()

    stop_reading = threading.Event()

    def drain(descriptor: int, retained: bytearray, limit: int) -> None:
        try:
            while not stop_reading.is_set():
                try:
                    chunk = os.read(descriptor, 65_536)
                except BlockingIOError:
                    time.sleep(_POLL_INTERVAL_SECONDS)
                    continue
                if not chunk:
                    return
                remaining = limit - len(retained)
                if len(chunk) > remaining:
                    retained.extend(chunk[:remaining])
                    overflow.set()
                    return
                retained.extend(chunk)
        except (OSError, ValueError):
            read_error.set()

    threads = (
        threading.Thread(
            target=drain,
            args=(stdout_descriptor, stdout, STDOUT_LIMIT_BYTES),
            name=f"{_READER_THREAD_NAME_PREFIX}stdout",
        ),
        threading.Thread(
            target=drain,
            args=(stderr_descriptor, stderr, STDERR_LIMIT_BYTES),
            name=f"{_READER_THREAD_NAME_PREFIX}stderr",
        ),
    )
    for thread in threads:
        thread.daemon = True
        thread.start()
    deadline = time.monotonic() + timeout_seconds
    failed = False
    try:
        while process.poll() is None:
            if overflow.is_set() or read_error.is_set() or time.monotonic() >= deadline:
                failed = True
                _terminate_and_reap(process)
                break
            time.sleep(_POLL_INTERVAL_SECONDS)
        if process.poll() is None:
            _terminate_and_reap(process)
            failed = True
        if not failed and not _join_threads(threads, _READER_CLEANUP_GRACE_SECONDS):
            failed = True
        if failed or overflow.is_set() or read_error.is_set() or process.returncode != 0:
            raise _ProcessFailure
        return _ProcessResult(bytes(stdout), bytes(stderr))
    except _ProcessFailure:
        if process.poll() is None:
            _terminate_and_reap(process)
        raise
    except (OSError, subprocess.SubprocessError):
        if process.poll() is None:
            _terminate_and_reap(process)
        raise _ProcessFailure from None
    finally:
        stop_reading.set()
        _close_streams(process.stdout, process.stderr)
        if not _join_threads(threads, _READER_CLEANUP_GRACE_SECONDS):
            raise _ProcessFailure from None


def _validated_timeout(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _ProcessFailure
    timeout_seconds = float(value)
    if not math.isfinite(timeout_seconds) or not 1.0 <= timeout_seconds <= 60.0:
        raise _ProcessFailure
    return timeout_seconds


def _nonblocking_descriptor(stream: object) -> int:
    try:
        descriptor = stream.fileno()  # type: ignore[attr-defined]
        if isinstance(descriptor, bool) or not isinstance(descriptor, int) or descriptor < 0:
            raise ValueError
        os.set_blocking(descriptor, False)
    except (AttributeError, OSError, TypeError, ValueError):
        raise _ProcessFailure from None
    return descriptor


def _join_threads(threads: tuple[threading.Thread, ...], grace_seconds: float) -> bool:
    deadline = time.monotonic() + grace_seconds
    for thread in threads:
        thread.join(max(0.0, deadline - time.monotonic()))
    return not any(thread.is_alive() for thread in threads)


def _close_streams(*streams: object) -> None:
    for stream in streams:
        if stream is None:
            continue
        try:
            stream.close()  # type: ignore[attr-defined]
        except (OSError, ValueError):
            pass


def _terminate_and_reap(process: subprocess.Popen[bytes]) -> None:
    try:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=_TERMINATION_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=_TERMINATION_GRACE_SECONDS)
    except (OSError, subprocess.SubprocessError):
        raise _ProcessFailure from None


def _parse_fpcalc_json(stdout: bytes) -> FingerprintBackendResult:
    try:
        text = stdout.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
        if not isinstance(value, dict):
            raise ValueError
        duration = value["duration"]
        fingerprint = value["fingerprint"]
        return FingerprintBackendResult(duration, fingerprint)
    except (KeyError, TypeError, UnicodeDecodeError, ValueError, json.JSONDecodeError):
        raise FingerprintBackendFailure from None
