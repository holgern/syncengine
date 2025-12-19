"""Tests for sync state invalidation and change detection bugs.

This test suite reproduces the bugs described in SYNCENGINE_BUG_REPORT.md:
- Issue 1: Stale state prevents re-synchronization
- Issue 2: File changes not detected (deletions, size changes, mtime changes)

These tests should FAIL initially, demonstrating the bugs, and will PASS
once the state validation logic is implemented.
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import Mock

import pytest

from syncengine.engine import SyncEngine
from syncengine.models import FileEntry
from syncengine.modes import SyncMode
from syncengine.pair import SyncPair
from syncengine.protocols import (
    FileEntriesManagerProtocol,
    OutputHandlerProtocol,
    StorageClientProtocol,
)
from syncengine.state import SyncStateManager


@pytest.fixture
def mock_entries_manager_factory():
    """Create a mock entries manager factory."""

    class MockEntriesManagerFactory:
        def __init__(self):
            self.manager = Mock(spec=FileEntriesManagerProtocol)
            # Return a mock folder entry with an id attribute
            mock_folder = Mock()
            mock_folder.id = 999
            self.manager.find_folder_by_name.return_value = mock_folder
            self.manager.get_all_recursive.return_value = []
            self.manager.iter_all_recursive.side_effect = lambda *args, **kwargs: iter(
                []
            )

        def __call__(self, client, storage_id):
            return self.manager

    return MockEntriesManagerFactory()


@pytest.fixture
def mock_client():
    """Create a mock storage client."""
    client = Mock(spec=StorageClientProtocol)
    client.delete_file_entries = Mock(return_value={"deleted": True})
    client.upload_file = Mock(return_value={"status": "success", "id": 1})
    return client


@pytest.fixture
def mock_output():
    """Create a quiet mock output formatter."""
    output = Mock(spec=OutputHandlerProtocol)
    output.quiet = True
    return output


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_state_dir():
    """Create a temporary directory for state files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestTwoWaySyncLocalDeletionDetection:
    """Test Case 1: Detect Local Deletions (TWO_WAY).

    Bug: After initial sync, deleting local files is not detected.
    The sync engine says "No changes needed" even though files should
    be deleted from remote.
    """

    def test_two_way_sync_detects_local_deletion(
        self,
        mock_client,
        mock_entries_manager_factory,
        mock_output,
        temp_dir,
        temp_state_dir,
    ):
        """Test that TWO_WAY sync detects when local files are deleted.

        Steps:
        1. Initial sync: sync 3 files (test1.txt, test2.txt, test3.txt)
        2. Delete 2 files locally (test1.txt, test2.txt)
        3. Re-sync: should detect deletions and delete from remote

        Expected: 2 remote deletions
        Actual (BUG): "No changes needed"
        """
        # Setup: Create 3 local files
        file1 = temp_dir / "test1.txt"
        file1.write_text("content1")
        file2 = temp_dir / "test2.txt"
        file2.write_text("content2")
        file3 = temp_dir / "test3.txt"
        file3.write_text("content3")

        # Setup: Mock remote to have all 3 files
        remote_entry1 = FileEntry(
            id=1,
            name="test1.txt",
            type="file",
            file_size=8,
            hash="7e55db001d319a94b0b713529a756623",  # MD5 of "content1"
        )
        remote_entry2 = FileEntry(
            id=2,
            name="test2.txt",
            type="file",
            file_size=8,
            hash="eea670f4ac941df71a3b5f268ebe3eac",  # MD5 of "content2"
        )
        remote_entry3 = FileEntry(
            id=3,
            name="test3.txt",
            type="file",
            file_size=8,
            hash="c96310e55d9677b978eae0dada47642c",  # MD5 of "content3"
        )
        remote_files_list = [
            (remote_entry1, "test1.txt"),
            (remote_entry2, "test2.txt"),
            (remote_entry3, "test3.txt"),
        ]
        mock_entries_manager_factory.manager.get_all_recursive.return_value = (
            remote_files_list
        )
        # Mock iter_all_recursive for streaming mode - fresh iterator
        mock_entries_manager_factory.manager.iter_all_recursive.side_effect = (
            lambda *args, **kwargs: iter([remote_files_list])
        )

        # Create engine with temp state directory
        state_manager = SyncStateManager(state_dir=temp_state_dir)
        engine = SyncEngine(
            mock_client,
            mock_entries_manager_factory,
            output=mock_output,
            state_manager=state_manager,
        )

        pair = SyncPair(
            source=temp_dir,
            destination="/remote",
            sync_mode=SyncMode.TWO_WAY,
        )

        # Step 1: Initial sync (all files match, should skip)
        stats1 = engine.sync_pair(pair, dry_run=False)
        assert stats1["skips"] == 3
        assert stats1["uploads"] == 0
        assert stats1["downloads"] == 0
        assert stats1["deletes_remote"] == 0

        # Step 2: Delete 2 local files
        file1.unlink()
        file2.unlink()

        # Verify files are deleted
        assert not file1.exists()
        assert not file2.exists()
        assert file3.exists()

        # Step 3: Re-sync - should detect local deletions
        stats2 = engine.sync_pair(pair, dry_run=False)

        # BUG: This assertion will FAIL because the engine doesn't detect
        # that files were deleted locally. It will say "No changes needed".
        # Expected: deletes_remote=2 (delete test1.txt and test2.txt from remote)
        # Actual: deletes_remote=0
        assert stats2["deletes_remote"] == 2, (
            f"Expected 2 remote deletions for locally deleted files, "
            f"but got {stats2['deletes_remote']}. "
            f"This demonstrates the state invalidation bug."
        )

        # Verify delete calls were made
        assert mock_client.delete_file_entries.call_count >= 2


class TestTwoWaySyncRemoteDeletionDetection:
    """Test Case 2: Detect Remote Deletions (TWO_WAY).

    Bug: After initial sync, deleting remote files is not detected.
    The sync engine says "No changes needed" even though files should
    be deleted locally.
    """

    def test_two_way_sync_detects_remote_deletion(
        self,
        mock_client,
        mock_entries_manager_factory,
        mock_output,
        temp_dir,
        temp_state_dir,
    ):
        """Test that TWO_WAY sync detects when remote files are deleted.

        Steps:
        1. Initial sync: sync 3 files
        2. Delete 2 files remotely (simulate by removing from mock)
        3. Re-sync: should detect deletions and delete from local

        Expected: 2 local deletions
        Actual (BUG): "No changes needed"
        """
        # Setup: Create 3 local files
        file1 = temp_dir / "test1.txt"
        file1.write_text("content1")
        file2 = temp_dir / "test2.txt"
        file2.write_text("content2")
        file3 = temp_dir / "test3.txt"
        file3.write_text("content3")

        # Setup: Mock remote to have all 3 files initially
        remote_entry1 = FileEntry(
            id=1,
            name="test1.txt",
            type="file",
            file_size=8,
            hash="7e55db001d319a94b0b713529a756623",  # MD5 of "content1"
        )
        remote_entry2 = FileEntry(
            id=2,
            name="test2.txt",
            type="file",
            file_size=8,
            hash="eea670f4ac941df71a3b5f268ebe3eac",  # MD5 of "content2"
        )
        remote_entry3 = FileEntry(
            id=3,
            name="test3.txt",
            type="file",
            file_size=8,
            hash="c96310e55d9677b978eae0dada47642c",  # MD5 of "content3"
        )
        remote_files_list = [
            (remote_entry1, "test1.txt"),
            (remote_entry2, "test2.txt"),
            (remote_entry3, "test3.txt"),
        ]
        mock_entries_manager_factory.manager.get_all_recursive.return_value = (
            remote_files_list
        )
        # Mock iter_all_recursive for streaming mode - fresh iterator
        mock_entries_manager_factory.manager.iter_all_recursive.side_effect = (
            lambda *args, **kwargs: iter([remote_files_list])
        )

        # Create engine with temp state directory
        state_manager = SyncStateManager(state_dir=temp_state_dir)
        engine = SyncEngine(
            mock_client,
            mock_entries_manager_factory,
            output=mock_output,
            state_manager=state_manager,
        )

        pair = SyncPair(
            source=temp_dir,
            destination="/remote",
            sync_mode=SyncMode.TWO_WAY,
        )

        # Step 1: Initial sync (all files match, should skip)
        stats1 = engine.sync_pair(pair, dry_run=False)
        assert stats1["skips"] == 3

        # Step 2: "Delete" 2 remote files (simulate by updating mock)
        remote_files_list = [
            (remote_entry3, "test3.txt"),  # Only test3.txt remains
        ]
        mock_entries_manager_factory.manager.get_all_recursive.return_value = (
            remote_files_list
        )
        # Update iter_all_recursive for the new remote state
        mock_entries_manager_factory.manager.iter_all_recursive.side_effect = (
            lambda *args, **kwargs: iter([remote_files_list])
        )

        # Step 3: Re-sync - should detect remote deletions
        stats2 = engine.sync_pair(pair, dry_run=False)

        # BUG: This assertion will FAIL because the engine doesn't detect
        # that files were deleted remotely.
        # Expected: deletes_local=2 (delete test1.txt and test2.txt locally)
        # Actual: deletes_local=0
        assert stats2["deletes_local"] == 2, (
            f"Expected 2 local deletions for remotely deleted files, "
            f"but got {stats2['deletes_local']}. "
            f"This demonstrates the state invalidation bug."
        )

        # Verify local files were deleted
        assert not file1.exists(), "test1.txt should have been deleted locally"
        assert not file2.exists(), "test2.txt should have been deleted locally"
        assert file3.exists(), "test3.txt should still exist"


class TestSyncDetectsSizeChanges:
    """Test Case 3: Detect Size Changes.

    Bug: After initial sync, modifying file size is not detected.
    The sync engine says "No changes needed" even though file size changed.
    """

    def test_sync_detects_size_change(
        self,
        mock_client,
        mock_entries_manager_factory,
        mock_output,
        temp_dir,
        temp_state_dir,
    ):
        """Test that sync detects when file size changes.

        Steps:
        1. Initial sync: sync file with 8 bytes
        2. Modify file to have different size (16 bytes)
        3. Re-sync: should detect size change and re-upload

        Expected: 1 upload (file was modified)
        Actual (BUG): "No changes needed"
        """
        # Setup: Create local file with original content
        test_file = temp_dir / "test.txt"
        original_content = "original"  # 8 bytes
        test_file.write_text(original_content)

        # Setup: Mock remote file with original size
        remote_entry = FileEntry(
            id=1,
            name="test.txt",
            type="file",
            file_size=len(original_content),
            hash="919c8b643b7133116b02fc0d9bb7df3f",  # MD5 of "original"
        )
        remote_files_list = [
            (remote_entry, "test.txt"),
        ]
        mock_entries_manager_factory.manager.get_all_recursive.return_value = (
            remote_files_list
        )
        # Mock iter_all_recursive for streaming mode - fresh iterator
        mock_entries_manager_factory.manager.iter_all_recursive.side_effect = (
            lambda *args, **kwargs: iter([remote_files_list])
        )

        # Create engine with temp state directory
        state_manager = SyncStateManager(state_dir=temp_state_dir)
        engine = SyncEngine(
            mock_client,
            mock_entries_manager_factory,
            output=mock_output,
            state_manager=state_manager,
        )

        pair = SyncPair(
            source=temp_dir,
            destination="/remote",
            sync_mode=SyncMode.TWO_WAY,
        )

        # Step 1: Initial sync (file matches, should skip)
        stats1 = engine.sync_pair(pair, dry_run=False)
        assert stats1["skips"] == 1
        assert stats1["uploads"] == 0

        # Step 2: Modify file (different size)
        modified_content = "modified content"  # 16 bytes (different size)
        test_file.write_text(modified_content)
        time.sleep(0.1)  # Ensure mtime changes

        # Verify size changed
        assert len(modified_content) != len(original_content)

        # Step 3: Re-sync - should detect size change
        stats2 = engine.sync_pair(pair, dry_run=False)

        # BUG: This assertion will FAIL because the engine doesn't detect
        # that the file size changed.
        # Expected: uploads=1 (file was modified, needs re-upload)
        # Actual: uploads=0 (engine thinks file is still in sync)
        assert stats2["uploads"] == 1, (
            f"Expected 1 upload for size-modified file, "
            f"but got {stats2['uploads']}. "
            f"This demonstrates the state invalidation bug."
        )


class TestSyncDetectsMtimeChanges:
    """Test Case 4: Detect Mtime Changes.

    Bug: After initial sync, modifying file mtime is not detected even
    when content changes (but size stays the same).
    """

    def test_sync_detects_mtime_change(
        self,
        mock_client,
        mock_entries_manager_factory,
        mock_output,
        temp_dir,
        temp_state_dir,
    ):
        """Test that sync detects when file mtime changes.

        Steps:
        1. Initial sync: sync file with original mtime
        2. Modify file (same size, different content)
        3. Re-sync: should detect mtime change and re-upload

        Expected: 1 upload (file was modified)
        Actual (BUG): "No changes needed"
        """
        # Setup: Create local file with original content
        test_file = temp_dir / "test.txt"
        original_content = "content"  # 7 bytes
        test_file.write_text(original_content)
        original_mtime = test_file.stat().st_mtime

        # Setup: Mock remote file with original size
        remote_entry = FileEntry(
            id=1,
            name="test.txt",
            type="file",
            file_size=len(original_content),
            hash="9a0364b9e99bb480dd25e1f0284c8555",  # MD5 of "content"
        )
        remote_files_list = [
            (remote_entry, "test.txt"),
        ]
        mock_entries_manager_factory.manager.get_all_recursive.return_value = (
            remote_files_list
        )
        # Mock iter_all_recursive for streaming mode - fresh iterator
        mock_entries_manager_factory.manager.iter_all_recursive.side_effect = (
            lambda *args, **kwargs: iter([remote_files_list])
        )

        # Create engine with temp state directory
        state_manager = SyncStateManager(state_dir=temp_state_dir)
        engine = SyncEngine(
            mock_client,
            mock_entries_manager_factory,
            output=mock_output,
            state_manager=state_manager,
        )

        pair = SyncPair(
            source=temp_dir,
            destination="/remote",
            sync_mode=SyncMode.TWO_WAY,
        )

        # Step 1: Initial sync (file matches, should skip)
        stats1 = engine.sync_pair(pair, dry_run=False)
        assert stats1["skips"] == 1
        assert stats1["uploads"] == 0

        # Step 2: Modify file (same size, different content, different mtime)
        time.sleep(2.0)  # Ensure mtime differs by >1 second
        modified_content = "CONTENT"  # 7 bytes (same size!)
        test_file.write_text(modified_content)
        new_mtime = test_file.stat().st_mtime

        # Verify size is same but mtime changed
        assert len(modified_content) == len(original_content)
        assert new_mtime > original_mtime + 1.0  # Changed by >1 second

        # Step 3: Re-sync - should detect mtime change
        stats2 = engine.sync_pair(pair, dry_run=False)

        # BUG: This assertion will FAIL because the engine doesn't detect
        # that the file mtime changed (even though content is different).
        # Expected: uploads=1 (file was modified, needs re-upload)
        # Actual: uploads=0 (engine thinks file is still in sync)
        assert stats2["uploads"] == 1, (
            f"Expected 1 upload for mtime-modified file, "
            f"but got {stats2['uploads']}. "
            f"This demonstrates the state invalidation bug."
        )


class TestStateIsolationByStorageId:
    """Test Case 5: State Isolation by storage_id.

    Bug: When destination_path is "" or "/", state files may collide
    between different sync operations targeting different storage IDs.
    """

    def test_state_isolation_different_storage(
        self,
        mock_client,
        mock_entries_manager_factory,
        mock_output,
        temp_dir,
        temp_state_dir,
    ):
        """Test that state is isolated by storage_id.

        Steps:
        1. Sync to storage A (storage_id=1)
        2. Modify local file
        3. Sync to storage B (storage_id=2) - should upload new file

        Expected: File uploaded to both storages
        Actual (BUG): Storage B might skip upload due to storage A state
        """
        # Setup: Create local file
        test_file = temp_dir / "test.txt"
        test_file.write_text("original")

        # Setup: Mock remote for both storages (empty initially)
        mock_entries_manager_factory.manager.get_all_recursive.return_value = []

        # Create engine with temp state directory
        state_manager = SyncStateManager(state_dir=temp_state_dir)
        engine = SyncEngine(
            mock_client,
            mock_entries_manager_factory,
            output=mock_output,
            state_manager=state_manager,
        )

        # Step 1: Sync to storage A
        pair_a = SyncPair(
            source=temp_dir,
            destination="/remote",
            sync_mode=SyncMode.TWO_WAY,
            storage_id=1,
        )
        stats_a = engine.sync_pair(pair_a, dry_run=False)
        assert stats_a["uploads"] == 1

        # Step 2: Modify local file
        test_file.write_text("modified")

        # Step 3: Sync to storage B (different storage_id)
        pair_b = SyncPair(
            source=temp_dir,
            destination="/remote",
            sync_mode=SyncMode.TWO_WAY,
            storage_id=2,
        )
        stats_b = engine.sync_pair(pair_b, dry_run=False)

        # BUG: This might FAIL if state keys don't include storage_id.
        # Expected: uploads=1 (new storage, should upload)
        # Actual: uploads=0 (state collision makes engine think it's synced)
        assert stats_b["uploads"] == 1, (
            f"Expected 1 upload to storage B, but got {stats_b['uploads']}. "
            f"This may indicate state collision between different storage IDs."
        )


class TestStateIsolationByDestinationPath:
    """Test state isolation when destination paths differ."""

    def test_state_isolation_different_destinations(
        self,
        mock_client,
        mock_entries_manager_factory,
        mock_output,
        temp_dir,
        temp_state_dir,
    ):
        """Test that state is isolated by destination path.

        Bug from report: When destination_path is "" or "/", state key
        generation may create collisions.
        """
        # Setup: Create local file
        test_file = temp_dir / "test.txt"
        test_file.write_text("content")

        # Setup: Mock remote (empty initially)
        mock_entries_manager_factory.manager.get_all_recursive.return_value = []

        # Create engine with temp state directory
        state_manager = SyncStateManager(state_dir=temp_state_dir)
        engine = SyncEngine(
            mock_client,
            mock_entries_manager_factory,
            output=mock_output,
            state_manager=state_manager,
        )

        # Sync to root destination
        pair_root = SyncPair(
            source=temp_dir,
            destination="/",
            sync_mode=SyncMode.TWO_WAY,
            storage_id=1,
        )
        stats_root = engine.sync_pair(pair_root, dry_run=False)
        assert stats_root["uploads"] == 1

        # Sync to specific folder destination
        pair_folder = SyncPair(
            source=temp_dir,
            destination="/folder",
            sync_mode=SyncMode.TWO_WAY,
            storage_id=1,
        )
        stats_folder = engine.sync_pair(pair_folder, dry_run=False)

        # Should upload again to different destination
        # BUG: Might fail if destination_path="" causes collision
        assert stats_folder["uploads"] == 1, (
            f"Expected 1 upload to /folder destination, "
            f"but got {stats_folder['uploads']}. "
            f"State may be incorrectly shared between destinations."
        )


class TestStateInvalidationAfterExternalChanges:
    """Test that state is properly invalidated after external changes.

    This tests the core issue: state should be validated on sync start,
    and invalidated files should be re-synced.
    """

    def test_state_invalidation_on_external_deletion(
        self,
        mock_client,
        mock_entries_manager_factory,
        mock_output,
        temp_dir,
        temp_state_dir,
    ):
        """Test that external file deletion invalidates state.

        Scenario: User manually deletes remote file outside of sync,
        then runs sync again. State should detect this and handle it.
        """
        # Setup: Create local file
        test_file = temp_dir / "test.txt"
        test_file.write_text("content")

        # Setup: Mock remote file
        remote_entry = FileEntry(
            id=1,
            name="test.txt",
            type="file",
            file_size=7,
            hash="9a0364b9e99bb480dd25e1f0284c8555",  # MD5 of "content"
        )
        remote_files_list = [
            (remote_entry, "test.txt"),
        ]
        mock_entries_manager_factory.manager.get_all_recursive.return_value = (
            remote_files_list
        )
        # Mock iter_all_recursive for streaming mode - fresh iterator
        mock_entries_manager_factory.manager.iter_all_recursive.side_effect = (
            lambda *args, **kwargs: iter([remote_files_list])
        )

        # Create engine with temp state directory
        state_manager = SyncStateManager(state_dir=temp_state_dir)
        engine = SyncEngine(
            mock_client,
            mock_entries_manager_factory,
            output=mock_output,
            state_manager=state_manager,
        )

        pair = SyncPair(
            source=temp_dir,
            destination="/remote",
            sync_mode=SyncMode.TWO_WAY,
        )

        # Initial sync
        stats1 = engine.sync_pair(pair, dry_run=False)
        assert stats1["skips"] == 1

        # External change: File deleted locally (simulating corruption/manual deletion)
        test_file.unlink()

        # Remote still has the file
        # This scenario should be handled: either download from remote
        # or delete from remote depending on sync mode expectations

        # Re-sync
        stats2 = engine.sync_pair(pair, dry_run=False)

        # In TWO_WAY mode, local deletion should propagate to remote
        assert (
            stats2["deletes_remote"] == 1
        ), "Local deletion should trigger remote deletion in TWO_WAY mode"
