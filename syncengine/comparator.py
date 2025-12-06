"""File comparison logic for sync operations."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .modes import SyncMode
from .scanner import DestinationFile, SourceFile
from .state import DestinationTree, SourceTree


class SyncAction(str, Enum):
    """Actions that can be taken during sync."""

    UPLOAD = "upload"
    """Upload source file to destination"""

    DOWNLOAD = "download"
    """Download destination file to source"""

    DELETE_SOURCE = "delete_source"
    """Delete source file"""

    DELETE_DESTINATION = "delete_destination"
    """Delete destination file"""

    RENAME_SOURCE = "rename_source"
    """Rename/move source file (detected via destination rename)"""

    RENAME_DESTINATION = "rename_destination"
    """Rename/move destination file (detected via source rename)"""

    SKIP = "skip"
    """Skip file (no action needed)"""

    CONFLICT = "conflict"
    """File conflict detected"""


@dataclass
class SyncDecision:
    """Represents a decision about how to sync a file."""

    action: SyncAction
    """Action to take"""

    reason: str
    """Human-readable reason for this decision"""

    source_file: Optional[SourceFile]
    """Source file (if exists)"""

    destination_file: Optional[DestinationFile]
    """Destination file (if exists)"""

    relative_path: str
    """Relative path of the file"""

    old_path: Optional[str] = None
    """For rename operations: the previous path of the file"""

    new_path: Optional[str] = None
    """For rename operations: the new path of the file"""


class FileComparator:
    """Compares source and destination files to determine sync actions.

    For bidirectional sync modes (TWO_WAY), the comparator can use previous
    sync state to determine whether a file that exists only on one side is
    a new file or was deleted from the other side.

    Rename detection uses file_id (for source files) and id (for destination files)
    to detect when a file has been moved/renamed rather than deleted+created.
    This enables efficient rename operations instead of re-uploading/downloading.
    """

    def __init__(
        self,
        sync_mode: SyncMode,
        previous_synced_files: Optional[set[str]] = None,
        previous_source_tree: Optional[SourceTree] = None,
        previous_destination_tree: Optional[DestinationTree] = None,
    ):
        """Initialize file comparator.

        Args:
            sync_mode: Sync mode to use for comparison
            previous_synced_files: Set of relative paths that were synced
                                  in the previous sync operation. Used for
                                  deletion detection in TWO_WAY mode.
            previous_source_tree: Previous source tree state for rename detection.
                                Contains file_id -> path mapping.
            previous_destination_tree: Previous destination tree state for rename
                                      detection. Contains id -> path mapping.
        """
        self.sync_mode = sync_mode
        self.previous_synced_files = previous_synced_files or set()
        self.previous_source_tree = previous_source_tree
        self.previous_destination_tree = previous_destination_tree

        # Track detected renames to avoid processing them twice
        self._source_renames: dict[int, str] = {}  # file_id -> new_path
        self._destination_renames: dict[int, str] = {}  # id -> new_path
        self._handled_rename_old_paths: set[str] = set()

    def compare_files(
        self,
        source_files: dict[str, SourceFile],
        destination_files: dict[str, DestinationFile],
    ) -> list[SyncDecision]:
        """Compare source and destination files and determine sync actions.

        Args:
            source_files: Dictionary mapping relative_path to SourceFile
            destination_files: Dictionary mapping relative_path to DestinationFile

        Returns:
            List of SyncDecision objects
        """
        decisions: list[SyncDecision] = []

        # First pass: detect renames by comparing with previous state
        if self.sync_mode == SyncMode.TWO_WAY:
            self._detect_renames(source_files, destination_files)

        # Get all unique paths
        all_paths = set(source_files.keys()) | set(destination_files.keys())

        for path in sorted(all_paths):
            # Skip if this path was already handled as old path of a rename
            if path in self._handled_rename_old_paths:
                continue

            source_file = source_files.get(path)
            destination_file = destination_files.get(path)

            decision = self._compare_single_file(
                path, source_file, destination_file, source_files, destination_files
            )
            decisions.append(decision)

        return decisions

    def _detect_renames(
        self,
        source_files: dict[str, SourceFile],
        destination_files: dict[str, DestinationFile],
    ) -> None:
        """Detect renames by comparing current files with previous state.

        A rename is detected when:
        - Source: A file_id exists in the previous source tree at path A,
                 but now exists at path B in current source files
        - Destination: An id exists in the previous destination tree at path A,
                      but now exists at path B in current destination files

        Args:
            source_files: Current source files
            destination_files: Current destination files
        """
        # Detect source renames (same file_id, different path)
        if self.previous_source_tree:
            # Build current file_id -> path mapping
            current_source_by_file_id = {
                f.file_id: f.relative_path for f in source_files.values()
            }

            for (
                file_id,
                prev_source_state,
            ) in self.previous_source_tree.file_ids.items():
                if file_id in current_source_by_file_id:
                    current_path = current_source_by_file_id[file_id]
                    prev_path = prev_source_state.path
                    if current_path != prev_path:
                        # Source rename detected!
                        self._source_renames[file_id] = current_path

        # Detect destination renames (same id, different path)
        if self.previous_destination_tree:
            # Build current id -> path mapping
            current_dest_by_id = {
                f.id: f.relative_path for f in destination_files.values()
            }

            for dest_id, prev_dest_state in self.previous_destination_tree.ids.items():
                if dest_id in current_dest_by_id:
                    current_path = current_dest_by_id[dest_id]
                    prev_path = prev_dest_state.path
                    if current_path != prev_path:
                        # Destination rename detected!
                        self._destination_renames[dest_id] = current_path

    def _compare_single_file(
        self,
        path: str,
        source_file: Optional[SourceFile],
        destination_file: Optional[DestinationFile],
        source_files: Optional[dict[str, SourceFile]] = None,
        destination_files: Optional[dict[str, DestinationFile]] = None,
    ) -> SyncDecision:
        """Compare a single file and determine action.

        Args:
            path: Relative path of the file
            source_file: Source file (if exists)
            destination_file: Destination file (if exists)
            source_files: All source files (for rename lookup)
            destination_files: All destination files (for rename lookup)

        Returns:
            SyncDecision for this file
        """
        # Case 1: File exists in both locations
        if source_file and destination_file:
            return self._compare_existing_files(path, source_file, destination_file)

        # Case 2: File only exists at source
        if source_file and not destination_file:
            return self._handle_source_only(
                path, source_file, source_files or {}, destination_files or {}
            )

        # Case 3: File only exists at destination
        if destination_file and not source_file:
            return self._handle_destination_only(
                path, destination_file, source_files or {}, destination_files or {}
            )

        # Should never happen
        return SyncDecision(
            action=SyncAction.SKIP,
            reason="No file found",
            source_file=None,
            destination_file=None,
            relative_path=path,
        )

    def _compare_existing_files(
        self, path: str, source_file: SourceFile, destination_file: DestinationFile
    ) -> SyncDecision:
        """Compare files that exist in both locations.

        Comparison logic:
        1. First compare sizes - if different, files are definitely different
        2. If sizes match, compare hashes if available (destination has hash)
        3. If hash not available, fall back to mtime comparison
        """
        # Check if files are identical by size first (quick check)
        if source_file.size == destination_file.size:
            # Sizes match - check hash if available for content verification
            # Destination files always have a hash from the API
            if destination_file.hash:
                # For now, we skip hash verification on download as computing
                # source hash is expensive. The size check is usually sufficient.
                # TODO: Add optional hash verification flag
                pass

            # Files are likely identical - skip
            return SyncDecision(
                action=SyncAction.SKIP,
                reason="Files are identical (same size)",
                source_file=source_file,
                destination_file=destination_file,
                relative_path=path,
            )

        # Files are different - check modification times
        if destination_file.mtime is None:
            # No destination mtime - can't compare, prefer source for safety
            if self.sync_mode.allows_upload:
                return SyncDecision(
                    action=SyncAction.UPLOAD,
                    reason="Destination mtime unavailable, uploading source version",
                    source_file=source_file,
                    destination_file=destination_file,
                    relative_path=path,
                )
            else:
                return SyncDecision(
                    action=SyncAction.SKIP,
                    reason="Different sizes but cannot determine which is newer",
                    source_file=source_file,
                    destination_file=destination_file,
                    relative_path=path,
                )

        # Compare modification times
        source_mtime = source_file.mtime
        destination_mtime = destination_file.mtime

        # Allow 2 second tolerance for filesystem differences
        time_diff = abs(source_mtime - destination_mtime)
        if time_diff < 2:
            # Times are essentially the same but sizes differ - conflict
            reason = (
                f"Same timestamp but different sizes "
                f"({source_file.size} vs {destination_file.size})"
            )
            return SyncDecision(
                action=SyncAction.CONFLICT,
                reason=reason,
                source_file=source_file,
                destination_file=destination_file,
                relative_path=path,
            )

        # Determine which is newer
        if source_mtime > destination_mtime:
            # Source is newer
            if self.sync_mode.allows_upload:
                return SyncDecision(
                    action=SyncAction.UPLOAD,
                    reason="Source file is newer",
                    source_file=source_file,
                    destination_file=destination_file,
                    relative_path=path,
                )
        else:
            # Destination is newer
            if self.sync_mode.allows_download:
                return SyncDecision(
                    action=SyncAction.DOWNLOAD,
                    reason="Destination file is newer",
                    source_file=source_file,
                    destination_file=destination_file,
                    relative_path=path,
                )

        # Can't sync due to mode restrictions
        return SyncDecision(
            action=SyncAction.SKIP,
            reason=f"Files differ but sync mode {self.sync_mode.value} prevents action",
            source_file=source_file,
            destination_file=destination_file,
            relative_path=path,
        )

    def _handle_source_only(
        self,
        path: str,
        source_file: SourceFile,
        source_files: dict[str, SourceFile],
        destination_files: dict[str, DestinationFile],
    ) -> SyncDecision:
        """Handle file that only exists at source.

        For TWO_WAY mode with previous state:
        - If file was previously synced, it was deleted from destination
          -> delete source
        - If file was NOT previously synced, it's a new file -> upload
        - If file_id matches a renamed file in destination, it's a rename -> rename dest

        Args:
            path: Current path of the file
            source_file: Source file object
            source_files: All current source files
            destination_files: All current destination files
        """
        # Check if this is a source rename that needs to be propagated to destination
        if (
            self.sync_mode == SyncMode.TWO_WAY
            and source_file.file_id in self._source_renames
            and self.previous_source_tree
        ):
            prev_state = self.previous_source_tree.get_by_file_id(source_file.file_id)
            if prev_state and prev_state.path != path:
                old_path = prev_state.path
                # Check if old path still exists in destination
                if old_path in destination_files:
                    # Mark old path as handled
                    self._handled_rename_old_paths.add(old_path)
                    return SyncDecision(
                        action=SyncAction.RENAME_DESTINATION,
                        reason=f"Source file renamed from '{old_path}' to '{path}'",
                        source_file=source_file,
                        destination_file=destination_files[old_path],
                        relative_path=path,
                        old_path=old_path,
                        new_path=path,
                    )

        # For TWO_WAY mode, use previous state to determine action
        if self.sync_mode == SyncMode.TWO_WAY and self.previous_synced_files:
            if path in self.previous_synced_files:
                # File was synced before but now only exists at source
                # This means it was deleted from destination -> delete source
                return SyncDecision(
                    action=SyncAction.DELETE_SOURCE,
                    reason="File deleted from destination (was previously synced)",
                    source_file=source_file,
                    destination_file=None,
                    relative_path=path,
                )
            # else: File was not synced before, treat as new source file

        if self.sync_mode.allows_upload:
            return SyncDecision(
                action=SyncAction.UPLOAD,
                reason="New source file",
                source_file=source_file,
                destination_file=None,
                relative_path=path,
            )
        elif self.sync_mode.allows_source_delete:
            # File was deleted from destination and should be deleted at source
            # (for destinationToSource mode)
            return SyncDecision(
                action=SyncAction.DELETE_SOURCE,
                reason="File deleted from destination",
                source_file=source_file,
                destination_file=None,
                relative_path=path,
            )
        else:
            reason = (
                f"Source-only file but sync mode {self.sync_mode.value} prevents action"
            )
            return SyncDecision(
                action=SyncAction.SKIP,
                reason=reason,
                source_file=source_file,
                destination_file=None,
                relative_path=path,
            )

    def _handle_destination_only(
        self,
        path: str,
        destination_file: DestinationFile,
        source_files: dict[str, SourceFile],
        destination_files: dict[str, DestinationFile],
    ) -> SyncDecision:
        """Handle file that only exists at destination.

        For TWO_WAY mode with previous state:
        - If file was previously synced, it was deleted at source -> delete destination
        - If file was NOT previously synced, it's a new file -> download
        - If id matches a renamed file at source, it's a rename -> rename source

        Args:
            path: Current path of the file
            destination_file: Destination file object
            source_files: All current source files
            destination_files: All current destination files
        """
        # Check if this is a destination rename that needs to be propagated to source
        if (
            self.sync_mode == SyncMode.TWO_WAY
            and destination_file.id in self._destination_renames
            and self.previous_destination_tree
        ):
            prev_state = self.previous_destination_tree.get_by_id(destination_file.id)
            if prev_state and prev_state.path != path:
                old_path = prev_state.path
                # Check if old path still exists at source
                if old_path in source_files:
                    # Mark old path as handled
                    self._handled_rename_old_paths.add(old_path)
                    return SyncDecision(
                        action=SyncAction.RENAME_SOURCE,
                        reason=(
                            f"Destination file renamed from '{old_path}' to '{path}'"
                        ),
                        source_file=source_files[old_path],
                        destination_file=destination_file,
                        relative_path=path,
                        old_path=old_path,
                        new_path=path,
                    )

        # For TWO_WAY mode, use previous state to determine action
        if self.sync_mode == SyncMode.TWO_WAY and self.previous_synced_files:
            if path in self.previous_synced_files:
                # File was synced before but now only exists at destination
                # This means it was deleted at source -> delete destination
                return SyncDecision(
                    action=SyncAction.DELETE_DESTINATION,
                    reason="File deleted at source (was previously synced)",
                    source_file=None,
                    destination_file=destination_file,
                    relative_path=path,
                )
            # else: File was not synced before, treat as new destination file

        if self.sync_mode.allows_download:
            return SyncDecision(
                action=SyncAction.DOWNLOAD,
                reason="New destination file",
                source_file=None,
                destination_file=destination_file,
                relative_path=path,
            )
        elif self.sync_mode.allows_destination_delete:
            # File was deleted at source and should be deleted at destination
            return SyncDecision(
                action=SyncAction.DELETE_DESTINATION,
                reason="File deleted at source",
                source_file=None,
                destination_file=destination_file,
                relative_path=path,
            )
        else:
            reason = (
                f"Destination-only file but sync mode "
                f"{self.sync_mode.value} prevents action"
            )
            return SyncDecision(
                action=SyncAction.SKIP,
                reason=reason,
                source_file=None,
                destination_file=destination_file,
                relative_path=path,
            )
