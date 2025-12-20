"""Quick test for initial sync preference feature."""

import tempfile
from pathlib import Path

from benchmarks.test_utils import LocalStorageClient, create_entries_manager_factory
from syncengine import InitialSyncPreference, SyncEngine, SyncMode, SyncPair
from syncengine.protocols import DefaultOutputHandler


def test_initial_sync_merge():
    """Test MERGE preference: merges both sides without deletions."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        source = base / "source"
        dest_storage = base / "dest"
        source.mkdir()
        dest_storage.mkdir()

        # Setup: source has file1, dest has file2
        (source / "file1.txt").write_text("source file")
        (dest_storage / "file2.txt").write_text("dest file")

        # Create engine
        client = LocalStorageClient(dest_storage)
        factory = create_entries_manager_factory(client)
        output = DefaultOutputHandler(quiet=True)
        engine = SyncEngine(client, factory, output=output)

        pair = SyncPair(source=source, destination="", sync_mode=SyncMode.TWO_WAY)

        # Sync with MERGE preference
        stats = engine.sync_pair(
            pair,
            use_streaming=False,  # Use traditional mode for simplicity
            initial_sync_preference=InitialSyncPreference.MERGE,
        )

        print(f"Stats: {stats}")

        # Expected: file1 uploaded, file2 downloaded, no deletions
        assert stats["uploads"] == 1, f"Expected 1 upload, got {stats['uploads']}"
        assert stats["downloads"] == 1, f"Expected 1 download, got {stats['downloads']}"
        assert stats["deletes_local"] == 0, "Expected no local deletions"
        assert stats["deletes_remote"] == 0, "Expected no remote deletions"

        # Verify both files exist in both locations
        assert (source / "file1.txt").exists()
        assert (source / "file2.txt").exists()
        assert (dest_storage / "file1.txt").exists()
        assert (dest_storage / "file2.txt").exists()

        print("✓ MERGE test passed")


def test_initial_sync_source_wins():
    """Test SOURCE_WINS preference: source is authoritative."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        source = base / "source"
        dest_storage = base / "dest"
        source.mkdir()
        dest_storage.mkdir()

        # Setup: source has file1, dest has file2
        (source / "file1.txt").write_text("source file")
        (dest_storage / "file2.txt").write_text("dest file")

        # Create engine
        client = LocalStorageClient(dest_storage)
        factory = create_entries_manager_factory(client)
        output = DefaultOutputHandler(quiet=True)
        engine = SyncEngine(client, factory, output=output)

        pair = SyncPair(source=source, destination="", sync_mode=SyncMode.TWO_WAY)

        # Sync with SOURCE_WINS preference
        stats = engine.sync_pair(
            pair,
            use_streaming=False,
            initial_sync_preference=InitialSyncPreference.SOURCE_WINS,
        )

        print(f"Stats: {stats}")

        # Expected: file1 uploaded, file2 deleted from dest
        assert stats["uploads"] == 1, f"Expected 1 upload, got {stats['uploads']}"
        assert stats["deletes_remote"] == 1, (
            f"Expected 1 remote delete, got {stats['deletes_remote']}"
        )

        # Verify: source has file1, dest has file1 (file2 deleted)
        assert (source / "file1.txt").exists()
        assert not (source / "file2.txt").exists()
        assert (dest_storage / "file1.txt").exists()
        assert not (dest_storage / "file2.txt").exists()

        print("✓ SOURCE_WINS test passed")


def test_initial_sync_destination_wins():
    """Test DESTINATION_WINS preference: destination is authoritative."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        source = base / "source"
        dest_storage = base / "dest"
        source.mkdir()
        dest_storage.mkdir()

        # Setup: source has file1, dest has file2
        (source / "file1.txt").write_text("source file")
        (dest_storage / "file2.txt").write_text("dest file")

        # Create engine
        client = LocalStorageClient(dest_storage)
        factory = create_entries_manager_factory(client)
        output = DefaultOutputHandler(quiet=True)
        engine = SyncEngine(client, factory, output=output)

        pair = SyncPair(source=source, destination="", sync_mode=SyncMode.TWO_WAY)

        # Sync with DESTINATION_WINS preference
        stats = engine.sync_pair(
            pair,
            use_streaming=False,
            initial_sync_preference=InitialSyncPreference.DESTINATION_WINS,
        )

        print(f"Stats: {stats}")

        # Expected: file2 downloaded, file1 deleted from source
        assert stats["downloads"] == 1, f"Expected 1 download, got {stats['downloads']}"
        assert stats["deletes_local"] == 1, (
            f"Expected 1 local delete, got {stats['deletes_local']}"
        )

        # Verify: both locations have only file2
        assert not (source / "file1.txt").exists()
        assert (source / "file2.txt").exists()
        assert not (dest_storage / "file1.txt").exists()
        assert (dest_storage / "file2.txt").exists()

        print("✓ DESTINATION_WINS test passed")


def test_initial_sync_risk_warning_many_remote():
    """Test that warnings are shown when destination has many more files."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        source = base / "source"
        dest_storage = base / "dest"
        source.mkdir()
        dest_storage.mkdir()

        # Setup: source has 2 files, dest has 20 files (10x more)
        for i in range(2):
            (source / f"source_{i}.txt").write_text(f"source file {i}")
        for i in range(20):
            (dest_storage / f"dest_{i}.txt").write_text(f"dest file {i}")

        # Create engine with custom output to capture warnings
        client = LocalStorageClient(dest_storage)
        factory = create_entries_manager_factory(client)

        # Capture output
        captured_output = []

        class CapturingOutput(DefaultOutputHandler):
            def warning(self, message: str):
                captured_output.append(("warning", message))

            def info(self, message: str):
                captured_output.append(("info", message))

        output = CapturingOutput(quiet=False)
        engine = SyncEngine(client, factory, output=output)

        pair = SyncPair(source=source, destination="", sync_mode=SyncMode.TWO_WAY)

        # Sync WITHOUT setting initial_sync_preference (should trigger warning)
        _ = engine.sync_pair(
            pair,
            use_streaming=False,
            dry_run=True,  # Use dry-run to avoid actual changes
            initial_sync_preference=None,  # Explicitly None to test warning
        )

        # Check that warning was emitted
        warning_messages = [msg for typ, msg in captured_output if typ == "warning"]
        assert any(
            "WARNING" in msg and "Destination has" in msg for msg in warning_messages
        ), (
            f"Expected warning about destination having more files. "
            f"Got: {warning_messages}"
        )

        print("✓ Risk warning test (many remote) passed")


def test_initial_sync_risk_warning_many_local():
    """Test that warnings are shown when source has many more files."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        source = base / "source"
        dest_storage = base / "dest"
        source.mkdir()
        dest_storage.mkdir()

        # Setup: source has 20 files, dest has 2 files
        for i in range(20):
            (source / f"source_{i}.txt").write_text(f"source file {i}")
        for i in range(2):
            (dest_storage / f"dest_{i}.txt").write_text(f"dest file {i}")

        # Create engine with custom output to capture warnings
        client = LocalStorageClient(dest_storage)
        factory = create_entries_manager_factory(client)

        # Capture output
        captured_output = []

        class CapturingOutput(DefaultOutputHandler):
            def warning(self, message: str):
                captured_output.append(("warning", message))

            def info(self, message: str):
                captured_output.append(("info", message))

        output = CapturingOutput(quiet=False)
        engine = SyncEngine(client, factory, output=output)

        pair = SyncPair(source=source, destination="", sync_mode=SyncMode.TWO_WAY)

        # Sync WITHOUT setting initial_sync_preference (should trigger warning)
        _ = engine.sync_pair(
            pair,
            use_streaming=False,
            dry_run=True,
            initial_sync_preference=None,
        )

        # Check that warning was emitted
        warning_messages = [msg for typ, msg in captured_output if typ == "warning"]
        assert any(
            "WARNING" in msg and "Source has" in msg for msg in warning_messages
        ), f"Expected warning about source having more files. Got: {warning_messages}"

        print("✓ Risk warning test (many local) passed")


def test_no_warning_when_preference_set():
    """Test that warnings are NOT shown when user explicitly sets preference."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        source = base / "source"
        dest_storage = base / "dest"
        source.mkdir()
        dest_storage.mkdir()

        # Setup: source has 2 files, dest has 20 files
        for i in range(2):
            (source / f"source_{i}.txt").write_text(f"source file {i}")
        for i in range(20):
            (dest_storage / f"dest_{i}.txt").write_text(f"dest file {i}")

        # Create engine with custom output to capture warnings
        client = LocalStorageClient(dest_storage)
        factory = create_entries_manager_factory(client)

        captured_output = []

        class CapturingOutput(DefaultOutputHandler):
            def warning(self, message: str):
                captured_output.append(("warning", message))

            def info(self, message: str):
                captured_output.append(("info", message))

        output = CapturingOutput(quiet=False)
        engine = SyncEngine(client, factory, output=output)

        pair = SyncPair(source=source, destination="", sync_mode=SyncMode.TWO_WAY)

        # Sync WITH explicit preference (should NOT trigger warning)
        _ = engine.sync_pair(
            pair,
            use_streaming=False,
            dry_run=True,
            initial_sync_preference=InitialSyncPreference.MERGE,  # Explicit
        )

        # Check that no warning was emitted (user made explicit choice)
        warning_messages = [msg for typ, msg in captured_output if typ == "warning"]
        risky_warnings = [
            msg
            for msg in warning_messages
            if "WARNING" in msg and ("Destination has" in msg or "Source has" in msg)
        ]
        assert len(risky_warnings) == 0, (
            f"Expected NO warning when preference is explicit. Got: {risky_warnings}"
        )

        print("✓ No warning test (explicit preference) passed")


def test_destination_wins_downloads_remote_only_files_traditional():
    """Test DESTINATION_WINS downloads files only on remote (traditional).

    Bug report scenario:
    - Source (local): test3.txt only
    - Destination (remote): test1.txt, test2.txt, test3.txt
    - Expected: Download test1.txt and test2.txt to source
    - Bug: Files were marked as synced WITHOUT being downloaded
    """
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        source = base / "source"
        dest_storage = base / "dest"
        source.mkdir()
        dest_storage.mkdir()

        # Setup: source has only test3.txt
        (source / "test3.txt").write_text("local content")

        # Destination has all 3 files
        (dest_storage / "test1.txt").write_text("remote content 1")
        (dest_storage / "test2.txt").write_text("remote content 2")
        (dest_storage / "test3.txt").write_text(
            "remote content 3 - different from local"
        )

        # Create engine
        client = LocalStorageClient(dest_storage)
        factory = create_entries_manager_factory(client)
        output = DefaultOutputHandler(quiet=True)
        engine = SyncEngine(client, factory, output=output)

        pair = SyncPair(source=source, destination="", sync_mode=SyncMode.TWO_WAY)

        # Sync with DESTINATION_WINS preference
        stats = engine.sync_pair(
            pair,
            use_streaming=False,  # Traditional mode
            initial_sync_preference=InitialSyncPreference.DESTINATION_WINS,
        )

        print(f"Stats: {stats}")

        # Expected: Download 2 files (test1.txt, test2.txt)
        # Note: test3.txt exists on both but we'll check it separately
        assert stats["downloads"] >= 2, (
            f"Expected at least 2 downloads, got {stats['downloads']}"
        )

        # Verify files were actually downloaded to source
        assert (source / "test1.txt").exists(), (
            "test1.txt should be downloaded to source"
        )
        assert (source / "test2.txt").exists(), (
            "test2.txt should be downloaded to source"
        )
        assert (source / "test3.txt").exists(), "test3.txt should exist on source"

        # Verify no deletions occurred
        # (DESTINATION_WINS keeps dest files, downloads them)
        assert stats["deletes_remote"] == 0, (
            "DESTINATION_WINS should not delete remote files"
        )

        print(
            "✓ DESTINATION_WINS downloads remote-only files "
            "(traditional mode) test passed"
        )

        print(
            "✓ DESTINATION_WINS downloads remote-only files (traditional mode) test passed"
        )


def test_destination_wins_downloads_remote_only_files_streaming():
    """Test DESTINATION_WINS downloads files only on remote (streaming).

    Same as traditional mode test but with streaming enabled.
    Bug report mentions this might behave differently.
    """
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        source = base / "source"
        dest_storage = base / "dest"
        source.mkdir()
        dest_storage.mkdir()

        # Setup: source has only test3.txt
        (source / "test3.txt").write_text("local content")

        # Destination has all 3 files
        (dest_storage / "test1.txt").write_text("remote content 1")
        (dest_storage / "test2.txt").write_text("remote content 2")
        (dest_storage / "test3.txt").write_text(
            "remote content 3 - different from local"
        )

        # Create engine
        client = LocalStorageClient(dest_storage)
        factory = create_entries_manager_factory(client)
        output = DefaultOutputHandler(quiet=True)
        engine = SyncEngine(client, factory, output=output)

        pair = SyncPair(source=source, destination="", sync_mode=SyncMode.TWO_WAY)

        # Sync with DESTINATION_WINS preference in STREAMING mode
        stats = engine.sync_pair(
            pair,
            use_streaming=True,  # Streaming mode
            initial_sync_preference=InitialSyncPreference.DESTINATION_WINS,
        )

        print(f"Stats (streaming): {stats}")

        # Expected: Download 2 files (test1.txt, test2.txt)
        assert stats["downloads"] >= 2, (
            f"Expected at least 2 downloads, got {stats['downloads']}"
        )

        # Verify files were actually downloaded to source
        assert (source / "test1.txt").exists(), (
            "test1.txt should be downloaded to source"
        )
        assert (source / "test2.txt").exists(), (
            "test2.txt should be downloaded to source"
        )
        assert (source / "test3.txt").exists(), "test3.txt should exist on source"

        # Verify no deletions occurred
        assert stats["deletes_remote"] == 0, (
            "DESTINATION_WINS should not delete remote files"
        )

        print(
            "✓ DESTINATION_WINS downloads remote-only files "
            "(streaming mode) test passed"
        )


def test_destination_wins_overwrites_with_remote_version():
    """Test DESTINATION_WINS overwrites local with remote when different.

    Bug report scenario:
    - test3.txt exists on both sides but with different sizes/content
    - Source: test3.txt (48 bytes, "local content")
    - Destination: test3.txt (64 bytes, "remote content 3...")
    - Expected: Download remote version, overwriting local
    """
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        source = base / "source"
        dest_storage = base / "dest"
        source.mkdir()
        dest_storage.mkdir()

        # Setup: both have test3.txt but different content/sizes
        local_content = "local content"  # Shorter
        remote_content = (
            "remote content 3 - different from local and much longer"  # Longer
        )

        (source / "test3.txt").write_text(local_content)
        (dest_storage / "test3.txt").write_text(remote_content)

        local_size_before = (source / "test3.txt").stat().st_size
        remote_size = (dest_storage / "test3.txt").stat().st_size

        print(
            f"Before sync - Local size: {local_size_before}, Remote size: {remote_size}"
        )

        # Create engine
        client = LocalStorageClient(dest_storage)
        factory = create_entries_manager_factory(client)
        output = DefaultOutputHandler(quiet=True)
        engine = SyncEngine(client, factory, output=output)

        pair = SyncPair(source=source, destination="", sync_mode=SyncMode.TWO_WAY)

        # Sync with DESTINATION_WINS preference
        stats = engine.sync_pair(
            pair,
            use_streaming=False,
            initial_sync_preference=InitialSyncPreference.DESTINATION_WINS,
        )

        print(f"Stats: {stats}")

        # Expected: Download remote version (destination wins on conflicts)
        assert stats["downloads"] >= 1, (
            f"Expected at least 1 download, got {stats['downloads']}"
        )

        # Verify local file was overwritten with remote version
        local_content_after = (source / "test3.txt").read_text()
        local_size_after = (source / "test3.txt").stat().st_size

        assert local_content_after == remote_content, (
            f"Local file should have remote content. Got: {local_content_after}"
        )
        assert local_size_after == remote_size, (
            f"Local file should have remote size {remote_size}, got {local_size_after}"
        )

        print("✓ DESTINATION_WINS overwrites with remote version test passed")


def test_destination_wins_deletes_source_only_files():
    """Test DESTINATION_WINS deletes files that exist only on source.

    Per the bug report and mode definition:
    - Files only on source: deleted from source
    - Files only on destination: downloaded to source
    """
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        source = base / "source"
        dest_storage = base / "dest"
        source.mkdir()
        dest_storage.mkdir()

        # Setup: source has file1 and file2, dest has only file2
        (source / "file1.txt").write_text("source only file")
        (source / "file2.txt").write_text("common file source")
        (dest_storage / "file2.txt").write_text("common file dest")

        # Create engine
        client = LocalStorageClient(dest_storage)
        factory = create_entries_manager_factory(client)
        output = DefaultOutputHandler(quiet=True)
        engine = SyncEngine(client, factory, output=output)

        pair = SyncPair(source=source, destination="", sync_mode=SyncMode.TWO_WAY)

        # Sync with DESTINATION_WINS preference
        stats = engine.sync_pair(
            pair,
            use_streaming=False,
            initial_sync_preference=InitialSyncPreference.DESTINATION_WINS,
        )

        print(f"Stats: {stats}")

        # Expected: Delete file1.txt from source (only on source, not on dest)
        assert stats["deletes_local"] == 1, (
            f"Expected 1 local deletion, got {stats['deletes_local']}"
        )

        # Verify file1.txt was deleted from source
        assert not (source / "file1.txt").exists(), (
            "file1.txt should be deleted from source (not on destination)"
        )

        # Verify file2.txt still exists (it's on both sides)
        assert (source / "file2.txt").exists(), "file2.txt should exist on source"
        assert (dest_storage / "file2.txt").exists(), (
            "file2.txt should exist on destination"
        )

        print("✓ DESTINATION_WINS deletes source-only files test passed")


def test_destination_wins_state_file_correctness():
    """Test state file only marks files as synced if they exist on source.

    Bug report issue:
    - State file marked test1.txt and test2.txt as synced
    - But they didn't exist in source_tree
    - This is incorrect - synced_files should only include files on BOTH
    """
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        source = base / "source"
        dest_storage = base / "dest"
        source.mkdir()
        dest_storage.mkdir()

        # Setup: source has only test3.txt, dest has all 3
        (source / "test3.txt").write_text("local content")
        (dest_storage / "test1.txt").write_text("remote content 1")
        (dest_storage / "test2.txt").write_text("remote content 2")
        (dest_storage / "test3.txt").write_text("remote content 3")

        # Create engine
        client = LocalStorageClient(dest_storage)
        factory = create_entries_manager_factory(client)
        output = DefaultOutputHandler(quiet=True)
        engine = SyncEngine(client, factory, output=output)

        pair = SyncPair(source=source, destination="", sync_mode=SyncMode.TWO_WAY)

        # Sync with DESTINATION_WINS
        _stats = engine.sync_pair(
            pair,
            use_streaming=False,
            initial_sync_preference=InitialSyncPreference.DESTINATION_WINS,
        )

        # After sync, all 3 files should exist on source (downloaded)
        assert (source / "test1.txt").exists(), (
            "test1.txt should exist on source after sync"
        )
        assert (source / "test2.txt").exists(), (
            "test2.txt should exist on source after sync"
        )
        assert (source / "test3.txt").exists(), (
            "test3.txt should exist on source after sync"
        )

        # Load state file and verify
        state = engine.state_manager.load_state(source, "", pair.storage_id)
        assert state is not None, "State file should exist after sync"

        # Verify synced_files includes all 3 files
        assert "test1.txt" in state.synced_files, (
            "test1.txt should be in synced_files (was downloaded)"
        )
        assert "test2.txt" in state.synced_files, (
            "test2.txt should be in synced_files (was downloaded)"
        )
        assert "test3.txt" in state.synced_files, (
            "test3.txt should be in synced_files (exists on both)"
        )

        # Verify source_tree has all 3 files
        source_tree_paths = set(state.source_tree.tree.keys())
        assert "test1.txt" in source_tree_paths, "test1.txt should be in source_tree"
        assert "test2.txt" in source_tree_paths, "test2.txt should be in source_tree"
        assert "test3.txt" in source_tree_paths, "test3.txt should be in source_tree"

        # Verify destination_tree has all 3 files
        dest_tree_paths = set(state.destination_tree.tree.keys())
        assert "test1.txt" in dest_tree_paths, "test1.txt should be in destination_tree"
        assert "test2.txt" in dest_tree_paths, "test2.txt should be in destination_tree"
        assert "test3.txt" in dest_tree_paths, "test3.txt should be in destination_tree"

        print("✓ DESTINATION_WINS state file correctness test passed")


def test_destination_wins_state_file_correctness_streaming():
    """Test state file correctness in streaming mode.

    Same as traditional mode test but with streaming enabled.
    """
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        source = base / "source"
        dest_storage = base / "dest"
        source.mkdir()
        dest_storage.mkdir()

        # Setup: source has only test3.txt, dest has all 3
        (source / "test3.txt").write_text("local content")
        (dest_storage / "test1.txt").write_text("remote content 1")
        (dest_storage / "test2.txt").write_text("remote content 2")
        (dest_storage / "test3.txt").write_text("remote content 3")

        # Create engine
        client = LocalStorageClient(dest_storage)
        factory = create_entries_manager_factory(client)
        output = DefaultOutputHandler(quiet=True)
        engine = SyncEngine(client, factory, output=output)

        pair = SyncPair(source=source, destination="", sync_mode=SyncMode.TWO_WAY)

        # Sync with DESTINATION_WINS in streaming mode
        _stats = engine.sync_pair(
            pair,
            use_streaming=True,  # Streaming mode
            initial_sync_preference=InitialSyncPreference.DESTINATION_WINS,
        )

        # After sync, all 3 files should exist on source
        assert (source / "test1.txt").exists(), (
            "test1.txt should exist on source after sync"
        )
        assert (source / "test2.txt").exists(), (
            "test2.txt should exist on source after sync"
        )
        assert (source / "test3.txt").exists(), (
            "test3.txt should exist on source after sync"
        )

        # Load state file and verify
        state = engine.state_manager.load_state(source, "", pair.storage_id)
        assert state is not None, "State file should exist after sync"

        # Verify synced_files includes all 3 files
        assert len(state.synced_files) == 3, (
            f"Expected 3 synced files, got {len(state.synced_files)}"
        )
        assert "test1.txt" in state.synced_files
        assert "test2.txt" in state.synced_files
        assert "test3.txt" in state.synced_files

        # Verify both trees have all 3 files
        assert len(state.source_tree.tree) == 3, "source_tree should have 3 files"
        assert len(state.destination_tree.tree) == 3, (
            "destination_tree should have 3 files"
        )

        print("✓ DESTINATION_WINS state file correctness (streaming) test passed")


if __name__ == "__main__":
    print("Testing Initial Sync Preferences...\n")
    test_initial_sync_merge()
    test_initial_sync_source_wins()
    test_initial_sync_destination_wins()
    test_initial_sync_risk_warning_many_remote()
    test_initial_sync_risk_warning_many_local()
    test_no_warning_when_preference_set()

    print("\n" + "=" * 60)
    print("Testing DESTINATION_WINS Bug Fixes...")
    print("=" * 60 + "\n")

    test_destination_wins_downloads_remote_only_files_traditional()
    test_destination_wins_downloads_remote_only_files_streaming()
    test_destination_wins_overwrites_with_remote_version()
    test_destination_wins_deletes_source_only_files()
    test_destination_wins_state_file_correctness()
    test_destination_wins_state_file_correctness_streaming()

    print("\n✅ All tests passed!")
