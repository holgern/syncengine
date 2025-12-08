"""Tests for syncengine models."""

import pytest

from syncengine.models import FileEntry, SyncConfig


class TestFileEntry:
    """Test FileEntry model."""

    def test_create_file_entry(self):
        """Test creating a file entry."""
        entry = FileEntry(
            id=1,
            type="file",
            name="test.txt",
            file_size=1024,
            hash="abc123",
            updated_at="2024-01-01T00:00:00Z",
            parent_id=0,
        )
        assert entry.id == 1
        assert entry.type == "file"
        assert entry.name == "test.txt"
        assert entry.file_size == 1024
        assert entry.hash == "abc123"
        assert entry.updated_at == "2024-01-01T00:00:00Z"
        assert entry.parent_id == 0

    def test_create_folder_entry(self):
        """Test creating a folder entry."""
        entry = FileEntry(
            id=2,
            type="folder",
            name="documents",
            parent_id=0,
        )
        assert entry.id == 2
        assert entry.type == "folder"
        assert entry.name == "documents"
        assert entry.file_size == 0
        assert entry.hash == ""

    def test_invalid_type_raises_error(self):
        """Test that invalid entry type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid entry type: invalid"):
            FileEntry(
                id=1,
                type="invalid",
                name="test.txt",
            )

    def test_is_file_property(self):
        """Test is_file property."""
        file_entry = FileEntry(id=1, type="file", name="test.txt")
        folder_entry = FileEntry(id=2, type="folder", name="docs")

        assert file_entry.is_file is True
        assert folder_entry.is_file is False

    def test_is_folder_property(self):
        """Test is_folder property."""
        file_entry = FileEntry(id=1, type="file", name="test.txt")
        folder_entry = FileEntry(id=2, type="folder", name="docs")

        assert file_entry.is_folder is False
        assert folder_entry.is_folder is True


class TestSyncConfig:
    """Test SyncConfig model."""

    def test_default_config(self):
        """Test default configuration values."""
        config = SyncConfig()
        assert config.ignore_file_name == ".syncignore"
        assert config.local_trash_dir_name == ".syncengine.trash.source"
        assert config.state_dir_name == "syncengine"
        assert config.app_name == "syncengine"

    def test_custom_config(self):
        """Test custom configuration values."""
        config = SyncConfig(
            ignore_file_name=".customignore",
            local_trash_dir_name=".trash",
            state_dir_name="mystate",
            app_name="myapp",
        )
        assert config.ignore_file_name == ".customignore"
        assert config.local_trash_dir_name == ".trash"
        assert config.state_dir_name == "mystate"
        assert config.app_name == "myapp"

    def test_empty_ignore_file_name_raises_error(self):
        """Test that empty ignore_file_name raises ValueError."""
        with pytest.raises(ValueError, match="ignore_file_name cannot be empty"):
            SyncConfig(ignore_file_name="")

    def test_empty_local_trash_dir_name_raises_error(self):
        """Test that empty local_trash_dir_name raises ValueError."""
        with pytest.raises(ValueError, match="local_trash_dir_name cannot be empty"):
            SyncConfig(local_trash_dir_name="")

    def test_empty_state_dir_name_raises_error(self):
        """Test that empty state_dir_name raises ValueError."""
        with pytest.raises(ValueError, match="state_dir_name cannot be empty"):
            SyncConfig(state_dir_name="")

    def test_empty_app_name_raises_error(self):
        """Test that empty app_name raises ValueError."""
        with pytest.raises(ValueError, match="app_name cannot be empty"):
            SyncConfig(app_name="")
