"""State management for tracking sync history.

This module provides state tracking for bidirectional sync modes,
enabling proper detection of file deletions and renames by remembering
which files were present in previous sync operations along with their
metadata (size, mtime, file_id, hash).

Inspired by filen-sync's state.ts implementation which stores:
- Full tree structure (path -> item mapping)
- File ID index for source files (file_id -> item mapping)
- ID index for destination files (id -> item mapping)
- Source file hashes for change detection

Cross-platform note:
- On Linux/macOS: file_id is the inode number (st_ino), which persists across renames
- On Windows: file_id is the NTFS file index (st_ino), which should persist across
  renames on NTFS but behavior may vary on other filesystems
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .constants import DEFAULT_STATE_DIR_NAME

logger = logging.getLogger(__name__)

# State format version - increment when breaking changes are made
STATE_VERSION = 2


@dataclass
class SourceItemState:
    """State of a source file/directory from previous sync.

    Stores metadata needed for rename detection and change comparison.
    """

    path: str
    """Relative path (using forward slashes)"""

    size: int
    """File size in bytes (0 for directories)"""

    mtime: float
    """Last modification time (Unix timestamp)"""

    file_id: int
    """Filesystem file identifier (inode on Unix, file index on Windows).

    This value persists across renames on most filesystems, enabling
    rename detection by tracking the same file_id at a different path.
    """

    item_type: str = "file"
    """Type: 'file' or 'directory'"""

    creation_time: Optional[float] = None
    """Creation time (Unix timestamp) if available"""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "path": self.path,
            "size": self.size,
            "mtime": self.mtime,
            "file_id": self.file_id,
            "item_type": self.item_type,
            "creation_time": self.creation_time,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceItemState":
        """Create from dictionary."""
        return cls(
            path=data.get("path", ""),
            size=data.get("size", 0),
            mtime=data.get("mtime", 0.0),
            # Support both 'file_id' and legacy 'inode' key for backward compatibility
            file_id=data.get("file_id", data.get("inode", 0)),
            item_type=data.get("item_type", "file"),
            creation_time=data.get("creation_time"),
        )


@dataclass
class DestinationItemState:
    """State of a destination file/directory from previous sync.

    Stores metadata needed for rename detection and change comparison.
    """

    path: str
    """Relative path (using forward slashes)"""

    size: int
    """File size in bytes (0 for directories)"""

    mtime: Optional[float]
    """Last modification time (Unix timestamp) if available"""

    id: int
    """Destination entry ID - persists across renames"""

    item_type: str = "file"
    """Type: 'file' or 'directory'"""

    file_hash: str = ""
    """MD5 hash of file content (empty for directories)"""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "path": self.path,
            "size": self.size,
            "mtime": self.mtime,
            "id": self.id,
            "item_type": self.item_type,
            "file_hash": self.file_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DestinationItemState":
        """Create from dictionary."""
        return cls(
            path=data.get("path", ""),
            size=data.get("size", 0),
            mtime=data.get("mtime"),
            # Support both 'id' and legacy 'uuid' key for backward compatibility
            id=data.get("id", data.get("uuid", 0)),
            item_type=data.get("item_type", "file"),
            file_hash=data.get("file_hash", ""),
        )


@dataclass
class SourceTree:
    """Full source tree state with path and file_id indexes.

    Provides O(1) lookup by both path and file_id for efficient
    rename detection.
    """

    tree: dict[str, SourceItemState] = field(default_factory=dict)
    """Path -> SourceItemState mapping"""

    file_ids: dict[int, SourceItemState] = field(default_factory=dict)
    """File ID -> SourceItemState mapping for rename detection"""

    @property
    def size(self) -> int:
        """Number of items in tree."""
        return len(self.tree)

    def add_item(self, item: SourceItemState) -> None:
        """Add an item to both indexes."""
        self.tree[item.path] = item
        self.file_ids[item.file_id] = item

    def remove_item(self, path: str) -> Optional[SourceItemState]:
        """Remove an item from both indexes by path."""
        item = self.tree.pop(path, None)
        if item:
            self.file_ids.pop(item.file_id, None)
        return item

    def get_by_path(self, path: str) -> Optional[SourceItemState]:
        """Get item by path."""
        return self.tree.get(path)

    def get_by_file_id(self, file_id: int) -> Optional[SourceItemState]:
        """Get item by file_id (for rename detection)."""
        return self.file_ids.get(file_id)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "tree": {k: v.to_dict() for k, v in self.tree.items()},
            "file_ids": {str(k): v.to_dict() for k, v in self.file_ids.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceTree":
        """Create from dictionary."""
        tree_data = data.get("tree", {})
        # Support both 'file_ids' and legacy 'inodes' key for backward compatibility
        file_ids_data = data.get("file_ids", data.get("inodes", {}))
        return cls(
            tree={k: SourceItemState.from_dict(v) for k, v in tree_data.items()},
            file_ids={
                int(k): SourceItemState.from_dict(v) for k, v in file_ids_data.items()
            },
        )


@dataclass
class DestinationTree:
    """Full destination tree state with path and ID indexes.

    Provides O(1) lookup by both path and ID for efficient
    rename detection.
    """

    tree: dict[str, DestinationItemState] = field(default_factory=dict)
    """Path -> DestinationItemState mapping"""

    ids: dict[int, DestinationItemState] = field(default_factory=dict)
    """ID -> DestinationItemState mapping for rename detection"""

    @property
    def size(self) -> int:
        """Number of items in tree."""
        return len(self.tree)

    def add_item(self, item: DestinationItemState) -> None:
        """Add an item to both indexes."""
        self.tree[item.path] = item
        self.ids[item.id] = item

    def remove_item(self, path: str) -> Optional[DestinationItemState]:
        """Remove an item from both indexes by path."""
        item = self.tree.pop(path, None)
        if item:
            self.ids.pop(item.id, None)
        return item

    def get_by_path(self, path: str) -> Optional[DestinationItemState]:
        """Get item by path."""
        return self.tree.get(path)

    def get_by_id(self, id: int) -> Optional[DestinationItemState]:
        """Get item by ID (for rename detection)."""
        return self.ids.get(id)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "tree": {k: v.to_dict() for k, v in self.tree.items()},
            "ids": {str(k): v.to_dict() for k, v in self.ids.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DestinationTree":
        """Create from dictionary."""
        tree_data = data.get("tree", {})
        # Support both 'ids' and legacy 'uuids' key for backward compatibility
        ids_data = data.get("ids", data.get("uuids", {}))
        return cls(
            tree={k: DestinationItemState.from_dict(v) for k, v in tree_data.items()},
            ids={
                int(k): DestinationItemState.from_dict(v) for k, v in ids_data.items()
            },
        )


@dataclass
class SyncState:
    """Represents the full state of a sync pair from a previous sync.

    Stores complete tree structure for both source and destination, enabling:
    - Deletion detection (file in previous state but not current)
    - Rename detection (same file_id/id, different path)
    - Change detection (same path, different size/mtime/hash)

    This is version 2 of the state format, storing full metadata instead
    of just file paths.
    """

    source_path: str
    """Source directory path that was synced"""

    destination_path: str
    """Destination path that was synced"""

    source_tree: SourceTree = field(default_factory=SourceTree)
    """Full source tree with path and file_id indexes"""

    destination_tree: DestinationTree = field(default_factory=DestinationTree)
    """Full destination tree with path and ID indexes"""

    source_file_hashes: dict[str, str] = field(default_factory=dict)
    """Path -> MD5 hash mapping for source files"""

    last_sync: Optional[str] = None
    """ISO timestamp of last successful sync"""

    version: int = STATE_VERSION
    """State format version"""

    # Legacy field for backward compatibility
    synced_files: set[str] = field(default_factory=set)
    """Set of relative paths (legacy, for backward compatibility)"""

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "source_path": self.source_path,
            "destination_path": self.destination_path,
            # Keep old keys for backward compatibility in JSON
            "local_path": self.source_path,
            "remote_path": self.destination_path,
            "source_tree": self.source_tree.to_dict(),
            "destination_tree": self.destination_tree.to_dict(),
            # Keep old keys for backward compatibility in JSON
            "local_tree": self.source_tree.to_dict(),
            "remote_tree": self.destination_tree.to_dict(),
            "source_file_hashes": self.source_file_hashes,
            "local_file_hashes": self.source_file_hashes,
            "last_sync": self.last_sync,
            # Include legacy synced_files for compatibility
            "synced_files": sorted(self.synced_files),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SyncState":
        """Create SyncState from dictionary."""
        version = data.get("version", 1)

        # Handle legacy v1 format (just synced_files)
        if version == 1 or ("source_tree" not in data and "local_tree" not in data):
            return cls(
                source_path=data.get("source_path", data.get("local_path", "")),
                destination_path=data.get(
                    "destination_path", data.get("remote_path", "")
                ),
                synced_files=set(data.get("synced_files", [])),
                last_sync=data.get("last_sync"),
                version=1,
            )

        # Handle v2 format with full trees (support both old and new keys)
        source_tree_data = data.get("source_tree", data.get("local_tree", {}))
        dest_tree_data = data.get("destination_tree", data.get("remote_tree", {}))
        source_hashes = data.get(
            "source_file_hashes", data.get("local_file_hashes", {})
        )

        return cls(
            source_path=data.get("source_path", data.get("local_path", "")),
            destination_path=data.get("destination_path", data.get("remote_path", "")),
            source_tree=SourceTree.from_dict(source_tree_data),
            destination_tree=DestinationTree.from_dict(dest_tree_data),
            source_file_hashes=source_hashes,
            last_sync=data.get("last_sync"),
            version=version,
            synced_files=set(data.get("synced_files", [])),
        )

    def get_synced_paths(self) -> set[str]:
        """Get all synced paths (for backward compatibility).

        Returns paths that exist in both source and destination trees.
        """
        if self.version == 1:
            return self.synced_files

        source_paths = set(self.source_tree.tree.keys())
        destination_paths = set(self.destination_tree.tree.keys())
        return source_paths & destination_paths


class SyncStateManager:
    """Manages sync state persistence for tracking file deletions and renames.

    The state is stored in a JSON file in the user's config directory,
    keyed by a hash of the source and destination paths to support multiple
    sync pairs.

    State is stored in versioned subdirectories to handle format migrations.
    """

    def __init__(
        self,
        state_dir: Optional[Path] = None,
        state_dir_name: str = DEFAULT_STATE_DIR_NAME,
    ):
        """Initialize state manager.

        Args:
            state_dir: Directory to store state files. Defaults to
                      ~/.config/{state_dir_name}/sync_state/
            state_dir_name: Name of the state directory (e.g., "syncengine")
        """
        if state_dir is None:
            state_dir = Path.home() / ".config" / state_dir_name / "sync_state"
        self.state_dir = state_dir / f"v{STATE_VERSION}"
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Also check legacy directory for migration
        self._legacy_dir = state_dir

    def _get_state_key(
        self, source_path: Path, destination_path: str, storage_id: Optional[int] = None
    ) -> str:
        """Generate a unique key for a sync pair.

        Args:
            source_path: Source directory path
            destination_path: Destination path
            storage_id: Optional storage ID to differentiate between storages

        Returns:
            Hash-based key for the sync pair
        """
        # Use absolute path for consistency
        source_abs = str(source_path.resolve())
        # Include storage_id in key to prevent collisions between different storages
        storage_suffix = f":storage_{storage_id}" if storage_id is not None else ""
        combined = f"{source_abs}:{destination_path}{storage_suffix}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def _get_state_file(
        self, source_path: Path, destination_path: str, storage_id: Optional[int] = None
    ) -> Path:
        """Get the state file path for a sync pair.

        Args:
            source_path: Source directory path
            destination_path: Destination path
            storage_id: Optional storage ID to differentiate between storages

        Returns:
            Path to the state file
        """
        key = self._get_state_key(source_path, destination_path, storage_id)
        return self.state_dir / f"{key}.json"

    def _get_legacy_state_file(self, source_path: Path, destination_path: str) -> Path:
        """Get legacy state file path (for migration)."""
        key = self._get_state_key(source_path, destination_path)
        return self._legacy_dir / f"{key}.json"

    def load_state(
        self,
        source_path: Path,
        destination_path: str,
        storage_id: Optional[int] = None,
    ) -> Optional[SyncState]:
        """Load sync state for a sync pair.

        Automatically migrates from v1 format if needed.

        Args:
            source_path: Source directory path
            destination_path: Destination path
            storage_id: Optional storage ID to differentiate between storages

        Returns:
            SyncState if found, None otherwise
        """
        state_file = self._get_state_file(source_path, destination_path, storage_id)
        legacy_file = self._get_legacy_state_file(source_path, destination_path)

        # Try current version first
        if state_file.exists():
            try:
                with open(state_file, encoding="utf-8") as f:
                    data = json.load(f)
                state = SyncState.from_dict(data)
                logger.debug(
                    f"Loaded sync state v{state.version} with "
                    f"{state.source_tree.size} source, "
                    f"{state.destination_tree.size} destination "
                    f"items from {state.last_sync}"
                )
                return state
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load sync state: {e}")
                return None

        # Try legacy v1 format for migration
        if legacy_file.exists() and legacy_file != state_file:
            try:
                with open(legacy_file, encoding="utf-8") as f:
                    data = json.load(f)
                state = SyncState.from_dict(data)
                logger.info(
                    f"Migrated legacy sync state with {len(state.synced_files)} files"
                )
                return state
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load legacy sync state: {e}")
                return None

        logger.debug(f"No sync state found at {state_file}")
        return None

    def save_state(
        self,
        source_path: Path,
        destination_path: str,
        synced_files: Optional[set[str]] = None,
        source_tree: Optional[SourceTree] = None,
        destination_tree: Optional[DestinationTree] = None,
        source_file_hashes: Optional[dict[str, str]] = None,
        storage_id: Optional[int] = None,
    ) -> None:
        """Save sync state for a sync pair.

        Args:
            source_path: Source directory path
            destination_path: Destination path
            synced_files: Set of relative paths (legacy, optional)
            source_tree: Full source tree state
            destination_tree: Full destination tree state
            source_file_hashes: MD5 hashes of source files
            storage_id: Optional storage ID to differentiate between storages
        """
        state = SyncState(
            source_path=str(source_path.resolve()),
            destination_path=destination_path,
            source_tree=source_tree or SourceTree(),
            destination_tree=destination_tree or DestinationTree(),
            source_file_hashes=source_file_hashes or {},
            synced_files=synced_files or set(),
            last_sync=datetime.now().isoformat(),
            version=STATE_VERSION,
        )

        # If only synced_files provided (backward compat), populate trees
        if synced_files and not source_tree and not destination_tree:
            state.synced_files = synced_files

        state_file = self._get_state_file(source_path, destination_path, storage_id)

        try:
            # Write atomically using temp file
            tmp_file = state_file.with_suffix(".tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(state.to_dict(), f, indent=2)
            tmp_file.replace(state_file)

            logger.debug(
                f"Saved sync state v{STATE_VERSION} with "
                f"{state.source_tree.size} source, "
                f"{state.destination_tree.size} destination "
                f"items to {state_file}"
            )
        except OSError as e:
            logger.warning(f"Failed to save sync state: {e}")
            # Clean up temp file if it exists
            tmp_file = state_file.with_suffix(".tmp")
            if tmp_file.exists():
                tmp_file.unlink()

    def save_state_from_trees(
        self,
        source_path: Path,
        destination_path: str,
        source_tree: SourceTree,
        destination_tree: DestinationTree,
        source_file_hashes: Optional[dict[str, str]] = None,
        storage_id: Optional[int] = None,
    ) -> None:
        """Save sync state with full tree information.

        This is the preferred method for v2 state format.

        Args:
            source_path: Source directory path
            destination_path: Destination path
            source_tree: Full source tree state
            destination_tree: Full destination tree state
            source_file_hashes: MD5 hashes of source files
            storage_id: Optional storage ID to differentiate between storages
        """
        # Also compute synced_files for backward compatibility
        source_paths = set(source_tree.tree.keys())
        destination_paths = set(destination_tree.tree.keys())
        synced_files = source_paths & destination_paths

        self.save_state(
            source_path=source_path,
            destination_path=destination_path,
            synced_files=synced_files,
            source_tree=source_tree,
            destination_tree=destination_tree,
            source_file_hashes=source_file_hashes,
            storage_id=storage_id,
        )

    def clear_state(
        self, source_path: Path, destination_path: str, storage_id: Optional[int] = None
    ) -> bool:
        """Clear sync state for a sync pair.

        Args:
            source_path: Source directory path
            destination_path: Destination path
            storage_id: Optional storage ID to differentiate between storages

        Returns:
            True if state was cleared, False if no state existed
        """
        state_file = self._get_state_file(source_path, destination_path, storage_id)
        legacy_file = self._get_legacy_state_file(source_path, destination_path)
        cleared = False

        if state_file.exists():
            state_file.unlink()
            logger.debug(f"Cleared sync state at {state_file}")
            cleared = True

        # Also clear legacy file if different
        if legacy_file != state_file and legacy_file.exists():
            legacy_file.unlink()
            logger.debug(f"Cleared legacy sync state at {legacy_file}")
            cleared = True

        return cleared


def build_source_tree_from_files(source_files: list) -> SourceTree:
    """Build a SourceTree from a list of SourceFile objects.

    This function creates a SourceTree with proper file_id indexing
    for efficient rename detection.

    Args:
        source_files: List of SourceFile objects from DirectoryScanner.scan_source()

    Returns:
        SourceTree with all files indexed by path and file_id
    """
    tree = SourceTree()

    for source_file in source_files:
        item = SourceItemState(
            path=source_file.relative_path,
            size=source_file.size,
            mtime=source_file.mtime,
            file_id=source_file.file_id,
            item_type="file",
            creation_time=source_file.creation_time,
        )
        tree.add_item(item)

    return tree


def build_destination_tree_from_files(destination_files: list) -> DestinationTree:
    """Build a DestinationTree from a list of DestinationFile objects.

    This function creates a DestinationTree with proper ID indexing
    for efficient rename detection.

    Args:
        destination_files: List of DestinationFile objects from
                          DirectoryScanner.scan_destination()

    Returns:
        DestinationTree with all files indexed by path and ID
    """
    tree = DestinationTree()

    for destination_file in destination_files:
        item = DestinationItemState(
            path=destination_file.relative_path,
            size=destination_file.size,
            mtime=destination_file.mtime,
            id=destination_file.id,
            item_type="file",
            file_hash=destination_file.hash,
        )
        tree.add_item(item)

    return tree


def validate_state_against_current_files(
    state: SyncState,
    current_source_files: dict[str, Any],
    current_dest_files: dict[str, Any],
) -> set[str]:
    """Validate cached state against current file system state.

    This function checks if files that were marked as synced in the cached
    state still exist and have the same metadata. This is critical for
    detecting:
    - File deletions (file in state but not in current scan)
    - File modifications (file exists but size/mtime changed)

    A file is considered "still validly synced" only if:
    1. It exists in current source scan with same size and mtime
    2. It exists in current destination scan with same size
    3. Both conditions are met

    Args:
        state: Previously saved sync state
        current_source_files: Dict mapping relative_path -> SourceFile
        current_dest_files: Dict mapping relative_path -> DestinationFile

    Returns:
        Set of relative paths that are still validly synced (no changes detected)
    """
    validated_paths = set()

    # Get all paths that were synced in previous state
    synced_paths = state.get_synced_paths()

    for path in synced_paths:
        # Check source file
        source_valid = False
        if path in current_source_files:
            current_source = current_source_files[path]
            state_source = state.source_tree.get_by_path(path)

            if state_source:
                # File exists - check if metadata matches
                size_matches = current_source.size == state_source.size
                mtime_matches = abs(current_source.mtime - state_source.mtime) < 1.0
                source_valid = size_matches and mtime_matches

                if not source_valid:
                    logger.debug(
                        f"Source file changed: {path} "
                        f"(size: {state_source.size} -> {current_source.size}, "
                        f"mtime: {state_source.mtime} -> {current_source.mtime})"
                    )
            else:
                # State has v1 format without tree data - assume valid if file exists
                source_valid = True
        else:
            logger.debug(f"Source file deleted: {path}")

        # Check destination file
        dest_valid = False
        if path in current_dest_files:
            current_dest = current_dest_files[path]
            state_dest = state.destination_tree.get_by_path(path)

            if state_dest:
                # File exists - check if metadata matches
                size_matches = current_dest.size == state_dest.size
                dest_valid = size_matches

                if not dest_valid:
                    logger.debug(
                        f"Destination file changed: {path} "
                        f"(size: {state_dest.size} -> {current_dest.size})"
                    )
            else:
                # State has v1 format without tree data - assume valid if file exists
                dest_valid = True
        else:
            logger.debug(f"Destination file deleted: {path}")

        # Only consider file as still synced if both source and dest are valid
        if source_valid and dest_valid:
            validated_paths.add(path)

    invalidated_count = len(synced_paths) - len(validated_paths)
    if invalidated_count > 0:
        logger.info(
            f"State validation: {len(validated_paths)} files still synced, "
            f"{invalidated_count} files invalidated (deleted or modified)"
        )

    return validated_paths
