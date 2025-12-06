"""Unit tests for sync modes."""

import pytest

from syncengine.modes import SyncMode


class TestSyncMode:
    """Tests for SyncMode enum."""

    def test_sync_mode_values(self):
        """Test that all sync modes have correct values."""
        assert SyncMode.TWO_WAY.value == "twoWay"
        assert SyncMode.SOURCE_TO_DESTINATION.value == "sourceToDestination"
        assert SyncMode.SOURCE_BACKUP.value == "sourceBackup"
        assert SyncMode.DESTINATION_TO_SOURCE.value == "destinationToSource"
        assert SyncMode.DESTINATION_BACKUP.value == "destinationBackup"

    def test_from_string_full_names(self):
        """Test parsing full sync mode names."""
        assert SyncMode.from_string("twoWay") == SyncMode.TWO_WAY
        assert (
            SyncMode.from_string("sourceToDestination")
            == SyncMode.SOURCE_TO_DESTINATION
        )
        assert SyncMode.from_string("sourceBackup") == SyncMode.SOURCE_BACKUP
        assert (
            SyncMode.from_string("destinationToSource")
            == SyncMode.DESTINATION_TO_SOURCE
        )
        assert SyncMode.from_string("destinationBackup") == SyncMode.DESTINATION_BACKUP

    def test_from_string_abbreviations(self):
        """Test parsing abbreviated sync mode names."""
        assert SyncMode.from_string("tw") == SyncMode.TWO_WAY
        assert SyncMode.from_string("std") == SyncMode.SOURCE_TO_DESTINATION
        assert SyncMode.from_string("sb") == SyncMode.SOURCE_BACKUP
        assert SyncMode.from_string("dts") == SyncMode.DESTINATION_TO_SOURCE
        assert SyncMode.from_string("db") == SyncMode.DESTINATION_BACKUP

    def test_from_string_case_insensitive(self):
        """Test that parsing is case-insensitive."""
        assert SyncMode.from_string("TWOWAY") == SyncMode.TWO_WAY
        assert SyncMode.from_string("TW") == SyncMode.TWO_WAY
        assert (
            SyncMode.from_string("SourceToDestination")
            == SyncMode.SOURCE_TO_DESTINATION
        )

    def test_from_string_invalid(self):
        """Test that invalid mode strings raise ValueError."""
        with pytest.raises(ValueError, match="Invalid sync mode"):
            SyncMode.from_string("invalid")

    def test_allows_upload(self):
        """Test allows_upload property."""
        assert SyncMode.TWO_WAY.allows_upload is True
        assert SyncMode.SOURCE_TO_DESTINATION.allows_upload is True
        assert SyncMode.SOURCE_BACKUP.allows_upload is True
        assert SyncMode.DESTINATION_TO_SOURCE.allows_upload is False
        assert SyncMode.DESTINATION_BACKUP.allows_upload is False

    def test_allows_download(self):
        """Test allows_download property."""
        assert SyncMode.TWO_WAY.allows_download is True
        assert SyncMode.SOURCE_TO_DESTINATION.allows_download is False
        assert SyncMode.SOURCE_BACKUP.allows_download is False
        assert SyncMode.DESTINATION_TO_SOURCE.allows_download is True
        assert SyncMode.DESTINATION_BACKUP.allows_download is True

    def test_allows_source_delete(self):
        """Test allows_source_delete property."""
        assert SyncMode.TWO_WAY.allows_source_delete is True
        assert SyncMode.SOURCE_TO_DESTINATION.allows_source_delete is False
        assert SyncMode.SOURCE_BACKUP.allows_source_delete is False
        assert SyncMode.DESTINATION_TO_SOURCE.allows_source_delete is True
        assert SyncMode.DESTINATION_BACKUP.allows_source_delete is False

    def test_allows_destination_delete(self):
        """Test allows_destination_delete property."""
        assert SyncMode.TWO_WAY.allows_destination_delete is True
        assert SyncMode.SOURCE_TO_DESTINATION.allows_destination_delete is True
        assert SyncMode.SOURCE_BACKUP.allows_destination_delete is False
        assert SyncMode.DESTINATION_TO_SOURCE.allows_destination_delete is False
        assert SyncMode.DESTINATION_BACKUP.allows_destination_delete is False

    def test_is_bidirectional(self):
        """Test is_bidirectional property."""
        assert SyncMode.TWO_WAY.is_bidirectional is True
        assert SyncMode.SOURCE_TO_DESTINATION.is_bidirectional is False
        assert SyncMode.SOURCE_BACKUP.is_bidirectional is False
        assert SyncMode.DESTINATION_TO_SOURCE.is_bidirectional is False
        assert SyncMode.DESTINATION_BACKUP.is_bidirectional is False

    def test_str_representation(self):
        """Test string representation."""
        assert str(SyncMode.TWO_WAY) == "twoWay"
        assert str(SyncMode.SOURCE_TO_DESTINATION) == "sourceToDestination"
