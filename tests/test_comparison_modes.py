"""Tests for ComparisonMode functionality.

This test suite verifies that each comparison mode correctly determines
whether files match or differ, and that the appropriate sync actions are taken.
"""

import hashlib
from unittest.mock import MagicMock

import pytest

from syncengine.comparator import FileComparator, SyncAction
from syncengine.models import ComparisonMode
from syncengine.modes import SyncMode
from syncengine.scanner import DestinationFile, SourceFile


class TestComparisonModeHashThenMtime:
    """Test HASH_THEN_MTIME mode (default behavior)."""

    def test_same_size_same_hash_skips(self, tmp_path):
        """Files with same size and hash should skip."""
        # Create source file
        source_file = tmp_path / "source.txt"
        source_file.write_text("test content")

        source = SourceFile.from_path(source_file, tmp_path)

        # Create mock destination with same hash
        dest_entry = MagicMock()
        dest_entry.id = 1
        dest_entry.hash = hashlib.md5(b"test content").hexdigest()
        dest_entry.file_size = 12
        dest_entry.updated_at = "2024-01-01T00:00:00Z"
        dest = DestinationFile(dest_entry, "source.txt")

        comparator = FileComparator(
            SyncMode.TWO_WAY, comparison_mode=ComparisonMode.HASH_THEN_MTIME
        )

        decision = comparator._compare_single_file(
            "source.txt", source, dest, None, None
        )

        assert decision.action == SyncAction.SKIP
        assert "identical" in decision.reason.lower()

    def test_same_size_different_hash_uploads(self, tmp_path):
        """Same size but different hash should upload (mtime decides direction)."""
        import time

        # Create source file with future mtime
        source_file = tmp_path / "source.txt"
        source_file.write_text("test content")
        # Set mtime to future to ensure source is newer
        future_time = time.time() + 10
        import os

        os.utime(source_file, (future_time, future_time))

        source = SourceFile.from_path(source_file, tmp_path)

        # Create mock destination with different hash but older time
        dest_entry = MagicMock()
        dest_entry.id = 1
        dest_entry.hash = "different_hash_value"
        dest_entry.file_size = 12  # Same size
        dest_entry.updated_at = "2024-01-01T00:00:00Z"  # Old time
        dest = DestinationFile(dest_entry, "source.txt")

        comparator = FileComparator(
            SyncMode.TWO_WAY, comparison_mode=ComparisonMode.HASH_THEN_MTIME
        )

        decision = comparator._compare_single_file(
            "source.txt", source, dest, None, None
        )

        # HASH_THEN_MTIME: Hash detects difference, mtime determines direction
        assert decision.action == SyncAction.UPLOAD
        assert "newer" in decision.reason.lower()

    def test_different_size_newer_source_uploads(self, tmp_path):
        """HASH_THEN_MTIME: Different sizes, mtime determines direction."""
        import time

        # Create source file with future mtime
        source_file = tmp_path / "source.txt"
        source_file.write_text("new content")
        # Set mtime to future
        future_time = time.time() + 10
        import os

        os.utime(source_file, (future_time, future_time))

        source = SourceFile.from_path(source_file, tmp_path)

        # Create mock destination with older time
        dest_entry = MagicMock()
        dest_entry.id = 1
        dest_entry.hash = "old_hash"
        dest_entry.file_size = 100  # Different size
        dest_entry.updated_at = "2024-01-01T00:00:00Z"
        dest = DestinationFile(dest_entry, "source.txt")

        comparator = FileComparator(
            SyncMode.TWO_WAY, comparison_mode=ComparisonMode.HASH_THEN_MTIME
        )

        decision = comparator._compare_single_file(
            "source.txt", source, dest, None, None
        )

        assert decision.action == SyncAction.UPLOAD
        assert "newer" in decision.reason.lower()


class TestComparisonModeSizeOnly:
    """Test SIZE_ONLY mode (for encrypted vaults)."""

    def test_same_size_different_hash_skips(self, tmp_path):
        """SIZE_ONLY: Files with same size should skip, even if hash differs."""
        # Create source file
        source_file = tmp_path / "source.txt"
        source_file.write_text("test content")

        source = SourceFile.from_path(source_file, tmp_path)

        # Create mock destination with same size but different hash
        dest_entry = MagicMock()
        dest_entry.id = 1
        dest_entry.hash = "different_hash_value"  # Different hash
        dest_entry.file_size = 12  # Same size
        dest_entry.updated_at = "2024-01-01T00:00:00Z"
        dest = DestinationFile(dest_entry, "source.txt")

        comparator = FileComparator(
            SyncMode.TWO_WAY, comparison_mode=ComparisonMode.SIZE_ONLY
        )

        decision = comparator._compare_single_file(
            "source.txt", source, dest, None, None
        )

        assert decision.action == SyncAction.SKIP
        assert "same size" in decision.reason.lower()

    def test_different_size_two_way_conflict(self, tmp_path):
        """SIZE_ONLY: Different sizes in TWO_WAY mode cause CONFLICT."""
        import time

        # Create source file with future mtime
        source_file = tmp_path / "source.txt"
        source_file.write_text("new content")
        # Set mtime to future
        future_time = time.time() + 10
        import os

        os.utime(source_file, (future_time, future_time))

        source = SourceFile.from_path(source_file, tmp_path)

        # Create mock destination with different size
        dest_entry = MagicMock()
        dest_entry.id = 1
        dest_entry.hash = "any_hash"
        dest_entry.file_size = 100  # Different size
        dest_entry.updated_at = "2024-01-01T00:00:00Z"
        dest = DestinationFile(dest_entry, "source.txt")

        comparator = FileComparator(
            SyncMode.TWO_WAY, comparison_mode=ComparisonMode.SIZE_ONLY
        )

        decision = comparator._compare_single_file(
            "source.txt", source, dest, None, None
        )

        # SIZE_ONLY mode cannot use mtime, so TWO_WAY sync results in CONFLICT
        assert decision.action == SyncAction.CONFLICT
        assert "cannot determine newer" in decision.reason.lower()

    def test_different_size_source_to_destination_uploads(self, tmp_path):
        """SIZE_ONLY: SOURCE_TO_DESTINATION mode uploads (prefers source)."""
        source_file = tmp_path / "source.txt"
        source_file.write_text("new content")

        source = SourceFile.from_path(source_file, tmp_path)

        # Create mock destination with different size
        dest_entry = MagicMock()
        dest_entry.id = 1
        dest_entry.hash = "any_hash"
        dest_entry.file_size = 100  # Different size
        dest_entry.updated_at = "2024-01-01T00:00:00Z"
        dest = DestinationFile(dest_entry, "source.txt")

        comparator = FileComparator(
            SyncMode.SOURCE_TO_DESTINATION, comparison_mode=ComparisonMode.SIZE_ONLY
        )

        decision = comparator._compare_single_file(
            "source.txt", source, dest, None, None
        )

        # One-way sync prefers source
        assert decision.action == SyncAction.UPLOAD
        assert "prefers source" in decision.reason.lower()

    def test_different_size_destination_to_source_downloads(self, tmp_path):
        """SIZE_ONLY: DESTINATION_TO_SOURCE mode downloads (prefers dest)."""
        source_file = tmp_path / "source.txt"
        source_file.write_text("new content")

        source = SourceFile.from_path(source_file, tmp_path)

        # Create mock destination with different size
        dest_entry = MagicMock()
        dest_entry.id = 1
        dest_entry.hash = "any_hash"
        dest_entry.file_size = 100  # Different size
        dest_entry.updated_at = "2024-01-01T00:00:00Z"
        dest = DestinationFile(dest_entry, "source.txt")

        comparator = FileComparator(
            SyncMode.DESTINATION_TO_SOURCE, comparison_mode=ComparisonMode.SIZE_ONLY
        )

        decision = comparator._compare_single_file(
            "source.txt", source, dest, None, None
        )

        # One-way sync prefers destination
        assert decision.action == SyncAction.DOWNLOAD
        assert "prefers destination" in decision.reason.lower()

    def test_same_size_empty_hash_skips(self, tmp_path):
        """SIZE_ONLY: Works even when destination hash is empty."""
        # Create source file
        source_file = tmp_path / "source.txt"
        source_file.write_text("test content")

        source = SourceFile.from_path(source_file, tmp_path)

        # Create mock destination with empty hash
        dest_entry = MagicMock()
        dest_entry.id = 1
        dest_entry.hash = ""  # Empty hash (encrypted vault scenario)
        dest_entry.file_size = 12  # Same size
        dest_entry.updated_at = "2024-01-01T00:00:00Z"
        dest = DestinationFile(dest_entry, "source.txt")

        comparator = FileComparator(
            SyncMode.TWO_WAY, comparison_mode=ComparisonMode.SIZE_ONLY
        )

        decision = comparator._compare_single_file(
            "source.txt", source, dest, None, None
        )

        assert decision.action == SyncAction.SKIP
        assert "same size" in decision.reason.lower()


class TestComparisonModeSizeAndMtime:
    """Test SIZE_AND_MTIME mode."""

    def test_same_size_same_mtime_skips(self, tmp_path):
        """SIZE_AND_MTIME: Files with same size and mtime should skip."""

        # Create source file
        source_file = tmp_path / "source.txt"
        source_file.write_text("test content")

        # Get current mtime
        current_mtime = source_file.stat().st_mtime

        source = SourceFile.from_path(source_file, tmp_path)

        # Create mock destination with same size and mtime
        from datetime import datetime

        dest_entry = MagicMock()
        dest_entry.id = 1
        dest_entry.hash = "any_hash"
        dest_entry.file_size = 12
        dest_entry.updated_at = datetime.utcfromtimestamp(current_mtime).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        dest = DestinationFile(dest_entry, "source.txt")

        comparator = FileComparator(
            SyncMode.TWO_WAY, comparison_mode=ComparisonMode.SIZE_AND_MTIME
        )

        decision = comparator._compare_single_file(
            "source.txt", source, dest, None, None
        )

        assert decision.action == SyncAction.SKIP
        assert "same size and mtime" in decision.reason.lower()

    def test_same_size_different_mtime_uploads(self, tmp_path):
        """SIZE_AND_MTIME: Different mtime means no match, uses mtime for direction."""
        import time

        # Create source file with future mtime
        source_file = tmp_path / "source.txt"
        source_file.write_text("test content")
        future_time = time.time() + 10
        import os

        os.utime(source_file, (future_time, future_time))

        source = SourceFile.from_path(source_file, tmp_path)

        # Create mock destination with old mtime
        dest_entry = MagicMock()
        dest_entry.id = 1
        dest_entry.hash = "any_hash"
        dest_entry.file_size = 12  # Same size
        dest_entry.updated_at = "2024-01-01T00:00:00Z"  # Old time
        dest = DestinationFile(dest_entry, "source.txt")

        comparator = FileComparator(
            SyncMode.TWO_WAY, comparison_mode=ComparisonMode.SIZE_AND_MTIME
        )

        decision = comparator._compare_single_file(
            "source.txt", source, dest, None, None
        )

        # SIZE_AND_MTIME: Detects mtime difference, then uses mtime to decide direction
        assert decision.action == SyncAction.UPLOAD
        assert "newer" in decision.reason.lower()

    def test_different_size_uploads(self, tmp_path):
        """SIZE_AND_MTIME: Different sizes, mtime determines direction."""
        # Create source file
        source_file = tmp_path / "source.txt"
        source_file.write_text("test content")

        source = SourceFile.from_path(source_file, tmp_path)

        # Create mock destination with different size
        dest_entry = MagicMock()
        dest_entry.id = 1
        dest_entry.hash = "any_hash"
        dest_entry.file_size = 100  # Different size
        dest_entry.updated_at = "2024-01-01T00:00:00Z"
        dest = DestinationFile(dest_entry, "source.txt")

        comparator = FileComparator(
            SyncMode.TWO_WAY, comparison_mode=ComparisonMode.SIZE_AND_MTIME
        )

        decision = comparator._compare_single_file(
            "source.txt", source, dest, None, None
        )

        assert decision.action == SyncAction.UPLOAD


class TestComparisonModeMtimeOnly:
    """Test MTIME_ONLY mode."""

    def test_same_mtime_different_size_skips(self, tmp_path):
        """MTIME_ONLY: Files with same mtime should skip even if size differs."""
        # Create source file
        source_file = tmp_path / "source.txt"
        source_file.write_text("test content")

        current_mtime = source_file.stat().st_mtime

        source = SourceFile.from_path(source_file, tmp_path)

        # Create mock destination with same mtime but different size
        from datetime import datetime

        dest_entry = MagicMock()
        dest_entry.id = 1
        dest_entry.hash = "any_hash"
        dest_entry.file_size = 999  # Different size
        dest_entry.updated_at = datetime.utcfromtimestamp(current_mtime).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        dest = DestinationFile(dest_entry, "source.txt")

        comparator = FileComparator(
            SyncMode.TWO_WAY, comparison_mode=ComparisonMode.MTIME_ONLY
        )

        decision = comparator._compare_single_file(
            "source.txt", source, dest, None, None
        )

        assert decision.action == SyncAction.SKIP
        assert "same mtime" in decision.reason.lower()

    def test_different_mtime_uploads(self, tmp_path):
        """MTIME_ONLY: Different mtime means no match, uses mtime for direction."""
        import time

        # Create source file with future mtime
        source_file = tmp_path / "source.txt"
        source_file.write_text("test content")
        future_time = time.time() + 10
        import os

        os.utime(source_file, (future_time, future_time))

        source = SourceFile.from_path(source_file, tmp_path)

        # Create mock destination with old mtime
        dest_entry = MagicMock()
        dest_entry.id = 1
        dest_entry.hash = "any_hash"
        dest_entry.file_size = 12
        dest_entry.updated_at = "2024-01-01T00:00:00Z"
        dest = DestinationFile(dest_entry, "source.txt")

        comparator = FileComparator(
            SyncMode.TWO_WAY, comparison_mode=ComparisonMode.MTIME_ONLY
        )

        decision = comparator._compare_single_file(
            "source.txt", source, dest, None, None
        )

        assert decision.action == SyncAction.UPLOAD

    def test_no_dest_mtime_fails(self, tmp_path):
        """MTIME_ONLY: Missing destination mtime should not match."""
        # Create source file
        source_file = tmp_path / "source.txt"
        source_file.write_text("test content")

        source = SourceFile.from_path(source_file, tmp_path)

        # Create mock destination without mtime
        dest_entry = MagicMock()
        dest_entry.id = 1
        dest_entry.hash = "any_hash"
        dest_entry.file_size = 12
        dest_entry.updated_at = None  # No mtime
        dest = DestinationFile(dest_entry, "source.txt")

        comparator = FileComparator(
            SyncMode.TWO_WAY, comparison_mode=ComparisonMode.MTIME_ONLY
        )

        decision = comparator._compare_single_file(
            "source.txt", source, dest, None, None
        )

        # Should upload because we can't compare mtime
        assert decision.action == SyncAction.UPLOAD


class TestComparisonModeHashOnly:
    """Test HASH_ONLY mode (strict)."""

    def test_same_hash_different_size_skips(self, tmp_path):
        """HASH_ONLY: Files with same hash should skip even if size differs."""
        # Create source file
        source_file = tmp_path / "source.txt"
        source_file.write_text("test content")

        source = SourceFile.from_path(source_file, tmp_path)

        # Create mock destination with same hash but different size
        dest_entry = MagicMock()
        dest_entry.id = 1
        dest_entry.hash = hashlib.md5(b"test content").hexdigest()
        dest_entry.file_size = 999  # Different size (shouldn't matter)
        dest_entry.updated_at = "2024-01-01T00:00:00Z"
        dest = DestinationFile(dest_entry, "source.txt")

        comparator = FileComparator(
            SyncMode.TWO_WAY, comparison_mode=ComparisonMode.HASH_ONLY
        )

        decision = comparator._compare_single_file(
            "source.txt", source, dest, None, None
        )

        assert decision.action == SyncAction.SKIP
        assert "same hash" in decision.reason.lower()

    def test_different_hash_two_way_conflict(self, tmp_path):
        """HASH_ONLY: Different hash in TWO_WAY mode causes CONFLICT."""
        import time

        # Create source file with future mtime
        source_file = tmp_path / "source.txt"
        source_file.write_text("test content")
        future_time = time.time() + 10
        import os

        os.utime(source_file, (future_time, future_time))

        source = SourceFile.from_path(source_file, tmp_path)

        # Create mock destination with different hash
        dest_entry = MagicMock()
        dest_entry.id = 1
        dest_entry.hash = "different_hash"
        dest_entry.file_size = 12
        dest_entry.updated_at = "2024-01-01T00:00:00Z"
        dest = DestinationFile(dest_entry, "source.txt")

        comparator = FileComparator(
            SyncMode.TWO_WAY, comparison_mode=ComparisonMode.HASH_ONLY
        )

        decision = comparator._compare_single_file(
            "source.txt", source, dest, None, None
        )

        # HASH_ONLY mode cannot use mtime, so TWO_WAY sync results in CONFLICT
        assert decision.action == SyncAction.CONFLICT
        assert "cannot determine newer" in decision.reason.lower()

    def test_different_hash_source_to_destination_uploads(self, tmp_path):
        """HASH_ONLY: SOURCE_TO_DESTINATION mode uploads (prefers source)."""
        source_file = tmp_path / "source.txt"
        source_file.write_text("test content")

        source = SourceFile.from_path(source_file, tmp_path)

        # Create mock destination with different hash
        dest_entry = MagicMock()
        dest_entry.id = 1
        dest_entry.hash = "different_hash"
        dest_entry.file_size = 12
        dest_entry.updated_at = "2024-01-01T00:00:00Z"
        dest = DestinationFile(dest_entry, "source.txt")

        comparator = FileComparator(
            SyncMode.SOURCE_TO_DESTINATION, comparison_mode=ComparisonMode.HASH_ONLY
        )

        decision = comparator._compare_single_file(
            "source.txt", source, dest, None, None
        )

        # One-way sync prefers source
        assert decision.action == SyncAction.UPLOAD
        assert "prefers source" in decision.reason.lower()

    def test_no_dest_hash_raises_error(self, tmp_path):
        """HASH_ONLY: Missing destination hash should raise error."""
        # Create source file
        source_file = tmp_path / "source.txt"
        source_file.write_text("test content")

        source = SourceFile.from_path(source_file, tmp_path)

        # Create mock destination without hash
        dest_entry = MagicMock()
        dest_entry.id = 1
        dest_entry.hash = ""  # Empty hash
        dest_entry.file_size = 12
        dest_entry.updated_at = "2024-01-01T00:00:00Z"
        dest = DestinationFile(dest_entry, "source.txt")

        comparator = FileComparator(
            SyncMode.TWO_WAY, comparison_mode=ComparisonMode.HASH_ONLY
        )

        with pytest.raises(
            ValueError, match="HASH_ONLY mode requires destination hash"
        ):
            comparator._compare_single_file("source.txt", source, dest, None, None)


class TestComparisonModeIntegration:
    """Integration tests for comparison modes with SyncEngine."""

    def test_size_only_mode_in_config(self, tmp_path):
        """Test that SIZE_ONLY mode can be configured in SyncConfig."""
        from syncengine.models import SyncConfig

        config = SyncConfig(comparison_mode=ComparisonMode.SIZE_ONLY)

        assert config.comparison_mode == ComparisonMode.SIZE_ONLY

    def test_default_comparison_mode(self):
        """Test that default comparison mode is HASH_THEN_MTIME."""
        from syncengine.models import SyncConfig

        config = SyncConfig()

        assert config.comparison_mode == ComparisonMode.HASH_THEN_MTIME

    def test_comparator_uses_config_mode(self):
        """Test that FileComparator respects the comparison_mode parameter."""
        comparator = FileComparator(
            SyncMode.TWO_WAY, comparison_mode=ComparisonMode.SIZE_ONLY
        )

        assert comparator.comparison_mode == ComparisonMode.SIZE_ONLY

    def test_comparator_default_mode(self):
        """Test that FileComparator defaults to HASH_THEN_MTIME."""
        comparator = FileComparator(SyncMode.TWO_WAY)

        assert comparator.comparison_mode == ComparisonMode.HASH_THEN_MTIME
