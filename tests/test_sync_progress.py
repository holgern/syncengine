"""Tests for sync progress tracking."""

import threading
from unittest.mock import MagicMock

from syncengine.progress import (
    SyncProgressEvent,
    SyncProgressInfo,
    SyncProgressTracker,
)


class TestSyncProgressEvent:
    """Test SyncProgressEvent enum."""

    def test_event_values(self):
        """Test that all event values are defined."""
        assert SyncProgressEvent.SCAN_DIR_START.value == "scan_dir_start"
        assert SyncProgressEvent.SCAN_DIR_COMPLETE.value == "scan_dir_complete"
        assert SyncProgressEvent.UPLOAD_BATCH_START.value == "upload_batch_start"
        assert SyncProgressEvent.UPLOAD_FILE_START.value == "upload_file_start"
        assert SyncProgressEvent.UPLOAD_FILE_PROGRESS.value == "upload_file_progress"
        assert SyncProgressEvent.UPLOAD_FILE_COMPLETE.value == "upload_file_complete"
        assert SyncProgressEvent.UPLOAD_FILE_ERROR.value == "upload_file_error"
        assert SyncProgressEvent.UPLOAD_BATCH_COMPLETE.value == "upload_batch_complete"
        assert SyncProgressEvent.SYNC_START.value == "sync_start"
        assert SyncProgressEvent.SYNC_COMPLETE.value == "sync_complete"


class TestSyncProgressInfo:
    """Test SyncProgressInfo dataclass."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        info = SyncProgressInfo(event=SyncProgressEvent.SYNC_START)
        assert info.event == SyncProgressEvent.SYNC_START
        assert info.directory == ""
        assert info.file_path == ""
        assert info.files_in_batch == 0
        assert info.files_uploaded == 0
        assert info.files_skipped == 0
        assert info.bytes_uploaded == 0
        assert info.bytes_total is None
        assert info.current_file_bytes == 0
        assert info.current_file_total == 0
        assert info.error_message == ""
        assert info.folder_files_uploaded == 0
        assert info.folder_files_total == 0
        assert info.folder_bytes_uploaded == 0
        assert info.folder_bytes_total == 0

    def test_custom_values(self):
        """Test creating progress info with custom values."""
        info = SyncProgressInfo(
            event=SyncProgressEvent.UPLOAD_FILE_PROGRESS,
            directory="test/dir",
            file_path="test/file.txt",
            files_in_batch=5,
            files_uploaded=10,
            files_skipped=2,
            bytes_uploaded=1024,
            bytes_total=2048,
            current_file_bytes=512,
            current_file_total=1024,
            error_message="test error",
            folder_files_uploaded=3,
            folder_files_total=5,
            folder_bytes_uploaded=800,
            folder_bytes_total=1500,
        )
        assert info.event == SyncProgressEvent.UPLOAD_FILE_PROGRESS
        assert info.directory == "test/dir"
        assert info.file_path == "test/file.txt"
        assert info.files_in_batch == 5
        assert info.files_uploaded == 10
        assert info.files_skipped == 2
        assert info.bytes_uploaded == 1024
        assert info.bytes_total == 2048
        assert info.current_file_bytes == 512
        assert info.current_file_total == 1024
        assert info.error_message == "test error"
        assert info.folder_files_uploaded == 3
        assert info.folder_files_total == 5
        assert info.folder_bytes_uploaded == 800
        assert info.folder_bytes_total == 1500


class TestSyncProgressTracker:
    """Test SyncProgressTracker class."""

    def test_init_no_callback(self):
        """Test initialization without callback."""
        tracker = SyncProgressTracker()
        assert tracker.callback is None
        assert tracker.total_bytes_uploaded == 0
        assert tracker.total_bytes_to_upload == 0
        assert tracker.total_files_uploaded == 0
        assert tracker.total_files_skipped == 0

    def test_init_with_callback(self):
        """Test initialization with callback."""
        callback = MagicMock()
        tracker = SyncProgressTracker(callback=callback)
        assert tracker.callback == callback

    def test_reset(self):
        """Test reset method clears all counters."""
        tracker = SyncProgressTracker()
        tracker.total_bytes_uploaded = 1000
        tracker.total_bytes_to_upload = 2000
        tracker.total_files_uploaded = 10
        tracker.total_files_skipped = 5
        tracker._file_bytes = {"file1": 100}
        tracker._file_totals = {"file1": 200}
        tracker._current_folder = "test"
        tracker._folder_files_total = 5
        tracker._folder_files_uploaded = 3
        tracker._folder_bytes_total = 1000
        tracker._folder_bytes_uploaded = 500

        tracker.reset()

        assert tracker.total_bytes_uploaded == 0
        assert tracker.total_bytes_to_upload == 0
        assert tracker.total_files_uploaded == 0
        assert tracker.total_files_skipped == 0
        assert len(tracker._file_bytes) == 0
        assert len(tracker._file_totals) == 0
        assert tracker._current_folder == ""
        assert tracker._folder_files_total == 0
        assert tracker._folder_files_uploaded == 0
        assert tracker._folder_bytes_total == 0
        assert tracker._folder_bytes_uploaded == 0

    def test_add_bytes_to_upload(self):
        """Test adding bytes to total."""
        tracker = SyncProgressTracker()
        tracker.add_bytes_to_upload(1000)
        assert tracker.total_bytes_to_upload == 1000
        tracker.add_bytes_to_upload(500)
        assert tracker.total_bytes_to_upload == 1500

    def test_on_scan_dir_start_no_callback(self):
        """Test scan dir start without callback."""
        tracker = SyncProgressTracker()
        # Should not raise exception
        tracker.on_scan_dir_start("test/dir")

    def test_on_scan_dir_start_with_callback(self):
        """Test scan dir start with callback."""
        callback = MagicMock()
        tracker = SyncProgressTracker(callback=callback)
        tracker.on_scan_dir_start("test/dir")

        callback.assert_called_once()
        info = callback.call_args[0][0]
        assert info.event == SyncProgressEvent.SCAN_DIR_START
        assert info.directory == "test/dir"

    def test_on_scan_dir_complete_no_callback(self):
        """Test scan dir complete without callback."""
        tracker = SyncProgressTracker()
        # Should not raise exception
        tracker.on_scan_dir_complete("test/dir", 10, 5)

    def test_on_scan_dir_complete_with_callback(self):
        """Test scan dir complete with callback."""
        callback = MagicMock()
        tracker = SyncProgressTracker(callback=callback)
        tracker.on_scan_dir_complete("test/dir", 10, 5)

        callback.assert_called_once()
        info = callback.call_args[0][0]
        assert info.event == SyncProgressEvent.SCAN_DIR_COMPLETE
        assert info.directory == "test/dir"
        assert info.files_in_batch == 10

    def test_on_upload_batch_start(self):
        """Test upload batch start."""
        callback = MagicMock()
        tracker = SyncProgressTracker(callback=callback)
        tracker.on_upload_batch_start("test/dir", 5, 10000)

        assert tracker.total_bytes_to_upload == 10000
        assert tracker._current_folder == "test/dir"
        assert tracker._folder_files_total == 5
        assert tracker._folder_bytes_total == 10000

        callback.assert_called_once()
        info = callback.call_args[0][0]
        assert info.event == SyncProgressEvent.UPLOAD_BATCH_START
        assert info.directory == "test/dir"
        assert info.files_in_batch == 5
        assert info.folder_files_total == 5
        assert info.folder_bytes_total == 10000

    def test_on_upload_file_start(self):
        """Test upload file start."""
        callback = MagicMock()
        tracker = SyncProgressTracker(callback=callback)
        tracker.on_upload_file_start("test/file.txt", 1024)

        assert tracker._file_bytes["test/file.txt"] == 0
        assert tracker._file_totals["test/file.txt"] == 1024

        callback.assert_called_once()
        info = callback.call_args[0][0]
        assert info.event == SyncProgressEvent.UPLOAD_FILE_START
        assert info.file_path == "test/file.txt"
        assert info.current_file_total == 1024

    def test_on_upload_file_progress(self):
        """Test upload file progress."""
        callback = MagicMock()
        tracker = SyncProgressTracker(callback=callback)
        tracker.on_upload_batch_start("test/dir", 1, 1024)
        callback.reset_mock()

        tracker.on_upload_file_start("test/file.txt", 1024)
        callback.reset_mock()

        # First progress update
        tracker.on_upload_file_progress("test/file.txt", 512, 1024)
        assert tracker.total_bytes_uploaded == 512
        assert tracker._folder_bytes_uploaded == 512
        assert tracker._file_bytes["test/file.txt"] == 512

        info = callback.call_args[0][0]
        assert info.event == SyncProgressEvent.UPLOAD_FILE_PROGRESS
        assert info.file_path == "test/file.txt"
        assert info.current_file_bytes == 512
        assert info.current_file_total == 1024
        assert info.bytes_uploaded == 512

        # Second progress update
        callback.reset_mock()
        tracker.on_upload_file_progress("test/file.txt", 1024, 1024)
        assert tracker.total_bytes_uploaded == 1024
        assert tracker._folder_bytes_uploaded == 1024
        assert tracker._file_bytes["test/file.txt"] == 1024

    def test_on_upload_file_complete(self):
        """Test upload file complete."""
        callback = MagicMock()
        tracker = SyncProgressTracker(callback=callback)
        tracker.on_upload_batch_start("test/dir", 1, 1024)
        tracker.on_upload_file_start("test/file.txt", 1024)
        tracker.on_upload_file_progress("test/file.txt", 1024, 1024)
        callback.reset_mock()

        tracker.on_upload_file_complete("test/file.txt")

        assert tracker.total_files_uploaded == 1
        assert tracker._folder_files_uploaded == 1
        assert "test/file.txt" not in tracker._file_bytes
        assert "test/file.txt" not in tracker._file_totals

        callback.assert_called_once()
        info = callback.call_args[0][0]
        assert info.event == SyncProgressEvent.UPLOAD_FILE_COMPLETE
        assert info.file_path == "test/file.txt"
        assert info.files_uploaded == 1

    def test_on_upload_file_error(self):
        """Test upload file error."""
        callback = MagicMock()
        tracker = SyncProgressTracker(callback=callback)
        tracker.on_upload_batch_start("test/dir", 1, 1024)
        tracker.on_upload_file_start("test/file.txt", 1024)
        tracker.on_upload_file_progress("test/file.txt", 512, 1024)

        # Verify bytes were tracked
        assert tracker.total_bytes_uploaded == 512
        callback.reset_mock()

        # Should rollback uploaded bytes
        tracker.on_upload_file_error("test/file.txt", "Upload failed")

        assert tracker.total_bytes_uploaded == 0  # Rolled back
        assert "test/file.txt" not in tracker._file_bytes
        assert "test/file.txt" not in tracker._file_totals

        callback.assert_called_once()
        info = callback.call_args[0][0]
        assert info.event == SyncProgressEvent.UPLOAD_FILE_ERROR
        assert info.file_path == "test/file.txt"
        assert info.error_message == "Upload failed"

    def test_on_files_skipped(self):
        """Test files skipped tracking."""
        tracker = SyncProgressTracker()
        tracker.on_files_skipped(5)
        assert tracker.total_files_skipped == 5
        tracker.on_files_skipped(3)
        assert tracker.total_files_skipped == 8

    def test_on_upload_batch_complete(self):
        """Test upload batch complete."""
        callback = MagicMock()
        tracker = SyncProgressTracker(callback=callback)
        tracker.on_upload_batch_start("test/dir", 2, 2048)
        tracker.on_upload_file_start("file1.txt", 1024)
        tracker.on_upload_file_progress("file1.txt", 1024, 1024)
        tracker.on_upload_file_complete("file1.txt")
        tracker.on_upload_file_start("file2.txt", 1024)
        tracker.on_upload_file_progress("file2.txt", 1024, 1024)
        tracker.on_upload_file_complete("file2.txt")
        callback.reset_mock()

        tracker.on_upload_batch_complete("test/dir", 2)

        callback.assert_called_once()
        info = callback.call_args[0][0]
        assert info.event == SyncProgressEvent.UPLOAD_BATCH_COMPLETE
        assert info.directory == "test/dir"
        assert info.files_in_batch == 2
        assert info.files_uploaded == 2
        assert info.folder_files_uploaded == 2
        assert info.folder_files_total == 2

    def test_create_file_progress_callback(self):
        """Test creating file progress callback."""
        callback = MagicMock()
        tracker = SyncProgressTracker(callback=callback)
        tracker.on_upload_batch_start("test/dir", 1, 1024)
        tracker.on_upload_file_start("test/file.txt", 1024)
        callback.reset_mock()

        file_callback = tracker.create_file_progress_callback("test/file.txt")

        # Call the file callback
        file_callback(512, 1024)

        # Should have triggered progress callback
        callback.assert_called_once()
        info = callback.call_args[0][0]
        assert info.event == SyncProgressEvent.UPLOAD_FILE_PROGRESS
        assert info.file_path == "test/file.txt"
        assert info.current_file_bytes == 512
        assert info.current_file_total == 1024

    def test_get_stats(self):
        """Test getting current statistics."""
        tracker = SyncProgressTracker()
        tracker.total_files_uploaded = 10
        tracker.total_files_skipped = 5
        tracker.total_bytes_uploaded = 10240
        tracker.total_bytes_to_upload = 20480

        stats = tracker.get_stats()

        assert stats["files_uploaded"] == 10
        assert stats["files_skipped"] == 5
        assert stats["bytes_uploaded"] == 10240
        assert stats["bytes_total"] == 20480

    def test_thread_safety(self):
        """Test that tracker is thread-safe."""
        tracker = SyncProgressTracker()
        tracker.on_upload_batch_start("test", 100, 100000)

        errors = []

        def upload_file(file_num):
            try:
                file_path = f"file{file_num}.txt"
                tracker.on_upload_file_start(file_path, 1000)
                for i in range(10):
                    tracker.on_upload_file_progress(file_path, i * 100, 1000)
                tracker.on_upload_file_complete(file_path)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(10):
            t = threading.Thread(target=upload_file, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        assert tracker.total_files_uploaded == 10

    def test_reset_folder_stats(self):
        """Test that folder stats are reset when starting new batch."""
        callback = MagicMock()
        tracker = SyncProgressTracker(callback=callback)

        # First batch
        tracker.on_upload_batch_start("dir1", 1, 1000)
        tracker.on_upload_file_start("file1.txt", 1000)
        tracker.on_upload_file_progress("file1.txt", 1000, 1000)
        tracker.on_upload_file_complete("file1.txt")

        # Second batch - folder stats should reset
        callback.reset_mock()
        tracker.on_upload_batch_start("dir2", 1, 500)

        info = callback.call_args[0][0]
        assert info.folder_files_uploaded == 0
        assert info.folder_files_total == 1
        assert info.folder_bytes_uploaded == 0
        assert info.folder_bytes_total == 500
        # But global stats should persist
        assert info.files_uploaded == 1
        assert info.bytes_uploaded == 1000
