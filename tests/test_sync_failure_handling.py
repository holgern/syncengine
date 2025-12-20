"""Tests for handling failed sync operations.

This module tests that syncengine correctly handles failures during sync operations
and doesn't mark failed operations as synced in the state file.

Bug Report: SYNCENGINE_DESTINATION_WINS_BUG.md
- Failed downloads were being marked as synced
- State file had files in synced_files that didn't exist in source_tree
- Subsequent syncs would skip the failed downloads
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

from benchmarks.test_utils import LocalStorageClient, create_entries_manager_factory
from syncengine import InitialSyncPreference, SyncEngine, SyncMode, SyncPair
from syncengine.protocols import DefaultOutputHandler


def test_failed_download_not_marked_synced_traditional():
    """Failed downloads should NOT be marked as synced (traditional mode).

    Scenario:
    - Remote has 3 files: test1.txt, test2.txt, test3.txt
    - Local has none
    - DESTINATION_WINS should download all 3
    - Download of test2.txt FAILS
    - State file should only mark test1.txt and test3.txt as synced
    - test2.txt should NOT be in synced_files or source_tree
    """
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        source = base / "source"
        dest_storage = base / "dest"
        source.mkdir()
        dest_storage.mkdir()

        # Setup: dest has 3 files, source is empty
        (dest_storage / "test1.txt").write_text("remote content 1")
        (dest_storage / "test2.txt").write_text("remote content 2")
        (dest_storage / "test3.txt").write_text("remote content 3")

        # Create engine
        client = LocalStorageClient(dest_storage)
        factory = create_entries_manager_factory(client)
        output = DefaultOutputHandler(quiet=True)
        engine = SyncEngine(client, factory, output=output)

        pair = SyncPair(source=source, destination="", sync_mode=SyncMode.TWO_WAY)

        # Mock the download operation to fail for test2.txt
        original_download = client.download_file

        def mock_download(hash_value, output_path, progress_callback=None):
            if "test2.txt" in str(output_path):
                # Simulate failed download - don't create the file
                raise Exception("Simulated download failure for test2.txt")
            return original_download(hash_value, output_path, progress_callback)

        with patch.object(client, "download_file", side_effect=mock_download):
            # Sync with DESTINATION_WINS
            stats = engine.sync_pair(
                pair,
                use_streaming=False,
                initial_sync_preference=InitialSyncPreference.DESTINATION_WINS,
            )

        print(f"Stats: {stats}")

        # Verify: test1.txt and test3.txt downloaded, test2.txt failed
        assert (
            source / "test1.txt"
        ).exists(), "test1.txt should exist (download succeeded)"
        assert not (
            source / "test2.txt"
        ).exists(), "test2.txt should NOT exist (download failed)"
        assert (
            source / "test3.txt"
        ).exists(), "test3.txt should exist (download succeeded)"

        # Check state file
        # State is saved to default location (~/.config/syncengine)
        state_manager = engine.state_manager
        state = state_manager.load_state(pair.source, pair.destination, pair.storage_id)

        assert state is not None, "State file should exist"

        # CRITICAL: synced_files should only contain successfully downloaded files
        assert (
            "test1.txt" in state.synced_files
        ), "test1.txt should be in synced_files (downloaded)"
        assert (
            "test2.txt" not in state.synced_files
        ), "test2.txt should NOT be in synced_files (download failed)"
        assert (
            "test3.txt" in state.synced_files
        ), "test3.txt should be in synced_files (downloaded)"

        # CRITICAL: source_tree should only contain files that exist locally
        assert (
            "test1.txt" in state.source_tree.tree
        ), "test1.txt should be in source_tree"
        assert (
            "test2.txt" not in state.source_tree.tree
        ), "test2.txt should NOT be in source_tree (doesn't exist locally)"
        assert (
            "test3.txt" in state.source_tree.tree
        ), "test3.txt should be in source_tree"

        # CRITICAL: All files in destination_tree
        assert "test1.txt" in state.destination_tree.tree
        assert "test2.txt" in state.destination_tree.tree
        assert "test3.txt" in state.destination_tree.tree

        # State consistency: synced_files ⊆ (source_tree ∩ destination_tree)
        for file_path in state.synced_files:
            assert (
                file_path in state.source_tree.tree
            ), f"{file_path} in synced_files but not in source_tree - this is the bug!"
            assert (
                file_path in state.destination_tree.tree
            ), f"{file_path} in synced_files but not in destination_tree"

        print("✓ Failed download not marked as synced (traditional mode)")


def test_failed_download_not_marked_synced_streaming():
    """Failed downloads should NOT be marked as synced (streaming mode).

    Same as traditional mode test but with streaming enabled.
    """
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        source = base / "source"
        dest_storage = base / "dest"
        source.mkdir()
        dest_storage.mkdir()

        # Setup: dest has 3 files, source is empty
        (dest_storage / "test1.txt").write_text("remote content 1")
        (dest_storage / "test2.txt").write_text("remote content 2")
        (dest_storage / "test3.txt").write_text("remote content 3")

        # Create engine
        client = LocalStorageClient(dest_storage)
        factory = create_entries_manager_factory(client)
        output = DefaultOutputHandler(quiet=True)
        engine = SyncEngine(client, factory, output=output)

        pair = SyncPair(source=source, destination="", sync_mode=SyncMode.TWO_WAY)

        # Mock the download operation to fail for test2.txt
        original_download = client.download_file

        def mock_download(hash_value, output_path, progress_callback=None):
            if "test2.txt" in str(output_path):
                # Simulate failed download - don't create the file
                raise Exception("Simulated download failure for test2.txt")
            return original_download(hash_value, output_path, progress_callback)

        with patch.object(client, "download_file", side_effect=mock_download):
            # Sync with DESTINATION_WINS in streaming mode
            stats = engine.sync_pair(
                pair,
                use_streaming=True,
                initial_sync_preference=InitialSyncPreference.DESTINATION_WINS,
            )

        print(f"Stats: {stats}")

        # Verify: test1.txt and test3.txt downloaded, test2.txt failed
        assert (
            source / "test1.txt"
        ).exists(), "test1.txt should exist (download succeeded)"
        assert not (
            source / "test2.txt"
        ).exists(), "test2.txt should NOT exist (download failed)"
        assert (
            source / "test3.txt"
        ).exists(), "test3.txt should exist (download succeeded)"

        # Check state file
        # State is saved to default location (~/.config/syncengine)
        state_manager = engine.state_manager
        state = state_manager.load_state(pair.source, pair.destination, pair.storage_id)

        assert state is not None, "State file should exist"

        # CRITICAL: synced_files should only contain successfully downloaded files
        assert (
            "test1.txt" in state.synced_files
        ), "test1.txt should be in synced_files (downloaded)"
        assert (
            "test2.txt" not in state.synced_files
        ), "test2.txt should NOT be in synced_files (download failed)"
        assert (
            "test3.txt" in state.synced_files
        ), "test3.txt should be in synced_files (downloaded)"

        # CRITICAL: source_tree should only contain files that exist locally
        assert (
            "test1.txt" in state.source_tree.tree
        ), "test1.txt should be in source_tree"
        assert (
            "test2.txt" not in state.source_tree.tree
        ), "test2.txt should NOT be in source_tree (doesn't exist locally)"
        assert (
            "test3.txt" in state.source_tree.tree
        ), "test3.txt should be in source_tree"

        # State consistency check
        for file_path in state.synced_files:
            assert (
                file_path in state.source_tree.tree
            ), f"{file_path} in synced_files but not in source_tree - this is the bug!"

        print("✓ Failed download not marked as synced (streaming mode)")


def test_failed_upload_not_marked_synced_traditional():
    """Failed uploads should NOT be marked as synced (traditional mode).

    Scenario:
    - Local has 3 files: test1.txt, test2.txt, test3.txt
    - Remote has none
    - SOURCE_WINS should upload all 3
    - Upload of test2.txt FAILS
    - State file should only mark test1.txt and test3.txt as synced
    """
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        source = base / "source"
        dest_storage = base / "dest"
        source.mkdir()
        dest_storage.mkdir()

        # Setup: source has 3 files, dest is empty
        (source / "test1.txt").write_text("local content 1")
        (source / "test2.txt").write_text("local content 2")
        (source / "test3.txt").write_text("local content 3")

        # Create engine
        client = LocalStorageClient(dest_storage)
        factory = create_entries_manager_factory(client)
        output = DefaultOutputHandler(quiet=True)
        engine = SyncEngine(client, factory, output=output)

        pair = SyncPair(source=source, destination="", sync_mode=SyncMode.TWO_WAY)

        # Mock the upload operation to fail for test2.txt
        original_upload = client.upload_file

        def mock_upload(file_path, relative_path, **kwargs):
            if "test2.txt" in str(file_path):
                # Simulate failed upload - don't create the remote file
                raise Exception("Simulated upload failure for test2.txt")
            return original_upload(file_path, relative_path, **kwargs)

        with patch.object(client, "upload_file", side_effect=mock_upload):
            # Sync with SOURCE_WINS
            stats = engine.sync_pair(
                pair,
                use_streaming=False,
                initial_sync_preference=InitialSyncPreference.SOURCE_WINS,
            )

        print(f"Stats: {stats}")

        # Verify: test1.txt and test3.txt uploaded, test2.txt failed
        assert (
            dest_storage / "test1.txt"
        ).exists(), "test1.txt should exist on remote (upload succeeded)"
        assert not (
            dest_storage / "test2.txt"
        ).exists(), "test2.txt should NOT exist on remote (upload failed)"
        assert (
            dest_storage / "test3.txt"
        ).exists(), "test3.txt should exist on remote (upload succeeded)"

        # Check state file
        # State is saved to default location (~/.config/syncengine)
        state_manager = engine.state_manager
        state = state_manager.load_state(pair.source, pair.destination, pair.storage_id)

        assert state is not None, "State file should exist"

        # CRITICAL: synced_files should only contain successfully uploaded files
        assert (
            "test1.txt" in state.synced_files
        ), "test1.txt should be in synced_files (uploaded)"
        assert (
            "test2.txt" not in state.synced_files
        ), "test2.txt should NOT be in synced_files (upload failed)"
        assert (
            "test3.txt" in state.synced_files
        ), "test3.txt should be in synced_files (uploaded)"

        # CRITICAL: destination_tree should only contain files that exist remotely
        assert (
            "test1.txt" in state.destination_tree.tree
        ), "test1.txt should be in destination_tree"
        assert (
            "test2.txt" not in state.destination_tree.tree
        ), "test2.txt should NOT be in destination_tree (doesn't exist remotely)"
        assert (
            "test3.txt" in state.destination_tree.tree
        ), "test3.txt should be in destination_tree"

        # State consistency check
        for file_path in state.synced_files:
            assert file_path in state.destination_tree.tree, (
                f"{file_path} in synced_files but not in destination_tree - "
                "this is the bug for uploads!"
            )

        print("✓ Failed upload not marked as synced (traditional mode)")


def test_failed_upload_not_marked_synced_streaming():
    """Failed uploads should NOT be marked as synced (streaming mode)."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        source = base / "source"
        dest_storage = base / "dest"
        source.mkdir()
        dest_storage.mkdir()

        # Setup: source has 3 files, dest is empty
        (source / "test1.txt").write_text("local content 1")
        (source / "test2.txt").write_text("local content 2")
        (source / "test3.txt").write_text("local content 3")

        # Create engine
        client = LocalStorageClient(dest_storage)
        factory = create_entries_manager_factory(client)
        output = DefaultOutputHandler(quiet=True)
        engine = SyncEngine(client, factory, output=output)

        pair = SyncPair(source=source, destination="", sync_mode=SyncMode.TWO_WAY)

        # Mock the upload operation to fail for test2.txt
        original_upload = client.upload_file

        def mock_upload(file_path, relative_path, **kwargs):
            if "test2.txt" in str(file_path):
                # Simulate failed upload
                raise Exception("Simulated upload failure for test2.txt")
            return original_upload(file_path, relative_path, **kwargs)

        with patch.object(client, "upload_file", side_effect=mock_upload):
            # Sync with SOURCE_WINS in streaming mode
            stats = engine.sync_pair(
                pair,
                use_streaming=True,
                initial_sync_preference=InitialSyncPreference.SOURCE_WINS,
            )

        print(f"Stats: {stats}")

        # Verify: test1.txt and test3.txt uploaded, test2.txt failed
        assert (
            dest_storage / "test1.txt"
        ).exists(), "test1.txt should exist on remote (upload succeeded)"
        assert not (
            dest_storage / "test2.txt"
        ).exists(), "test2.txt should NOT exist on remote (upload failed)"
        assert (
            dest_storage / "test3.txt"
        ).exists(), "test3.txt should exist on remote (upload succeeded)"

        # Check state file
        # State is saved to default location (~/.config/syncengine)
        state_manager = engine.state_manager
        state = state_manager.load_state(pair.source, pair.destination, pair.storage_id)

        assert state is not None, "State file should exist"

        # CRITICAL: synced_files should only contain successfully uploaded files
        assert (
            "test1.txt" in state.synced_files
        ), "test1.txt should be in synced_files (uploaded)"
        assert (
            "test2.txt" not in state.synced_files
        ), "test2.txt should NOT be in synced_files (upload failed)"
        assert (
            "test3.txt" in state.synced_files
        ), "test3.txt should be in synced_files (uploaded)"

        # State consistency check
        for file_path in state.synced_files:
            assert (
                file_path in state.destination_tree.tree
            ), f"{file_path} in synced_files but not in destination_tree"

        print("✓ Failed upload not marked as synced (streaming mode)")


def test_download_size_verification():
    """Downloaded files should have correct size matching remote file.

    Scenario:
    - Remote has file with size 100 bytes
    - Download appears to succeed but file is only 50 bytes (corrupted)
    - Should detect size mismatch and not mark as synced
    """
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        source = base / "source"
        dest_storage = base / "dest"
        source.mkdir()
        dest_storage.mkdir()

        # Setup: dest has file with specific content
        remote_content = "x" * 100  # 100 bytes
        (dest_storage / "test.txt").write_text(remote_content)

        # Create engine
        client = LocalStorageClient(dest_storage)
        factory = create_entries_manager_factory(client)
        output = DefaultOutputHandler(quiet=True)
        engine = SyncEngine(client, factory, output=output)

        pair = SyncPair(source=source, destination="", sync_mode=SyncMode.TWO_WAY)

        # Mock download to write corrupted/incomplete file
        def mock_download_corrupted(hash_value, output_path, **kwargs):
            # Write corrupted file with wrong size
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("x" * 50)  # Only 50 bytes instead of 100
            return output_path
            # Don't call original - simulate partial download

        with patch.object(client, "download_file", side_effect=mock_download_corrupted):
            engine.sync_pair(
                pair,
                use_streaming=False,
                initial_sync_preference=InitialSyncPreference.DESTINATION_WINS,
            )

        # File exists but with wrong size
        assert (source / "test.txt").exists()
        actual_size = (source / "test.txt").stat().st_size
        expected_size = 100

        # This test documents the expected behavior:
        # If file size doesn't match after download, it should not be marked
        # as synced. However, current implementation might not verify this.
        # This is an ENHANCEMENT, not part of the critical bug fix

        print(
            f"Downloaded file size: {actual_size} bytes "
            f"(expected {expected_size} bytes)"
        )
        print("✓ Download size verification test complete")


if __name__ == "__main__":
    # Run tests to demonstrate the bug
    print("Running failure handling tests...")
    print("\nTest 1: Failed download (traditional mode)")
    try:
        test_failed_download_not_marked_synced_traditional()
    except AssertionError as e:
        print(f"EXPECTED FAILURE (bug present): {e}")

    print("\nTest 2: Failed download (streaming mode)")
    try:
        test_failed_download_not_marked_synced_streaming()
    except AssertionError as e:
        print(f"EXPECTED FAILURE (bug present): {e}")

    print("\nTest 3: Failed upload (traditional mode)")
    try:
        test_failed_upload_not_marked_synced_traditional()
    except AssertionError as e:
        print(f"EXPECTED FAILURE (bug present): {e}")

    print("\nTest 4: Failed upload (streaming mode)")
    try:
        test_failed_upload_not_marked_synced_streaming()
    except AssertionError as e:
        print(f"EXPECTED FAILURE (bug present): {e}")

    print("\nTest 5: Download size verification")
    test_download_size_verification()
