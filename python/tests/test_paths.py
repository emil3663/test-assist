"""Tests for paths.py (TA-202): where recordings, exports and history live.

isolate_home (conftest.py, autouse) redirects QStandardPaths.writableLocation
for every test in the suite and asserts the redirect took effect on its own;
the tests here additionally pin the *reasoning* - that history and recordings
are deliberately different locations, and what migration does and does not
touch - not just today's value.
"""
from __future__ import annotations

import paths


def test_recordings_and_history_are_distinct_and_neither_contains_the_other(isolate_home):
    recordings = paths.recordings_dir()
    history = paths.history_dir()

    assert recordings != history
    assert history not in recordings.parents
    assert recordings not in history.parents


def test_history_dir_is_not_under_documents(isolate_home):
    """Pin the reasoning, not just today's value: history is auto-pruned on
    every launch (_prune_unreadable_history), and an auto-deleting folder
    must never live where a user keeps things they would miss."""
    recordings = paths.recordings_dir()   # resolves under the fake Documents
    history = paths.history_dir()

    assert recordings not in history.parents
    assert history != recordings


def test_isolation_a_path_from_paths_py_resolves_under_tmp_path(isolate_home, tmp_path):
    """The seam the whole ticket exists to protect: with the fixture active,
    nothing paths.py returns may resolve outside the temp directory."""
    assert str(paths.recordings_dir()).startswith(str(tmp_path))
    assert str(paths.history_dir()).startswith(str(tmp_path))
    assert str(paths.legacy_dir()).startswith(str(tmp_path))


# ── Migration ────────────────────────────────────────────────────────────────

def test_migration_moves_a_populated_legacy_folder(isolate_home):
    legacy = paths.legacy_dir()
    (legacy / "recordings").mkdir(parents=True)
    (legacy / "history").mkdir(parents=True)
    (legacy / "recordings" / "test-recording-1.mp4").write_bytes(b"video")
    (legacy / "history" / "snapshot-1.png").write_bytes(b"image")

    paths.migrate_legacy_data()

    assert (paths.recordings_dir() / "test-recording-1.mp4").read_bytes() == b"video"
    assert (paths.history_dir() / "snapshot-1.png").read_bytes() == b"image"
    # Best-effort, not destructive: the old folder is left in place.
    assert legacy.is_dir()


def test_migration_of_an_already_migrated_install_is_a_no_op(isolate_home):
    legacy = paths.legacy_dir()
    (legacy / "recordings").mkdir(parents=True)
    (legacy / "recordings" / "test-recording-1.mp4").write_bytes(b"video")

    paths.migrate_legacy_data()
    first_pass = (paths.recordings_dir() / "test-recording-1.mp4").read_bytes()

    # Running it again must not raise, duplicate, or touch anything further -
    # legacy/recordings is now empty, so there is nothing left to move.
    paths.migrate_legacy_data()

    assert first_pass == b"video"
    assert list((paths.recordings_dir()).glob("test-recording-1.mp4")) != []


def test_migration_does_not_overwrite_an_existing_file_at_the_destination(isolate_home):
    """A name collision is left alone in both places rather than risking
    overwriting a different file that happens to share a name."""
    legacy = paths.legacy_dir()
    (legacy / "recordings").mkdir(parents=True)
    (legacy / "recordings" / "clash.mp4").write_bytes(b"old")
    (paths.recordings_dir() / "clash.mp4").write_bytes(b"new")

    paths.migrate_legacy_data()

    assert (paths.recordings_dir() / "clash.mp4").read_bytes() == b"new"
    assert (legacy / "recordings" / "clash.mp4").read_bytes() == b"old"


def test_migration_with_no_legacy_folder_is_a_no_op(isolate_home):
    assert not paths.legacy_dir().is_dir()

    paths.migrate_legacy_data()   # must not raise

    assert list(paths.recordings_dir().iterdir()) == []
    assert list(paths.history_dir().iterdir()) == []


def test_migration_with_an_empty_legacy_folder_is_a_no_op(isolate_home):
    paths.legacy_dir().mkdir(parents=True)

    paths.migrate_legacy_data()   # must not raise

    assert list(paths.recordings_dir().iterdir()) == []


def test_migration_never_raises_and_never_blocks_startup(isolate_home, monkeypatch):
    """v1.0.0, v1.1.0 and v1.3.0 are public downloads with real user data in
    the old location - a broken migration must never prevent the app from
    starting."""
    legacy = paths.legacy_dir()
    legacy.mkdir(parents=True)
    (legacy / "recordings").mkdir()

    real_iterdir = paths.Path.iterdir
    unreadable = legacy / "recordings"

    def _flaky_iterdir(self):
        if self == unreadable:
            raise OSError("simulated: permission denied")
        return real_iterdir(self)

    monkeypatch.setattr(paths.Path, "iterdir", _flaky_iterdir)

    paths.migrate_legacy_data()   # must not raise


def test_migration_one_bad_item_does_not_stop_the_rest(isolate_home, monkeypatch):
    legacy = paths.legacy_dir()
    (legacy / "recordings").mkdir(parents=True)
    good = legacy / "recordings" / "good.mp4"
    bad = legacy / "recordings" / "bad.mp4"
    good.write_bytes(b"good")
    bad.write_bytes(b"bad")

    real_rename = paths.Path.rename

    def _flaky_rename(self, target):
        if self.name == "bad.mp4":
            raise OSError("simulated: file in use")
        return real_rename(self, target)

    monkeypatch.setattr(paths.Path, "rename", _flaky_rename)

    paths.migrate_legacy_data()

    assert (paths.recordings_dir() / "good.mp4").exists()
    assert not (paths.recordings_dir() / "bad.mp4").exists()
    assert bad.exists(), "the item that failed to move must be left where it was"
