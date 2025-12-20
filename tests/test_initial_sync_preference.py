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
        assert (
            stats["deletes_remote"] == 1
        ), f"Expected 1 remote delete, got {stats['deletes_remote']}"

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
        assert (
            stats["deletes_local"] == 1
        ), f"Expected 1 local delete, got {stats['deletes_local']}"

        # Verify: both locations have only file2
        assert not (source / "file1.txt").exists()
        assert (source / "file2.txt").exists()
        assert not (dest_storage / "file1.txt").exists()
        assert (dest_storage / "file2.txt").exists()

        print("✓ DESTINATION_WINS test passed")


if __name__ == "__main__":
    print("Testing Initial Sync Preferences...\n")
    test_initial_sync_merge()
    test_initial_sync_source_wins()
    test_initial_sync_destination_wins()
    print("\n✅ All tests passed!")
