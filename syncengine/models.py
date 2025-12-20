"""Data models for syncengine.

This module provides generic data structures used by the sync engine.
These models are cloud-agnostic and can work with any storage provider.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ComparisonMode(Enum):
    """File comparison strategies for sync operations.

    This enum defines how the sync engine determines whether files are
    identical or need to be synced. Different modes offer trade-offs between
    accuracy, performance, and compatibility with various storage backends.
    """

    HASH_THEN_MTIME = "hash_then_mtime"
    """Default behavior - most compatible.

    1. If both sides have content hash, compare hashes
    2. If hashes match, files are identical (skip sync)
    3. If hashes differ, files need sync
    4. If hashes unavailable, fall back to mtime + size comparison
    5. If hashes match but mtime differs, trust hash (no sync needed)

    Use when:
    - Remote storage provides content hashes (e.g., MD5)
    - You want the current default behavior
    - Maximum compatibility is needed
    """

    SIZE_ONLY = "size_only"
    """Compare only file size and name - fastest but least accurate.

    1. Skip hash computation entirely
    2. Skip mtime comparison
    3. Files considered identical if sizes match
    4. If sizes differ, use mtime to determine which is newer

    Use when:
    - Remote doesn't provide content hashes (e.g., encrypted vaults)
    - Hash computation is expensive or impossible
    - Mtime is unreliable (e.g., reflects upload time vs original mtime)
    - Fast sync is more important than accuracy
    - Files are unlikely to have same size with different content

    Warning:
    - TWO_WAY mode with SIZE_ONLY can miss content changes if size unchanged
    - Consider using SIZE_AND_MTIME for better safety
    """

    HASH_ONLY = "hash_only"
    """Compare only content hashes - most accurate but requires hashes.

    1. Require content hash on both sides
    2. Compare hashes to determine if files identical
    3. Ignore mtime differences completely
    4. Fail if hash unavailable

    Use when:
    - Content hash is always available
    - Mtime is unreliable (timezone issues, clock skew)
    - Need strict content verification
    - Performance of hash computation is acceptable

    Raises:
    - ValueError if hash is missing on either side
    """

    MTIME_ONLY = "mtime_only"
    """Compare only modification time - fast time-based sync.

    1. Skip hash computation entirely
    2. Compare only mtime (with 2-second tolerance)
    3. Files identical if mtime matches
    4. If mtime differs, newer file wins

    Use when:
    - Mtime is reliable and accurately reflects content changes
    - Hash computation is too expensive
    - Quick incremental sync is needed
    - Single-direction backup workflows

    Warning:
    - Same mtime but different size/content will be skipped
    - Clock skew between systems can cause issues
    """

    SIZE_AND_MTIME = "size_and_mtime"
    """Compare both size and mtime - balanced approach.

    1. Skip hash computation
    2. Files identical only if BOTH size AND mtime match
    3. If either differs, determine direction by mtime
    4. Safer than SIZE_ONLY for detecting changes

    Use when:
    - Want better safety than SIZE_ONLY
    - Hash computation too expensive
    - Mtime is reasonably reliable
    - Good balance of speed and accuracy needed

    Recommended for:
    - Encrypted vault sync where hash unavailable
    - Large file backups where hash is slow
    - TWO_WAY sync without content hashing
    """


@dataclass
class FileEntry:
    """Generic file entry representing a remote file or folder.

    This is a concrete implementation of the FileEntryProtocol that can
    be used by cloud service implementations or for testing.

    Attributes:
        id: Unique stable identifier for the entry (persists across renames).
            Used for file operations (download, delete, rename).
        type: Entry type - "file" or "folder"
        file_size: Size in bytes (0 for folders)
        hash: Content hash (e.g., MD5) for integrity verification (optional).
            Used for content comparison only, not for file identification.
            Can be empty string if content hashing unavailable.
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
    file names, directories, operational parameters, and comparison strategy.

    Attributes:
        ignore_file_name: Name of the ignore file (default: ".syncignore")
        local_trash_dir_name: Name of local trash directory
        state_dir_name: Name of state directory under ~/.config/
        app_name: Application name (used in paths and logging)
        verify_operations: If True, rescan files after sync to verify
            uploads/downloads succeeded. This is slower but catches failed
            operations. (default: True for safety)
        comparison_mode: Strategy for comparing files to determine if they
            need syncing. See ComparisonMode enum for available options.
            (default: HASH_THEN_MTIME for backward compatibility)
        supported_comparison_modes: List of comparison modes this adapter
            supports. If None, all modes are assumed supported. Used for
            validation and user guidance.
    """

    ignore_file_name: str = ".syncignore"
    local_trash_dir_name: str = ".syncengine.trash.source"
    state_dir_name: str = "syncengine"
    app_name: str = "syncengine"
    verify_operations: bool = True
    comparison_mode: ComparisonMode = ComparisonMode.HASH_THEN_MTIME
    supported_comparison_modes: Optional[list[ComparisonMode]] = None

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

        # Validate comparison mode is supported if modes are restricted
        if self.supported_comparison_modes is not None:
            if self.comparison_mode not in self.supported_comparison_modes:
                supported_names = [m.value for m in self.supported_comparison_modes]
                raise ValueError(
                    f"Comparison mode '{self.comparison_mode.value}' not supported. "
                    f"Supported modes: {', '.join(supported_names)}"
                )
