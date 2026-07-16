import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from spirecomm.communication import study_handshake
from spirecomm.communication.coordinator import Coordinator
from spirecomm.communication.study_handshake import (
    ATTEMPT_SCHEMA_VERSION,
    HANDSHAKE_ATTEMPT_ENV,
    HANDSHAKE_SCHEMA_VERSION,
    READY_SCHEMA_VERSION,
    RELEASE_SCHEMA_VERSION,
    HandshakePaths,
    StudyHandshakeError,
    build_attempt_record,
    build_ready_record,
    build_release_record,
    derive_slot_token,
    load_attempt_record,
    load_release_record,
    load_ready_record,
    perform_child_handshake_if_configured,
    publish_record_once,
    validate_ready_record,
    validate_release_record,
)
from spirecomm.spire.screen import ScreenType


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _paths(tmp_path):
    return HandshakePaths(
        attempt=(tmp_path / "slot-01-communication-attempt.json").resolve(),
        ready=(tmp_path / "slot-01-communication-ready.json").resolve(),
        release=(tmp_path / "slot-01-communication-release.json").resolve(),
    )


def _attempt(tmp_path, **overrides):
    paths = _paths(tmp_path)
    config_path = (tmp_path / "slot-01-config.json").resolve()
    config_path.write_text("{}\n", encoding="utf-8", newline="")
    values = {
        "study_id": "study-1",
        "registration_hash": "1" * 64,
        "run_lock_hash": "2" * 64,
        "slot_number": 1,
        "session_id": "study-1-s01",
        "config_path": config_path,
        "config_sha256": _sha256(config_path),
        "marker_start_count": 10,
        "paths": paths,
        "readiness_timeout_seconds": 30,
        "release_timeout_seconds": 10,
        "created_unix_ns": 100,
    }
    values.update(overrides)
    return build_attempt_record(**values)


def test_slot_token_is_deterministic_and_bound_to_every_identity():
    values = {
        "registration_hash": "1" * 64,
        "run_lock_hash": "2" * 64,
        "slot_number": 1,
        "session_id": "study-1-s01",
        "config_sha256": "3" * 64,
    }

    first = derive_slot_token(**values)
    second = derive_slot_token(**values)

    assert first == second
    assert len(first) == 64
    for field, replacement in (
        ("registration_hash", "4" * 64),
        ("run_lock_hash", "5" * 64),
        ("slot_number", 2),
        ("session_id", "study-1-s02"),
        ("config_sha256", "6" * 64),
    ):
        changed = dict(values)
        changed[field] = replacement
        assert derive_slot_token(**changed) != first


def test_attempt_record_has_exact_fixed_contract(tmp_path):
    attempt = _attempt(tmp_path)

    assert set(attempt) == {
        "attempt_hash",
        "attempt_path",
        "config_path",
        "config_sha256",
        "created_unix_ns",
        "marker_start_count",
        "protocol_version",
        "readiness_timeout_seconds",
        "ready_path",
        "registration_hash",
        "release_path",
        "release_timeout_seconds",
        "run_lock_hash",
        "schema_version",
        "session_id",
        "slot_number",
        "slot_token",
        "study_id",
    }
    assert attempt["schema_version"] == ATTEMPT_SCHEMA_VERSION
    assert attempt["protocol_version"] == HANDSHAKE_SCHEMA_VERSION
    assert attempt["readiness_timeout_seconds"] == 30
    assert attempt["release_timeout_seconds"] == 10
    assert attempt["slot_token"] == derive_slot_token(
        registration_hash=attempt["registration_hash"],
        run_lock_hash=attempt["run_lock_hash"],
        slot_number=attempt["slot_number"],
        session_id=attempt["session_id"],
        config_sha256=attempt["config_sha256"],
    )


@pytest.mark.parametrize(
    ("override", "match"),
    (
        ({"slot_number": True}, "slot_number"),
        ({"created_unix_ns": 1.0}, "created_unix_ns"),
        ({"marker_start_count": "10"}, "marker_start_count"),
        ({"readiness_timeout_seconds": 29}, "readiness timeout"),
        ({"release_timeout_seconds": 11}, "release timeout"),
        (
            {
                "paths": HandshakePaths(
                    attempt=Path("attempt.json"),
                    ready=Path("ready.json"),
                    release=Path("release.json"),
                )
            },
            "resolved absolute",
        ),
    ),
)
def test_attempt_record_rejects_noncanonical_values(tmp_path, override, match):
    with pytest.raises(StudyHandshakeError, match=match):
        _attempt(tmp_path, **override)


def test_record_publication_is_canonical_and_exclusive(tmp_path):
    paths = _paths(tmp_path)
    attempt = _attempt(tmp_path)

    publish_record_once(paths.attempt, attempt)

    expected = (
        json.dumps(
            attempt,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    assert paths.attempt.read_bytes() == expected
    assert load_attempt_record(paths.attempt) == attempt
    before = paths.attempt.read_bytes()
    with pytest.raises(StudyHandshakeError, match="already exists"):
        publish_record_once(paths.attempt, attempt)
    assert paths.attempt.read_bytes() == before


def test_record_publication_exposes_final_path_only_after_complete_bytes(
    tmp_path,
    monkeypatch,
):
    paths = _paths(tmp_path)
    attempt = _attempt(tmp_path)
    expected = (
        json.dumps(
            attempt,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    observed = []
    real_link = study_handshake.os.link

    def inspect_complete_source_before_link(source, destination):
        assert Path(destination) == paths.attempt
        assert not paths.attempt.exists()
        assert Path(source).read_bytes() == expected
        observed.append(Path(source))
        return real_link(source, destination)

    monkeypatch.setattr(
        study_handshake.os,
        "link",
        inspect_complete_source_before_link,
    )

    publish_record_once(paths.attempt, attempt)

    assert len(observed) == 1
    assert paths.attempt.read_bytes() == expected


def test_attempt_loader_rejects_self_hash_tamper(tmp_path):
    paths = _paths(tmp_path)
    attempt = _attempt(tmp_path)
    publish_record_once(paths.attempt, attempt)
    tampered = dict(attempt)
    tampered["marker_start_count"] += 1
    paths.attempt.write_text(
        json.dumps(tampered, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="",
    )

    with pytest.raises(StudyHandshakeError, match="attempt hash mismatch"):
        load_attempt_record(paths.attempt)


def test_ready_and_release_records_require_exact_pid_and_binding(tmp_path):
    attempt = _attempt(tmp_path)
    ready = build_ready_record(attempt, child_pid=4321, created_unix_ns=200)

    assert ready["schema_version"] == READY_SCHEMA_VERSION
    assert validate_ready_record(ready, attempt=attempt, child_pid=4321) == ready
    with pytest.raises(StudyHandshakeError, match="ready binding mismatch"):
        validate_ready_record(ready, attempt=attempt, child_pid=4322)

    release = build_release_record(attempt, ready, created_unix_ns=300)
    assert release["schema_version"] == RELEASE_SCHEMA_VERSION
    assert validate_release_record(release, attempt=attempt, ready=ready) == release
    changed_ready = dict(ready)
    changed_ready["ready_hash"] = "f" * 64
    with pytest.raises(StudyHandshakeError, match="release binding mismatch"):
        validate_release_record(release, attempt=attempt, ready=changed_ready)


def test_absent_environment_is_inert():
    class UntouchedCoordinator:
        def __getattribute__(self, name):
            if name.startswith("__"):
                return object.__getattribute__(self, name)
            raise AssertionError(f"coordinator was touched: {name}")

    assert (
        perform_child_handshake_if_configured(
            UntouchedCoordinator(),
            environ={},
        )
        is False
    )


def test_child_publishes_ready_after_one_callback_free_state_then_waits_for_release(
    tmp_path,
):
    paths = _paths(tmp_path)
    attempt = _attempt(tmp_path)
    publish_record_once(paths.attempt, attempt)
    events = []

    class FakeCoordinator:
        last_error = None
        last_game_state = None

        def start_input_thread(self):
            events.append("input-started")

        def receive_game_state_update(self, *, block, perform_callbacks):
            assert block is False
            assert perform_callbacks is False
            assert not paths.ready.exists()
            self.last_game_state = object()
            events.append("state-received")
            return True

    release_published = False

    def sleep(_seconds):
        nonlocal release_published
        assert paths.ready.exists()
        events.append("ready-observed")
        if not release_published:
            ready = load_ready_record(paths.ready)
            release = build_release_record(attempt, ready, created_unix_ns=300)
            publish_record_once(paths.release, release)
            release_published = True
            events.append("release-published")

    coordinator = FakeCoordinator()
    result = perform_child_handshake_if_configured(
        coordinator,
        environ={HANDSHAKE_ATTEMPT_ENV: str(paths.attempt)},
        monotonic=lambda: 0.0,
        sleep=sleep,
        child_pid=4321,
        created_unix_ns=lambda: 200,
    )

    assert result is True
    assert coordinator.last_game_state is not None
    assert events == [
        "input-started",
        "state-received",
        "ready-observed",
        "release-published",
    ]
    ready = load_ready_record(paths.ready)
    assert ready["child_pid"] == 4321
    assert load_release_record(paths.release) == build_release_record(
        attempt,
        ready,
        created_unix_ns=300,
    )


def test_released_retained_in_game_state_is_processed_exactly_once():
    coordinator = Coordinator(start_input_thread=False)
    retained_state = SimpleNamespace(screen_type="EVENT")
    terminal_state = SimpleNamespace(
        screen=SimpleNamespace(victory=True),
        screen_type=ScreenType.GAME_OVER,
    )
    callback_states = []
    receive_calls = []
    coordinator.game_is_ready = True
    coordinator.in_game = True
    coordinator.last_game_state = retained_state
    coordinator.register_state_change_callback(
        lambda state: callback_states.append(state)
    )
    coordinator.check_communication_threads = lambda: True
    coordinator.execute_next_action_if_ready = lambda: None

    def receive_after_release(*, block=False, perform_callbacks=True):
        receive_calls.append((block, perform_callbacks))
        coordinator.in_game = False
        coordinator.game_over_state = terminal_state
        return True

    coordinator.receive_game_state_update = receive_after_release

    assert coordinator.play_one_game(object()) is True
    assert callback_states == [retained_state]
    assert receive_calls == [(False, True)]


class _Clock:
    def __init__(self):
        self.value = 0.0

    def monotonic(self):
        return self.value

    def sleep_past_deadline(self, _seconds):
        self.value = 31.0


def test_child_readiness_timeout_fails_without_ready(tmp_path):
    paths = _paths(tmp_path)
    attempt = _attempt(tmp_path)
    publish_record_once(paths.attempt, attempt)
    clock = _Clock()

    class NoStateCoordinator:
        last_error = None
        last_game_state = None

        def start_input_thread(self):
            pass

        def receive_game_state_update(self, *, block, perform_callbacks):
            return False

    with pytest.raises(StudyHandshakeError, match="readiness deadline"):
        perform_child_handshake_if_configured(
            NoStateCoordinator(),
            environ={HANDSHAKE_ATTEMPT_ENV: str(paths.attempt)},
            monotonic=clock.monotonic,
            sleep=clock.sleep_past_deadline,
            child_pid=4321,
            created_unix_ns=lambda: 200,
        )
    assert not paths.ready.exists()
    assert not paths.release.exists()


def test_child_release_timeout_fails_after_ready(tmp_path):
    paths = _paths(tmp_path)
    attempt = _attempt(tmp_path)
    publish_record_once(paths.attempt, attempt)
    clock = _Clock()

    class ReadyCoordinator:
        last_error = None
        last_game_state = object()

        def start_input_thread(self):
            pass

        def receive_game_state_update(self, *, block, perform_callbacks):
            return True

    with pytest.raises(StudyHandshakeError, match="release deadline"):
        perform_child_handshake_if_configured(
            ReadyCoordinator(),
            environ={HANDSHAKE_ATTEMPT_ENV: str(paths.attempt)},
            monotonic=clock.monotonic,
            sleep=clock.sleep_past_deadline,
            child_pid=4321,
            created_unix_ns=lambda: 200,
        )
    assert paths.ready.exists()
    assert not paths.release.exists()


def test_child_rejects_communication_error_without_ready(tmp_path):
    paths = _paths(tmp_path)
    attempt = _attempt(tmp_path)
    publish_record_once(paths.attempt, attempt)

    class ErrorCoordinator:
        last_error = "CommunicationMod rejected state"
        last_game_state = object()

        def start_input_thread(self):
            pass

        def receive_game_state_update(self, *, block, perform_callbacks):
            return True

    with pytest.raises(StudyHandshakeError, match="CommunicationMod error"):
        perform_child_handshake_if_configured(
            ErrorCoordinator(),
            environ={HANDSHAKE_ATTEMPT_ENV: str(paths.attempt)},
            monotonic=lambda: 0.0,
            sleep=lambda _seconds: None,
            child_pid=4321,
            created_unix_ns=lambda: 200,
        )
    assert not paths.ready.exists()


def test_child_rejects_stale_ready_or_release_before_receiving_state(tmp_path):
    paths = _paths(tmp_path)
    attempt = _attempt(tmp_path)
    publish_record_once(paths.attempt, attempt)
    paths.ready.write_text("{}\n", encoding="utf-8", newline="")

    with pytest.raises(StudyHandshakeError, match="stale handshake artifact"):
        perform_child_handshake_if_configured(
            object(),
            environ={HANDSHAKE_ATTEMPT_ENV: str(paths.attempt)},
        )


def test_child_rejects_config_drift_before_receiving_state(tmp_path):
    paths = _paths(tmp_path)
    attempt = _attempt(tmp_path)
    publish_record_once(paths.attempt, attempt)
    Path(attempt["config_path"]).write_text(
        '{"tampered":true}\n',
        encoding="utf-8",
        newline="",
    )

    with pytest.raises(StudyHandshakeError, match="config hash mismatch"):
        perform_child_handshake_if_configured(
            object(),
            environ={HANDSHAKE_ATTEMPT_ENV: str(paths.attempt)},
        )
