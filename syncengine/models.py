"""Data models for syncengine.

This module provides generic data structures used by the sync engine.
These models are cloud-agnostic and can work with any storage provider.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FileEntry:
    """Generic file entry representing a remote file or folder.

    This is a concrete implementation of the FileEntryProtocol that can
    be used by cloud service implementations or for testing.

    Attributes:
        id: Unique identifier for the entry (persists across renames)
        type: Entry type - "file" or "folder"
        file_size: Size in bytes (0 for folders)
        hash: Content hash (e.g., MD5) for integrity verification
        name: File or folder name
        updated_at: ISO timestamp of last modification (optional)
        parent_id: Parent folder ID (optional)
    """

    id: int
    type: str
    name: str
    file_size: int = 0
    hash: str = ""
    updated_at: Optional[str] = None
    parent_id: Optional[int] = None

    def __post_init__(self) -> None:
        """Validate entry type."""
        if self.type not in ("file", "folder"):
            raise ValueError(
                f"Invalid entry type: {self.type}. Must be 'file' or 'folder'"
            )

    @property
    def is_file(self) -> bool:
        """Check if this entry is a file."""
        return self.type == "file"

    @property
    def is_folder(self) -> bool:
        """Check if this entry is a folder."""
        return self.type == "folder"


@dataclass
class SyncConfig:
    """Configuration for sync operations.

    This allows customizing various aspects of sync behavior including
    file names, directories, and operational parameters.

    Attributes:
        ignore_file_name: Name of the ignore file (default: ".syncignore")
        local_trash_dir_name: Name of local trash directory
        state_dir_name: Name of state directory under ~/.config/
        app_name: Application name (used in paths and logging)
    """

    ignore_file_name: str = ".syncignore"
    local_trash_dir_name: str = ".syncengine.trash.source"
    state_dir_name: str = "syncengine"
    app_name: str = "syncengine"

    def __post_init__(self) -> None:
        """Validate configuration."""
        if not self.ignore_file_name:
            raise ValueError("ignore_file_name cannot be empty")
        if not self.local_trash_dir_name:
            raise ValueError("local_trash_dir_name cannot be empty")
        if not self.state_dir_name:
            raise ValueError("state_dir_name cannot be empty")
        if not self.app_name:
            raise ValueError("app_name cannot be empty")
