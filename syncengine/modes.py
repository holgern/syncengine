"""Sync modes for different synchronization strategies."""

from enum import Enum


class SyncMode(str, Enum):
    """Synchronization modes for source and destination sync.

    Each mode has different behavior for file changes, deletions, conflicts.
    """

    # Full sync modes
    TWO_WAY = "twoWay"
    """Mirror every action in both directions.
    Renaming, deleting & moving is applied to both sides."""

    SOURCE_TO_DESTINATION = "sourceToDestination"
    """Mirror every action done at source to destination but never act on
    destination changes. Renaming, deleting & moving is only transferred
    to the destination."""

    SOURCE_BACKUP = "sourceBackup"
    """Only upload data to destination, never delete anything or act on
    destination changes. Renaming & moving is transferred to destination,
    but not source deletions."""

    DESTINATION_TO_SOURCE = "destinationToSource"
    """Mirror every action done at destination to source but never act on
    source changes. Renaming, deleting & moving is only transferred
    to the source side."""

    DESTINATION_BACKUP = "destinationBackup"
    """Only download data from destination, never delete anything or act on
    source changes. Renaming & moving is transferred to source,
    but not destination deletions."""

    @classmethod
    def from_string(cls, value: str) -> "SyncMode":
        """Parse sync mode from string, supporting abbreviations.

        Args:
            value: Mode string (full name or abbreviation)

        Returns:
            SyncMode enum value

        Raises:
            ValueError: If mode string is not recognized

        Examples:
            >>> SyncMode.from_string("twoWay")
            SyncMode.TWO_WAY
            >>> SyncMode.from_string("tw")
            SyncMode.TWO_WAY
            >>> SyncMode.from_string("std")
            SyncMode.SOURCE_TO_DESTINATION
        """
        # Map of abbreviations and legacy aliases to full names
        abbreviations = {
            # Short abbreviations
            "tw": "twoWay",
            "std": "sourceToDestination",
            "sb": "sourceBackup",
            "dts": "destinationToSource",
            "db": "destinationBackup",
            # Legacy pydrime CLI aliases (user-friendly names)
            "localtocloud": "sourceToDestination",
            "cloudtolocal": "destinationToSource",
            "localbackup": "sourceBackup",
            "cloudbackup": "destinationBackup",
            # Legacy Short abbreviations
            "ltc": "sourceToDestination",
            "lb": "sourceBackup",
            "ctl": "destinationToSource",
            "cb": "destinationBackup",
        }

        # Normalize input
        normalized = value.lower()

        # Check if it's an abbreviation
        if normalized in abbreviations:
            value = abbreviations[normalized]

        # Try to find matching enum value (case-insensitive)
        for mode in cls:
            if mode.value.lower() == value.lower():
                return mode

        # If no match found, raise error with helpful message
        valid_values = [m.value for m in cls] + list(abbreviations.keys())
        raise ValueError(
            f"Invalid sync mode: {value}. Valid values are: {', '.join(valid_values)}"
        )

    @property
    def allows_upload(self) -> bool:
        """Check if this mode allows uploading files."""
        return self in {
            SyncMode.TWO_WAY,
            SyncMode.SOURCE_TO_DESTINATION,
            SyncMode.SOURCE_BACKUP,
        }

    @property
    def allows_download(self) -> bool:
        """Check if this mode allows downloading files."""
        return self in {
            SyncMode.TWO_WAY,
            SyncMode.DESTINATION_TO_SOURCE,
            SyncMode.DESTINATION_BACKUP,
        }

    @property
    def allows_source_delete(self) -> bool:
        """Check if this mode allows deleting source files."""
        return self in {SyncMode.TWO_WAY, SyncMode.DESTINATION_TO_SOURCE}

    @property
    def allows_destination_delete(self) -> bool:
        """Check if this mode allows deleting destination files."""
        return self in {SyncMode.TWO_WAY, SyncMode.SOURCE_TO_DESTINATION}

    @property
    def is_bidirectional(self) -> bool:
        """Check if this mode syncs in both directions."""
        return self == SyncMode.TWO_WAY

    @property
    def requires_source_scan(self) -> bool:
        """Check if this mode requires scanning source files.

        We need to scan source files if we might upload, delete at source,
        or download (to compare against existing source files for idempotency).
        """
        return self.allows_upload or self.allows_source_delete or self.allows_download

    @property
    def requires_destination_scan(self) -> bool:
        """Check if this mode requires scanning destination files.

        We need to scan destination files if we might download, delete at destination,
        or upload (to compare against existing destination files for idempotency).
        """
        return (
            self.allows_download or self.allows_destination_delete or self.allows_upload
        )

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


class InitialSyncPreference(str, Enum):
    """Preference for handling initial sync when no previous state exists.

    When performing a TWO_WAY sync with no previous state, the engine cannot
    distinguish between "file deleted locally" vs "file added remotely". This
    enum controls how to handle files that exist on only one side during the
    first sync.

    After the first sync establishes state, normal TWO_WAY behavior applies
    regardless of this preference.
    """

    MERGE = "merge"
    """Merge both sides without deletions.

    Download files from destination that don't exist locally.
    Upload files from source that don't exist on destination.
    No deletions occur on first sync.

    Best for: Merging two existing directories, cloud backup restoration.
    """

    SOURCE_WINS = "source_wins"
    """Source is authoritative on first sync.

    Files only on source: uploaded to destination
    Files only on destination: deleted from destination

    Best for: Making destination an exact mirror of source.
    """

    DESTINATION_WINS = "destination_wins"
    """Destination is authoritative on first sync.

    Files only on destination: downloaded to source
    Files only on source: deleted from source

    Best for: Cloud/vault restoration, treating remote as source of truth.
    """

    @classmethod
    def from_string(cls, value: str) -> "InitialSyncPreference":
        """Parse preference from string.

        Args:
            value: Preference string

        Returns:
            InitialSyncPreference enum value

        Raises:
            ValueError: If preference string is not recognized

        Examples:
            >>> InitialSyncPreference.from_string("merge")
            InitialSyncPreference.MERGE
            >>> InitialSyncPreference.from_string("source_wins")
            InitialSyncPreference.SOURCE_WINS
        """
        # Normalize input
        normalized = value.lower().replace("-", "_")

        # Try to find matching enum value
        for pref in cls:
            if pref.value.replace("-", "_") == normalized:
                return pref

        # If no match found, raise error with helpful message
        valid_values = [p.value for p in cls]
        raise ValueError(
            f"Invalid initial sync preference: {value}. "
            f"Valid values are: {', '.join(valid_values)}"
        )

    def __str__(self) -> str:
        """Return string representation."""
        return self.value
