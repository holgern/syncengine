"""Sync pair definition for synchronizing source and destination paths."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .modes import SyncMode


@dataclass
class SyncPair:
    """Defines a synchronization pair between source and destination paths.

    A sync pair specifies how files should be synchronized between a source directory
    and a destination path, including the sync mode and various options.
    Supports local-to-local, local-to-cloud, cloud-to-local, and cloud-to-cloud sync.

    Examples:
        >>> pair = SyncPair(
        ...     source=Path("/home/user/Documents"),
        ...     destination="/Documents",
        ...     sync_mode=SyncMode.TWO_WAY
        ... )
        >>> pair.alias = "documents"
        >>> pair.ignore = ["*.tmp", "*.log"]
    """

    source: Path
    """Source directory path to sync"""

    destination: str
    """Destination path (e.g., "/Documents" or "Documents")"""

    sync_mode: SyncMode
    """Synchronization mode (how files are synced)"""

    alias: Optional[str] = None
    """Optional alias for easy reference in CLI"""

    disable_source_trash: bool = False
    """If True, deleted source files are permanently deleted
    instead of moved to trash"""

    ignore: list[str] = field(default_factory=list)
    """List of glob patterns to ignore (e.g., ["*.log", "temp/*"])"""

    exclude_dot_files: bool = False
    """If True, exclude files and folders starting with dot"""

    storage_id: int = 0
    """Storage/workspace ID (0 for personal/default storage)"""

    parent_id: Optional[int] = None
    """Optional parent folder ID for uploads. If specified, files will be uploaded
    into this folder instead of creating/using a folder based on destination path."""

    @property
    def use_source_trash(self) -> bool:
        """Whether to use source trash for deleted files."""
        return not self.disable_source_trash

    def __post_init__(self) -> None:
        """Validate and normalize sync pair configuration."""
        # Ensure source is a Path object (runtime coercion when passed as str)
        # Cast to Any to allow runtime type check without mypy complaining
        source_value: Any = self.source
        if not isinstance(source_value, Path):
            object.__setattr__(self, "source", Path(source_value))

        # Ensure sync_mode is SyncMode enum
        if isinstance(self.sync_mode, str):
            self.sync_mode = SyncMode.from_string(self.sync_mode)

        # Normalize destination path (remove leading/trailing slashes for consistency)
        # When destination is "/" or empty, files sync directly to destination root.
        # E.g., source/subdir/file.txt -> /subdir/file.txt (not /source/subdir/file.txt)
        if self.destination == "/":
            # Root directory - normalize to empty string (meaning destination root)
            self.destination = ""
        else:
            self.destination = self.destination.strip("/")

    @classmethod
    def from_dict(cls, data: dict) -> "SyncPair":
        """Create SyncPair from dictionary (e.g., from JSON config).

        Args:
            data: Dictionary with sync pair configuration

        Returns:
            SyncPair instance

        Raises:
            ValueError: If required fields are missing or invalid

        Examples:
            >>> data = {
            ...     "source": "/home/user/Documents",
            ...     "destination": "/Documents",
            ...     "syncMode": "twoWay",
            ...     "alias": "documents"
            ... }
            >>> pair = SyncPair.from_dict(data)
        """
        required_fields = ["source", "destination", "syncMode"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        return cls(
            source=Path(data["source"]),
            destination=data["destination"],
            sync_mode=SyncMode.from_string(data["syncMode"]),
            alias=data.get("alias"),
            disable_source_trash=data.get("disableSourceTrash", False),
            ignore=data.get("ignore", []),
            exclude_dot_files=data.get("excludeDotFiles", False),
            storage_id=data.get("storageId", 0),
            parent_id=data.get("parentId"),
        )

    def to_dict(self) -> dict:
        """Convert SyncPair to dictionary for JSON serialization.

        Returns:
            Dictionary representation of sync pair.
            Uses POSIX-style paths (forward slashes) for cross-platform consistency.
        """
        return {
            "source": self.source.as_posix(),
            "destination": self.destination,
            "syncMode": self.sync_mode.value,
            "alias": self.alias,
            "disableSourceTrash": self.disable_source_trash,
            "ignore": self.ignore,
            "excludeDotFiles": self.exclude_dot_files,
            "storageId": self.storage_id,
            "parentId": self.parent_id,
        }

    @classmethod
    def parse_literal(
        cls, literal: str, default_mode: Optional[SyncMode] = None
    ) -> "SyncPair":
        """Parse a literal sync pair string.

        Supports various formats:
        - /source:/destination                     # Two-way (default)
        - /source:twoWay:/destination              # Explicit mode
        - /source:tw:/destination                  # Abbreviated mode
        - /source:sourceToDestination:/destination # Full mode name

        On Windows, also supports:
        - C:/source:mode:/destination              # Windows path with mode
        - C:/source:/destination                   # Windows path without mode

        Args:
            literal: Literal sync pair string
            default_mode: Default sync mode if not specified (defaults to TWO_WAY)

        Returns:
            SyncPair instance

        Raises:
            ValueError: If literal format is invalid

        Examples:
            >>> pair = SyncPair.parse_literal("/home/user/docs:/Documents")
            >>> pair.sync_mode
            SyncMode.TWO_WAY
            >>> pair = SyncPair.parse_literal("/home/user/docs:std:/Documents")
            >>> pair.sync_mode
            SyncMode.SOURCE_TO_DESTINATION
        """
        import re

        if default_mode is None:
            default_mode = SyncMode.TWO_WAY

        # Handle Windows drive letters (e.g., C:, D:)
        # If path starts with a drive letter, split only on colons after the drive
        windows_drive_match = re.match(r"^([A-Za-z]:)", literal)
        if windows_drive_match:
            drive = windows_drive_match.group(1)
            rest_of_literal = literal[len(drive) :]
            parts = rest_of_literal.split(":")
            # Prepend the drive to the first part
            if parts:
                parts[0] = drive + parts[0]
        else:
            parts = literal.split(":")

        if len(parts) == 2:
            # Format: /source:/destination (default mode)
            source, destination = parts
            sync_mode = default_mode
        elif len(parts) == 3:
            # Format: /source:mode:/destination
            source, mode_str, destination = parts
            sync_mode = SyncMode.from_string(mode_str)
        else:
            raise ValueError(
                f"Invalid sync pair literal: {literal}. "
                "Expected format: '/source:/destination' or '/source:mode:/destination'"
            )

        # Validate paths are not empty
        if not source or not destination:
            raise ValueError(
                f"Invalid sync pair literal: {literal}. "
                "Source and destination paths cannot be empty"
            )

        return cls(
            source=Path(source),
            destination=destination,
            sync_mode=sync_mode,
        )

    def __str__(self) -> str:
        """String representation of sync pair.

        Uses POSIX-style paths for cross-platform consistency.
        """
        source_str = self.source.as_posix()
        if self.alias:
            return (
                f"{self.alias} ({source_str} "
                f"←{self.sync_mode.value}→ {self.destination})"
            )
        return f"{source_str} ←{self.sync_mode.value}→ {self.destination}"

    def __repr__(self) -> str:
        """Detailed representation of sync pair."""
        return (
            f"SyncPair(source={self.source.as_posix()}, "
            f"destination={self.destination}, "
            f"sync_mode={self.sync_mode}, alias={self.alias})"
        )
