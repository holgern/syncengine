"""Unit tests for sync pairs."""

from pathlib import Path

import pytest

from syncengine.modes import SyncMode
from syncengine.pair import SyncPair


class TestSyncPair:
    """Tests for SyncPair class."""

    def test_create_sync_pair(self):
        """Test creating a basic sync pair."""
        pair = SyncPair(
            source=Path("/home/user/Documents"),
            destination="/Documents",
            sync_mode=SyncMode.TWO_WAY,
        )

        assert pair.source == Path("/home/user/Documents")
        assert (
            pair.destination == "Documents"
        )  # Normalized without leading/trailing slashes
        assert pair.sync_mode == SyncMode.TWO_WAY
        assert pair.alias is None
        assert pair.storage_id == 0

    def test_sync_pair_with_options(self):
        """Test creating sync pair with all options."""
        pair = SyncPair(
            source=Path("/home/user/Documents"),
            destination="/Documents",
            sync_mode=SyncMode.SOURCE_TO_DESTINATION,
            alias="documents",
            disable_source_trash=True,
            ignore=["*.log", "*.tmp"],
            exclude_dot_files=True,
            storage_id=5,
        )

        assert pair.alias == "documents"
        assert pair.disable_source_trash is True
        assert pair.ignore == ["*.log", "*.tmp"]
        assert pair.exclude_dot_files is True
        assert pair.storage_id == 5

    def test_sync_pair_normalization(self):
        """Test that paths are normalized."""
        pair = SyncPair(
            source="/home/user/Documents",  # String converted to Path
            destination="/Documents/",  # Trailing slash removed
            sync_mode="twoWay",  # String converted to SyncMode
        )

        assert isinstance(pair.source, Path)
        assert pair.destination == "Documents"
        assert pair.sync_mode == SyncMode.TWO_WAY

    def test_from_dict(self):
        """Test creating sync pair from dictionary."""
        data = {
            "source": "/home/user/Documents",
            "destination": "/Documents",
            "syncMode": "twoWay",
            "alias": "documents",
            "disableSourceTrash": True,
            "ignore": ["*.log"],
            "excludeDotFiles": True,
            "storageId": 5,
        }

        pair = SyncPair.from_dict(data)

        assert pair.source == Path("/home/user/Documents")
        assert pair.destination == "Documents"
        assert pair.sync_mode == SyncMode.TWO_WAY
        assert pair.alias == "documents"
        assert pair.disable_source_trash is True
        assert pair.ignore == ["*.log"]
        assert pair.exclude_dot_files is True
        assert pair.storage_id == 5

    def test_from_dict_minimal(self):
        """Test creating sync pair from dictionary with minimal fields."""
        data = {
            "source": "/home/user/Documents",
            "destination": "/Documents",
            "syncMode": "twoWay",
        }

        pair = SyncPair.from_dict(data)

        assert pair.source == Path("/home/user/Documents")
        assert pair.destination == "Documents"
        assert pair.sync_mode == SyncMode.TWO_WAY
        assert pair.alias is None
        assert pair.disable_source_trash is False
        assert pair.ignore == []
        assert pair.exclude_dot_files is False
        assert pair.storage_id == 0

    def test_from_dict_missing_required_field(self):
        """Test that missing required fields raise ValueError."""
        data = {
            "source": "/home/user/Documents",
            # Missing destination and syncMode
        }

        with pytest.raises(ValueError, match="Missing required fields"):
            SyncPair.from_dict(data)

    def test_to_dict(self):
        """Test converting sync pair to dictionary."""
        pair = SyncPair(
            source=Path("/home/user/Documents"),
            destination="/Documents",
            sync_mode=SyncMode.TWO_WAY,
            alias="documents",
            disable_source_trash=True,
            ignore=["*.log"],
            exclude_dot_files=True,
            storage_id=5,
        )

        data = pair.to_dict()

        assert data == {
            "source": "/home/user/Documents",
            "destination": "Documents",
            "syncMode": "twoWay",
            "alias": "documents",
            "disableSourceTrash": True,
            "ignore": ["*.log"],
            "excludeDotFiles": True,
            "storageId": 5,
            "parentId": None,
        }

    def test_parse_literal_simple(self):
        """Test parsing simple literal sync pair."""
        pair = SyncPair.parse_literal("/home/user/docs:/Documents")

        assert pair.source == Path("/home/user/docs")
        assert pair.destination == "Documents"
        assert pair.sync_mode == SyncMode.TWO_WAY  # Default

    def test_parse_literal_with_mode(self):
        """Test parsing literal sync pair with mode."""
        pair = SyncPair.parse_literal("/home/user/docs:sourceToDestination:/Documents")

        assert pair.source == Path("/home/user/docs")
        assert pair.destination == "Documents"
        assert pair.sync_mode == SyncMode.SOURCE_TO_DESTINATION

    def test_parse_literal_with_abbreviation(self):
        """Test parsing literal sync pair with abbreviated mode."""
        pair = SyncPair.parse_literal("/home/user/docs:std:/Documents")

        assert pair.source == Path("/home/user/docs")
        assert pair.destination == "Documents"
        assert pair.sync_mode == SyncMode.SOURCE_TO_DESTINATION

    def test_parse_literal_invalid_format(self):
        """Test that invalid literal format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid sync pair literal"):
            SyncPair.parse_literal("invalid")

        with pytest.raises(ValueError, match="Invalid sync pair literal"):
            SyncPair.parse_literal("too:many:colons:here")

    def test_parse_literal_empty_paths(self):
        """Test that empty paths raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            SyncPair.parse_literal(":/Documents")

        with pytest.raises(ValueError, match="cannot be empty"):
            SyncPair.parse_literal("/home/user/docs:")

    def test_str_representation(self):
        """Test string representation."""
        pair = SyncPair(
            source=Path("/home/user/docs"),
            destination="/Documents",
            sync_mode=SyncMode.TWO_WAY,
        )

        assert "twoWay" in str(pair)
        assert "/home/user/docs" in str(pair)
        assert "Documents" in str(pair)

    def test_str_representation_with_alias(self):
        """Test string representation with alias."""
        pair = SyncPair(
            source=Path("/home/user/docs"),
            destination="/Documents",
            sync_mode=SyncMode.TWO_WAY,
            alias="documents",
        )

        result = str(pair)
        assert "documents" in result

    def test_repr(self):
        """Test repr representation."""
        pair = SyncPair(
            source=Path("/home/user/docs"),
            destination="/Documents",
            sync_mode=SyncMode.TWO_WAY,
        )

        result = repr(pair)
        assert "SyncPair" in result
        assert "source=" in result
        assert "destination=" in result
        assert "sync_mode=" in result


class TestSyncPairLiteralParsing:
    """Comprehensive tests for literal sync pair parsing with all 5 sync modes."""

    def test_parse_literal_two_way_shorthand(self):
        """Test parsing two-way sync with shorthand notation."""
        pair = SyncPair.parse_literal("./source:/destination")
        assert str(pair.source) == "source"
        assert pair.destination == "destination"
        assert pair.sync_mode == SyncMode.TWO_WAY

    def test_parse_literal_two_way_full_name(self):
        """Test parsing two-way sync with full mode name."""
        pair = SyncPair.parse_literal("./source:twoWay:/destination")
        assert str(pair.source) == "source"
        assert pair.destination == "destination"
        assert pair.sync_mode == SyncMode.TWO_WAY

    def test_parse_literal_two_way_abbreviation(self):
        """Test parsing two-way sync with abbreviation."""
        pair = SyncPair.parse_literal("./source:tw:/destination")
        assert str(pair.source) == "source"
        assert pair.destination == "destination"
        assert pair.sync_mode == SyncMode.TWO_WAY

    def test_parse_literal_source_to_destination_full_name(self):
        """Test parsing source-to-destination sync with full mode name."""
        pair = SyncPair.parse_literal("./source:sourceToDestination:/destination")
        assert str(pair.source) == "source"
        assert pair.destination == "destination"
        assert pair.sync_mode == SyncMode.SOURCE_TO_DESTINATION

    def test_parse_literal_source_to_destination_abbreviation(self):
        """Test parsing source-to-destination sync with abbreviation."""
        pair = SyncPair.parse_literal("./source:std:/destination")
        assert str(pair.source) == "source"
        assert pair.destination == "destination"
        assert pair.sync_mode == SyncMode.SOURCE_TO_DESTINATION

    def test_parse_literal_source_backup_full_name(self):
        """Test parsing source backup sync with full mode name."""
        pair = SyncPair.parse_literal("./source:sourceBackup:/destination")
        assert str(pair.source) == "source"
        assert pair.destination == "destination"
        assert pair.sync_mode == SyncMode.SOURCE_BACKUP

    def test_parse_literal_source_backup_abbreviation(self):
        """Test parsing source backup sync with abbreviation."""
        pair = SyncPair.parse_literal("./source:sb:/destination")
        assert str(pair.source) == "source"
        assert pair.destination == "destination"
        assert pair.sync_mode == SyncMode.SOURCE_BACKUP

    def test_parse_literal_destination_to_source_full_name(self):
        """Test parsing destination-to-source sync with full mode name."""
        pair = SyncPair.parse_literal("./source:destinationToSource:/destination")
        assert str(pair.source) == "source"
        assert pair.destination == "destination"
        assert pair.sync_mode == SyncMode.DESTINATION_TO_SOURCE

    def test_parse_literal_destination_to_source_abbreviation(self):
        """Test parsing destination-to-source sync with abbreviation."""
        pair = SyncPair.parse_literal("./source:dts:/destination")
        assert str(pair.source) == "source"
        assert pair.destination == "destination"
        assert pair.sync_mode == SyncMode.DESTINATION_TO_SOURCE

    def test_parse_literal_destination_backup_full_name(self):
        """Test parsing destination backup sync with full mode name."""
        pair = SyncPair.parse_literal("./source:destinationBackup:/destination")
        assert str(pair.source) == "source"
        assert pair.destination == "destination"
        assert pair.sync_mode == SyncMode.DESTINATION_BACKUP

    def test_parse_literal_destination_backup_abbreviation(self):
        """Test parsing destination backup sync with abbreviation."""
        pair = SyncPair.parse_literal("./source:db:/destination")
        assert str(pair.source) == "source"
        assert pair.destination == "destination"
        assert pair.sync_mode == SyncMode.DESTINATION_BACKUP


class TestSyncPairRootDestination:
    """Tests for syncing to destination root with destination='/'.

    When destination is set to '/' (root), files should sync directly to
    the destination root without creating a wrapper folder. For example:
    - source/subdir/file.txt -> /subdir/file.txt (NOT /source/subdir/file.txt)

    This is important for cross-platform compatibility, especially on Windows
    where path handling differs.
    """

    def test_destination_slash_normalized_to_empty_string(self):
        """Test that destination='/' is normalized to empty string."""
        pair = SyncPair(
            source=Path("/home/user/my_folder"),
            destination="/",
            sync_mode=SyncMode.SOURCE_TO_DESTINATION,
        )

        # "/" should be normalized to "" (empty string means root)
        assert pair.destination == ""

    def test_destination_slash_from_dict(self):
        """Test that destination='/' from dict config is normalized correctly."""
        data = {
            "source": "/home/user/my_folder",
            "destination": "/",
            "syncMode": "sourceToDestination",
        }

        pair = SyncPair.from_dict(data)

        assert pair.destination == ""

    def test_destination_empty_string_stays_empty(self):
        """Test that destination='' stays as empty string."""
        pair = SyncPair(
            source=Path("/home/user/my_folder"),
            destination="",
            sync_mode=SyncMode.SOURCE_TO_DESTINATION,
        )

        assert pair.destination == ""

    def test_destination_slash_with_windows_style_source_path(self):
        """Test destination='/' with Windows-style source path (forward slashes).

        On Windows, paths like C:/Users/test/sync should work correctly
        with destination='/'.
        """
        # Using forward slashes which work on all platforms
        pair = SyncPair(
            source=Path("C:/Users/test/sync"),
            destination="/",
            sync_mode=SyncMode.SOURCE_TO_DESTINATION,
        )

        assert pair.destination == ""
        # source.name should give the folder name
        assert pair.source.name == "sync"

    def test_destination_slash_to_dict_preserves_empty(self):
        """Test that to_dict preserves empty destination (root)."""
        pair = SyncPair(
            source=Path("/home/user/my_folder"),
            destination="/",
            sync_mode=SyncMode.SOURCE_TO_DESTINATION,
        )

        data = pair.to_dict()

        # Empty string in dict represents root
        assert data["destination"] == ""

    def test_destination_slash_parse_literal(self):
        """Test parsing literal with destination='/'."""
        pair = SyncPair.parse_literal("/home/user/docs:/")

        assert pair.source == Path("/home/user/docs")
        assert pair.destination == ""  # Normalized to empty
        assert pair.sync_mode == SyncMode.TWO_WAY

    def test_destination_slash_parse_literal_with_mode(self):
        """Test parsing literal with mode and destination='/'."""
        pair = SyncPair.parse_literal("/home/user/docs:std:/")

        assert pair.source == Path("/home/user/docs")
        assert pair.destination == ""  # Normalized to empty
        assert pair.sync_mode == SyncMode.SOURCE_TO_DESTINATION

    def test_syncing_to_root_detection(self):
        """Test that syncing_to_root can be detected from empty destination."""
        pair = SyncPair(
            source=Path("/home/user/my_folder"),
            destination="/",
            sync_mode=SyncMode.SOURCE_TO_DESTINATION,
        )

        # This is how the engine detects root syncing
        syncing_to_root = not pair.destination or pair.destination == "/"
        assert syncing_to_root is True

    def test_non_root_destination_not_detected_as_root(self):
        """Test that non-root destination paths are not detected as root."""
        pair = SyncPair(
            source=Path("/home/user/my_folder"),
            destination="/some/folder",
            sync_mode=SyncMode.SOURCE_TO_DESTINATION,
        )

        # After normalization, destination should be "some/folder"
        assert pair.destination == "some/folder"

        # This should NOT be detected as root
        syncing_to_root = not pair.destination or pair.destination == "/"
        assert syncing_to_root is False

    def test_destination_path_construction_for_root(self):
        """Test that file paths are constructed correctly when syncing to root.

        When destination is '/' (empty after normalization), the full destination path
        should be just the relative path without any prefix.
        """
        pair = SyncPair(
            source=Path("/home/user/my_folder"),
            destination="/",
            sync_mode=SyncMode.SOURCE_TO_DESTINATION,
        )

        # Simulate how engine constructs paths
        relative_path = "subdir/file.txt"
        if pair.destination:
            full_destination_path = f"{pair.destination}/{relative_path}"
        else:
            full_destination_path = relative_path

        # Should be just the relative path, NOT "my_folder/subdir/file.txt"
        assert full_destination_path == "subdir/file.txt"

    def test_destination_path_construction_for_named_folder(self):
        """Test file paths are constructed correctly for named destination."""
        pair = SyncPair(
            source=Path("/home/user/my_folder"),
            destination="/backup",
            sync_mode=SyncMode.SOURCE_TO_DESTINATION,
        )

        # Simulate how engine constructs paths
        relative_path = "subdir/file.txt"
        if pair.destination:
            full_destination_path = f"{pair.destination}/{relative_path}"
        else:
            full_destination_path = relative_path

        # Should include the destination folder prefix
        assert full_destination_path == "backup/subdir/file.txt"
