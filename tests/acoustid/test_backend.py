from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import threading
import time
from dataclasses import replace
from types import SimpleNamespace

import pytest
from beets.library import Item

from beetsplug.noqlenmeta.acoustid import (
    AcoustIDEvidenceReason,
    AcoustIDExistingValues,
    AcoustIDFingerprintOrigin,
    AcoustIDSourceSnapshot,
    FingerprintBackendFailure,
    FingerprintBackendResult,
    FingerprintBackendUnavailable,
    FpcalcFingerprintBackend,
    SelectedAcoustIDItem,
    SourceSnapshotError,
    acquire_source_snapshot,
    default_acoustid_settings,
    prepare_fingerprint,
    verify_source_snapshot,
)
from beetsplug.noqlenmeta.acoustid.backend import (
    _READER_THREAD_NAME_PREFIX,
    STDERR_LIMIT_BYTES,
    STDOUT_LIMIT_BYTES,
    _ProcessFailure,
    _ProcessResult,
    run_bounded_process,
)
from beetsplug.noqlenmeta.acoustid.domain import _MAX_FINGERPRINT_LENGTH

PRIVATE_PATH = b"/private/music/track.flac"
PRIVATE_FINGERPRINT = "private-synthetic-fingerprint"


def selected(
    *, fingerprint: object = None, duration: object = 100
) -> SelectedAcoustIDItem:
    item = Item(
        id=1,
        album_id=None,
        path=PRIVATE_PATH,
        length=duration,
        acoustid_fingerprint=fingerprint,
    )
    return SelectedAcoustIDItem(
        "library-item:1",
        1,
        None,
        item,
        item.path,
        AcoustIDExistingValues.from_stored(None, fingerprint, duration),
    )


def snapshot(**changes: int) -> AcoustIDSourceSnapshot:
    values = {"device": 1, "inode": 2, "size": 3, "mtime_ns": 4}
    values.update(changes)
    return AcoustIDSourceSnapshot(**values)


class Backend:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result or FingerprintBackendResult(120, PRIVATE_FINGERPRINT)
        self.error = error
        self.paths: list[bytes | str] = []

    def fingerprint(self, path: bytes | str) -> FingerprintBackendResult:
        self.paths.append(path)
        if self.error is not None:
            raise self.error
        return self.result


def test_reusable_existing_material_is_fully_lazy() -> None:
    calls: list[str] = []
    settings = default_acoustid_settings()

    result = prepare_fingerprint(
        selected(fingerprint=PRIVATE_FINGERPRINT),
        settings,
        False,
        lambda: calls.append("factory"),  # type: ignore[arg-type,func-returns-value]
        snapshot_function=lambda path: calls.append("snapshot"),  # type: ignore[arg-type,func-returns-value]
    )

    assert result.reason is AcoustIDEvidenceReason.FINGERPRINT_REUSED
    assert result.material is not None
    assert result.material.origin is AcoustIDFingerprintOrigin.EXISTING
    assert result.material.source_snapshot is None
    assert calls == []
    assert PRIVATE_FINGERPRINT not in repr(result)
    assert PRIVATE_PATH.decode() not in repr(result)


def test_unauthorized_missing_or_malformed_material_is_fully_lazy() -> None:
    for fingerprint in (None, " padded "):
        calls: list[str] = []

        def create_backend(calls=calls):
            return calls.append("factory")

        def take_snapshot(path, calls=calls):
            return calls.append("snapshot")

        result = prepare_fingerprint(
            selected(fingerprint=fingerprint),
            default_acoustid_settings(),
            False,
            create_backend,  # type: ignore[arg-type]
            snapshot_function=take_snapshot,  # type: ignore[arg-type]
        )
        assert result.reason is AcoustIDEvidenceReason.FINGERPRINT_MISSING
        assert result.material is None
        assert calls == []


@pytest.mark.parametrize("authority", ["settings", "invocation"])
def test_generation_authority_runs_backend_once_after_pre_snapshot(authority: str) -> None:
    events: list[str] = []
    backend = Backend()
    settings = replace(default_acoustid_settings(), compute_missing=authority == "settings")

    def snapshots(path):
        events.append("snapshot")
        return snapshot()

    def factory():
        events.append("factory")
        return backend

    result = prepare_fingerprint(
        selected(fingerprint=" malformed "),
        settings,
        authority == "invocation",
        factory,
        snapshot_function=snapshots,
    )

    assert result.reason is AcoustIDEvidenceReason.FINGERPRINT_GENERATED
    assert events == ["snapshot", "factory", "snapshot"]
    assert backend.paths == [PRIVATE_PATH]
    assert result.material is not None
    assert result.material.origin is AcoustIDFingerprintOrigin.GENERATED
    assert result.material.source_snapshot == snapshot()


def test_reuse_disabled_generates_instead_of_using_stored_material() -> None:
    backend = Backend()
    result = prepare_fingerprint(
        selected(fingerprint="stored-private"),
        replace(default_acoustid_settings(), reuse_existing=False, compute_missing=True),
        False,
        lambda: backend,
        snapshot_function=lambda path: snapshot(),
    )

    assert result.reason is AcoustIDEvidenceReason.FINGERPRINT_GENERATED
    assert backend.paths == [PRIVATE_PATH]


def test_pre_snapshot_failure_prevents_backend_creation() -> None:
    calls: list[str] = []

    def fail(path):
        raise SourceSnapshotError

    result = prepare_fingerprint(
        selected(),
        replace(default_acoustid_settings(), compute_missing=True),
        False,
        lambda: calls.append("factory"),  # type: ignore[arg-type,func-returns-value]
        snapshot_function=fail,
    )

    assert result.reason is AcoustIDEvidenceReason.STALE_SOURCE_FILE
    assert calls == []


@pytest.mark.parametrize("mode", ["post-failure", "changed"])
def test_post_snapshot_failure_or_change_discards_generated_material(mode: str) -> None:
    after = SourceSnapshotError() if mode == "post-failure" else snapshot(size=4)
    values = iter([snapshot(), after])

    def snapshots(path):
        value = next(values)
        if isinstance(value, Exception):
            raise value
        return value

    result = prepare_fingerprint(
        selected(),
        replace(default_acoustid_settings(), compute_missing=True),
        False,
        Backend,
        snapshot_function=snapshots,
    )

    assert result.reason is AcoustIDEvidenceReason.STALE_SOURCE_FILE
    assert result.material is None


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (
            FingerprintBackendUnavailable(),
            AcoustIDEvidenceReason.FINGERPRINT_BACKEND_UNAVAILABLE,
        ),
        (FingerprintBackendFailure(), AcoustIDEvidenceReason.FINGERPRINT_FAILED),
    ],
)
def test_declared_backend_errors_map_to_safe_reasons(error: Exception, reason) -> None:
    backend = Backend(error=error)
    result = prepare_fingerprint(
        selected(),
        replace(default_acoustid_settings(), compute_missing=True),
        False,
        lambda: backend,
        snapshot_function=lambda path: snapshot(),
    )

    assert result.reason is reason
    assert result.material is None
    assert PRIVATE_PATH.decode() not in repr(result)
    assert PRIVATE_FINGERPRINT not in repr(result)


def test_programmer_errors_are_not_swallowed() -> None:
    with pytest.raises(RuntimeError, match="programmer"):
        prepare_fingerprint(
            selected(),
            replace(default_acoustid_settings(), compute_missing=True),
            False,
            lambda: (_ for _ in ()).throw(RuntimeError("programmer")),
            snapshot_function=lambda path: snapshot(),
        )


def test_regular_file_snapshot_and_later_verification(tmp_path) -> None:
    source = tmp_path / "track.flac"
    source.write_bytes(b"synthetic")

    captured = acquire_source_snapshot(os.fsencode(source))

    actual = os.stat(source, follow_symlinks=False)
    assert captured == AcoustIDSourceSnapshot(
        actual.st_dev, actual.st_ino, actual.st_size, actual.st_mtime_ns
    )
    assert verify_source_snapshot(os.fsencode(source), captured)
    source.write_bytes(b"changed-content")
    assert not verify_source_snapshot(os.fsencode(source), captured)
    source.unlink()
    assert not verify_source_snapshot(os.fsencode(source), captured)


def test_snapshot_rejects_symlink_directory_and_non_regular_file(tmp_path) -> None:
    source = tmp_path / "track.flac"
    source.write_bytes(b"synthetic")
    link = tmp_path / "private-link"
    link.symlink_to(source)

    for path in (link, tmp_path):
        with pytest.raises(SourceSnapshotError) as captured:
            acquire_source_snapshot(os.fsencode(path))
        assert str(path) not in str(captured.value)

    fake = SimpleNamespace(st_mode=stat.S_IFIFO, st_dev=1, st_ino=2, st_size=3, st_mtime_ns=4)
    with pytest.raises(SourceSnapshotError):
        acquire_source_snapshot(PRIVATE_PATH, stat_function=lambda *args, **kwargs: fake)


@pytest.mark.parametrize(
    "field", ["st_mode", "st_dev", "st_ino", "st_size", "st_mtime_ns"]
)
def test_snapshot_rejects_malformed_stat_fields(field: str) -> None:
    values = {
        "st_mode": stat.S_IFREG,
        "st_dev": 1,
        "st_ino": 2,
        "st_size": 3,
        "st_mtime_ns": 4,
    }
    values[field] = True

    with pytest.raises(SourceSnapshotError) as captured:
        acquire_source_snapshot(
            PRIVATE_PATH,
            stat_function=lambda *args, **kwargs: SimpleNamespace(**values),
        )
    assert PRIVATE_PATH.decode() not in str(captured.value)


def test_snapshot_fails_closed_without_no_follow_support() -> None:
    def unsupported(path):
        raise AssertionError("must not be reached")

    with pytest.raises(SourceSnapshotError):
        acquire_source_snapshot(PRIVATE_PATH, stat_function=unsupported)
    with pytest.raises(SourceSnapshotError):
        acquire_source_snapshot(
            PRIVATE_PATH,
            stat_function=lambda *args, **kwargs: (_ for _ in ()).throw(NotImplementedError()),
        )


@pytest.mark.parametrize(
    "changed",
    [snapshot(device=9), snapshot(inode=9), snapshot(size=9), snapshot(mtime_ns=9)],
)
def test_exact_snapshot_verification_rejects_each_changed_field(changed) -> None:
    assert not verify_source_snapshot(
        PRIVATE_PATH, snapshot(), snapshot_function=lambda path: changed
    )


def test_fpcalc_uses_exact_argv_and_timeout_without_discovery() -> None:
    calls = []

    def runner(argv, timeout):
        calls.append((argv, timeout))
        return _ProcessResult(
            json.dumps({"duration": 120.5, "fingerprint": PRIVATE_FINGERPRINT}).encode(),
            b"ignored stderr",
        )

    settings = replace(default_acoustid_settings(), fpcalc="configured-fpcalc", timeout_seconds=17)
    backend = FpcalcFingerprintBackend.from_settings(settings, runner=runner)
    assert calls == []

    result = backend.fingerprint(PRIVATE_PATH)

    assert calls == [
        (("configured-fpcalc", "-json", "-length", "120", "--", PRIVATE_PATH), 17.0)
    ]
    assert result.duration_seconds == 120.5
    assert PRIVATE_FINGERPRINT not in repr(result)
    assert PRIVATE_PATH.decode() not in repr(backend)
    assert "configured-fpcalc" not in repr(backend)


@pytest.mark.parametrize("timeout", [1, 60])
def test_fpcalc_backend_accepts_and_normalizes_timeout_boundaries(timeout: int) -> None:
    backend = FpcalcFingerprintBackend("private-executable", timeout, lambda argv, value: None)

    assert backend.timeout_seconds == float(timeout)


@pytest.mark.parametrize(
    "timeout",
    [True, float("nan"), float("inf"), -float("inf"), 0, -1, 0.999, 60.001, "1", None],
)
def test_fpcalc_backend_rejects_unsafe_timeouts_without_disclosure(timeout: object) -> None:
    executable = "private-executable"

    with pytest.raises(ValueError) as captured:
        FpcalcFingerprintBackend(executable, timeout)  # type: ignore[arg-type]

    assert str(captured.value) == "fpcalc backend configuration is invalid"
    assert executable not in str(captured.value)
    assert PRIVATE_PATH.decode() not in str(captured.value)


@pytest.mark.parametrize("executable", ["", " ", "\t\n"])
def test_fpcalc_backend_rejects_empty_or_whitespace_executable(executable: str) -> None:
    with pytest.raises(ValueError) as captured:
        FpcalcFingerprintBackend(executable, 1)

    assert str(captured.value) == "fpcalc backend configuration is invalid"


def test_fpcalc_backend_preserves_a_falsey_injected_runner() -> None:
    class Runner:
        def __bool__(self) -> bool:
            return False

        def __call__(self, argv, timeout):
            return _ProcessResult(b'{"duration":1,"fingerprint":"x"}', b"")

    runner = Runner()
    backend = FpcalcFingerprintBackend.from_settings(
        default_acoustid_settings(), runner=runner
    )

    assert backend.runner is runner


@pytest.mark.parametrize(
    "payload",
    [
        b"\xff",
        b"not-json",
        b'{"duration": 1, "fingerprint": "x"} trailing',
        b"[]",
        b'{"fingerprint": "x"}',
        b'{"duration": 1}',
        b'{"duration": true, "fingerprint": "x"}',
        b'{"duration": NaN, "fingerprint": "x"}',
        b'{"duration": Infinity, "fingerprint": "x"}',
        b'{"duration": 0, "fingerprint": "x"}',
        b'{"duration": -1, "fingerprint": "x"}',
        b'{"duration": 1, "fingerprint": ""}',
        b'{"duration": 1, "fingerprint": " "}',
    ],
)
def test_fpcalc_rejects_invalid_json_outputs_without_raw_disclosure(payload: bytes) -> None:
    backend = FpcalcFingerprintBackend(
        "private-executable",
        1,
        lambda argv, timeout: _ProcessResult(payload, b"private-stderr"),
    )

    with pytest.raises(FingerprintBackendFailure) as captured:
        backend.fingerprint(PRIVATE_PATH)
    rendered = str(captured.value)
    assert PRIVATE_PATH.decode() not in rendered
    assert "private-executable" not in rendered
    assert "private-stderr" not in rendered


def test_fpcalc_rejects_oversized_fingerprint_and_ignores_unknown_keys() -> None:
    oversized = json.dumps(
        {"duration": 1, "fingerprint": "x" * (_MAX_FINGERPRINT_LENGTH + 1)}
    ).encode()
    invalid = FpcalcFingerprintBackend(
        "fpcalc", 1, lambda argv, timeout: _ProcessResult(oversized, b"")
    )
    with pytest.raises(FingerprintBackendFailure):
        invalid.fingerprint(PRIVATE_PATH)

    valid = FpcalcFingerprintBackend(
        "fpcalc",
        1,
        lambda argv, timeout: _ProcessResult(
            json.dumps(
                {"duration": 1, "fingerprint": "x", "unknown": {"private": "ignored"}}
            ).encode(),
            b"",
        ),
    )
    result = valid.fingerprint(PRIVATE_PATH)
    assert not hasattr(result, "unknown")


def test_stderr_is_never_used_as_json_fallback() -> None:
    backend = FpcalcFingerprintBackend(
        "fpcalc",
        1,
        lambda argv, timeout: _ProcessResult(
            b"",
            b'{"duration": 1, "fingerprint": "private-stderr-fingerprint"}',
        ),
    )
    with pytest.raises(FingerprintBackendFailure):
        backend.fingerprint(PRIVATE_PATH)


def test_missing_executable_maps_to_backend_unavailable() -> None:
    backend = FpcalcFingerprintBackend("noqlen-definitely-missing-executable", 1)

    with pytest.raises(FingerprintBackendUnavailable) as captured:
        backend.fingerprint(PRIVATE_PATH)
    assert "noqlen-definitely-missing-executable" not in str(captured.value)
    assert PRIVATE_PATH.decode() not in str(captured.value)


def run_python(script: str, timeout: float = 2) -> _ProcessResult:
    return run_bounded_process((sys.executable, "-c", script), timeout)


def assert_no_reader_threads() -> None:
    assert not [
        thread.name
        for thread in threading.enumerate()
        if thread.name.startswith(_READER_THREAD_NAME_PREFIX)
    ]


def pipe_stream(data: bytes = b""):
    reader, writer = os.pipe()
    try:
        if data:
            os.write(writer, data)
    finally:
        os.close(writer)
    return os.fdopen(reader, "rb", buffering=0)


def test_runner_drains_streams_concurrently_and_accepts_exact_limits() -> None:
    result = run_python(
        "import sys,threading; "
        "a=threading.Thread(target=lambda:sys.stdout.buffer.write(b'x'*1048576)); "
        "b=threading.Thread(target=lambda:sys.stderr.buffer.write(b'y'*65536)); "
        "a.start();b.start();a.join();b.join()",
        5,
    )

    assert len(result.stdout) == STDOUT_LIMIT_BYTES
    assert len(result.stderr) == STDERR_LIMIT_BYTES
    assert "x" * 100 not in repr(result)
    assert "y" * 100 not in repr(result)
    assert_no_reader_threads()


@pytest.mark.parametrize(
    "script",
    [
        "import sys;sys.stdout.buffer.write(b'x'*1048577);sys.stdout.flush()",
        "import sys;sys.stderr.buffer.write(b'x'*65537);sys.stderr.flush()",
        "import time;time.sleep(5)",
        "import sys;sys.exit(3)",
    ],
    ids=["stdout-overflow", "stderr-overflow", "timeout", "non-zero"],
)
def test_runner_overflow_timeout_and_nonzero_are_sanitized(script: str) -> None:
    with pytest.raises(_ProcessFailure) as captured:
        run_python(script, 1 if "sleep" in script else 3)
    assert str(captured.value) == "fingerprint process failed"
    assert_no_reader_threads()


@pytest.mark.parametrize(
    "timeout",
    [True, float("nan"), float("inf"), -float("inf"), 0, -1, 0.999, 60.001, "1", None],
)
def test_runner_rejects_unsafe_timeout_before_process_creation(timeout: object) -> None:
    calls = []

    with pytest.raises(_ProcessFailure) as captured:
        run_bounded_process(
            ("private-executable", PRIVATE_PATH),
            timeout,  # type: ignore[arg-type]
            popen_factory=lambda *args, **kwargs: calls.append((args, kwargs)),  # type: ignore[arg-type,return-value]
        )

    assert calls == []
    assert str(captured.value) == "fingerprint process failed"
    assert "private-executable" not in str(captured.value)
    assert PRIVATE_PATH.decode() not in str(captured.value)
    assert_no_reader_threads()


def test_runner_uses_no_shell_disconnected_stdin_and_sanitized_environment(monkeypatch) -> None:
    sensitive_value = "synthetic-private-value"
    monkeypatch.setenv("NOQLENMETA_ACOUSTID_API_KEY", sensitive_value)
    captured = {}

    class Process:
        stdout = pipe_stream(b"ok")
        stderr = pipe_stream()
        returncode = 0

        def poll(self):
            return 0

    def popen(argv, **kwargs):
        captured.update(kwargs)
        captured["argv"] = argv
        return Process()

    result = run_bounded_process(("private-executable", PRIVATE_PATH), 1, popen_factory=popen)

    assert captured["shell"] is False
    assert captured["stdin"] is subprocess.DEVNULL
    assert captured["stdout"] is subprocess.PIPE
    assert captured["stderr"] is subprocess.PIPE
    assert "NOQLENMETA_ACOUSTID_API_KEY" not in captured["env"]
    assert sensitive_value not in repr(result)
    assert_no_reader_threads()


def test_runner_kills_and_reaps_after_termination_grace() -> None:
    events = []

    class Process:
        stdout = pipe_stream()
        stderr = pipe_stream()
        returncode = None

        def poll(self):
            return self.returncode

        def terminate(self):
            events.append("terminate")

        def kill(self):
            events.append("kill")

        def wait(self, timeout=None):
            events.append("wait")
            if "kill" not in events:
                raise subprocess.TimeoutExpired("private-command", timeout)
            self.returncode = -9
            return self.returncode

    process = Process()
    with pytest.raises(_ProcessFailure):
        run_bounded_process(("private-executable",), 1, popen_factory=lambda *a, **k: process)

    assert events == ["terminate", "wait", "kill", "wait"]
    assert process.returncode == -9
    assert_no_reader_threads()


def test_runner_fails_boundedly_when_reap_after_kill_times_out(monkeypatch) -> None:
    raw_message = "private-command-after-kill"
    events = []

    class Process:
        stdout = pipe_stream()
        stderr = pipe_stream()
        returncode = None

        def poll(self):
            return self.returncode

        def terminate(self):
            events.append("terminate")

        def kill(self):
            events.append("kill")
            self.returncode = -9

        def wait(self, timeout=None):
            events.append(("wait", timeout))
            raise subprocess.TimeoutExpired(raw_message, timeout)

    process = Process()
    monkeypatch.setattr(
        "beetsplug.noqlenmeta.acoustid.backend.os.read",
        lambda descriptor, size: (_ for _ in ()).throw(ValueError("private read failure")),
    )
    started = time.monotonic()

    with pytest.raises(_ProcessFailure) as captured:
        run_bounded_process(
            ("private-executable", PRIVATE_PATH),
            1,
            popen_factory=lambda *args, **kwargs: process,
        )

    elapsed = time.monotonic() - started
    assert elapsed < 1.0
    assert events[0] == "terminate"
    assert events[1][0] == "wait"
    assert events[1][1] is not None
    assert events[2] == "kill"
    assert events[3] == events[1]
    assert str(captured.value) == "fingerprint process failed"
    assert captured.value.__cause__ is None
    assert raw_message not in str(captured.value)
    assert "private read failure" not in str(captured.value)
    assert "private-executable" not in str(captured.value)
    assert PRIVATE_PATH.decode() not in str(captured.value)
    assert_no_reader_threads()


def test_runner_fails_boundedly_when_descendant_keeps_pipes_open() -> None:
    script = (
        "import subprocess,sys;"
        "subprocess.Popen([sys.executable,'-c','import time;time.sleep(1.5)']);"
        "sys.exit(0)"
    )
    started = time.monotonic()

    with pytest.raises(_ProcessFailure):
        run_python(script, 1)

    assert time.monotonic() - started < 1.25
    assert_no_reader_threads()


def test_runner_stream_close_races_are_sanitized_and_cleanup_readers(monkeypatch) -> None:
    class RacingStream:
        def __init__(self) -> None:
            self.descriptor, self.writer = os.pipe()

        def fileno(self):
            return self.descriptor

        def close(self):
            raise ValueError("private stream state")

    class Process:
        stdout = RacingStream()
        stderr = RacingStream()
        returncode = 0

        def poll(self):
            return self.returncode

    process = Process()
    monkeypatch.setattr(
        "beetsplug.noqlenmeta.acoustid.backend.os.read",
        lambda descriptor, size: (_ for _ in ()).throw(ValueError("private stream state")),
    )
    try:
        with pytest.raises(_ProcessFailure) as captured:
            run_bounded_process(
                ("private-executable", PRIVATE_PATH),
                1,
                popen_factory=lambda *args, **kwargs: process,
            )
    finally:
        for stream in (process.stdout, process.stderr):
            os.close(stream.descriptor)
            os.close(stream.writer)

    assert str(captured.value) == "fingerprint process failed"
    assert "private stream state" not in str(captured.value)
    assert "private-executable" not in str(captured.value)
    assert PRIVATE_PATH.decode() not in str(captured.value)
    assert_no_reader_threads()


def test_runner_unsupported_pipe_setup_fails_closed_without_blocking_reader() -> None:
    read_started = threading.Event()
    release_read = threading.Event()
    events = []

    class UnsupportedBlockingStream:
        def fileno(self):
            raise OSError("private unsupported descriptor")

        def read(self, size):
            read_started.set()
            release_read.wait(5)

        def close(self):
            events.append("close")

    class Process:
        stdout = UnsupportedBlockingStream()
        stderr = UnsupportedBlockingStream()
        returncode = None

        def poll(self):
            return self.returncode

        def terminate(self):
            events.append("terminate")

        def wait(self, timeout=None):
            events.append("wait")
            self.returncode = -15
            return self.returncode

    process = Process()
    started = time.monotonic()
    try:
        with pytest.raises(_ProcessFailure) as captured:
            run_bounded_process(
                ("private-executable", PRIVATE_PATH),
                1,
                popen_factory=lambda *args, **kwargs: process,
            )
    finally:
        release_read.set()

    assert time.monotonic() - started < 0.25
    assert not read_started.is_set()
    assert events == ["terminate", "wait", "close", "close"]
    assert process.returncode == -15
    assert str(captured.value) == "fingerprint process failed"
    assert "private unsupported descriptor" not in str(captured.value)
    assert "private-executable" not in str(captured.value)
    assert PRIVATE_PATH.decode() not in str(captured.value)
    assert_no_reader_threads()


def test_runner_nonblocking_setup_failure_never_starts_blocking_reader(monkeypatch) -> None:
    read_started = threading.Event()
    release_read = threading.Event()
    events = []

    class BlockingStream:
        def __init__(self) -> None:
            self.descriptor, self.writer = os.pipe()

        def fileno(self):
            return self.descriptor

        def read(self, size):
            read_started.set()
            release_read.wait(5)

        def close(self):
            events.append("close")

    class Process:
        stdout = BlockingStream()
        stderr = BlockingStream()
        returncode = None

        def poll(self):
            return self.returncode

        def terminate(self):
            events.append("terminate")

        def wait(self, timeout=None):
            events.append("wait")
            self.returncode = -15
            return self.returncode

    process = Process()
    monkeypatch.setattr(
        "beetsplug.noqlenmeta.acoustid.backend.os.set_blocking",
        lambda descriptor, blocking: (_ for _ in ()).throw(
            OSError("private nonblocking failure")
        ),
    )
    started = time.monotonic()
    try:
        with pytest.raises(_ProcessFailure) as captured:
            run_bounded_process(
                ("private-executable", PRIVATE_PATH),
                1,
                popen_factory=lambda *args, **kwargs: process,
            )
    finally:
        release_read.set()
        for stream in (process.stdout, process.stderr):
            os.close(stream.descriptor)
            os.close(stream.writer)

    assert time.monotonic() - started < 0.25
    assert not read_started.is_set()
    assert events == ["terminate", "wait", "close", "close"]
    assert process.returncode == -15
    assert str(captured.value) == "fingerprint process failed"
    assert "private nonblocking failure" not in str(captured.value)
    assert "private-executable" not in str(captured.value)
    assert PRIVATE_PATH.decode() not in str(captured.value)
    assert_no_reader_threads()


def test_runner_uses_only_bounded_reader_joins(monkeypatch) -> None:
    original_join = threading.Thread.join
    observed_timeouts = []

    def checked_join(thread, timeout=None):
        if thread.name.startswith(_READER_THREAD_NAME_PREFIX):
            observed_timeouts.append(timeout)
            assert timeout is not None
        return original_join(thread, timeout)

    monkeypatch.setattr(threading.Thread, "join", checked_join)

    assert run_python("pass").stdout == b""
    assert observed_timeouts
    assert_no_reader_threads()


def test_runner_sanitizes_popen_value_error() -> None:
    raw_message = "private invalid argv path"

    with pytest.raises(_ProcessFailure) as captured:
        run_bounded_process(
            ("private-executable", PRIVATE_PATH),
            1,
            popen_factory=lambda *args, **kwargs: (_ for _ in ()).throw(
                ValueError(raw_message)
            ),
        )

    assert str(captured.value) == "fingerprint process failed"
    assert captured.value.__cause__ is None
    assert raw_message not in str(captured.value)
    assert "private-executable" not in str(captured.value)
    assert PRIVATE_PATH.decode() not in str(captured.value)
    assert_no_reader_threads()
