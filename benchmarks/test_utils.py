"""
Shared utilities and mock classes for benchmarking sync operations.

This module provides mock implementations of storage clients and file entries
that simulate cloud storage using local filesystem operations. These utilities
are used across all benchmark scripts to test sync behavior without requiring
actual cloud storage access.
"""

import hashlib
import os
import shutil
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Callable, Optional

from syncengine.protocols import FileEntriesManagerProtocol, FileEntryProtocol


class LocalFileEntry:
    """A file entry representing a local file (simulating cloud storage)."""

    def __init__(self, path: Path, relative_path: str, entry_id: int):
        """Initialize a local file entry.

        Args:
            path: Absolute path to the file
            relative_path: Relative path within the storage
            entry_id: Unique identifier for this entry
        """
        self._path = path
        self._relative_path = relative_path
        self._id = entry_id
        self._stat = path.stat() if path.exists() else None

    @property
    def id(self) -> int:
        """Unique identifier for the file entry."""
        return self._id

    @property
    def type(self) -> str:
        """Entry type: 'file' or 'folder'."""
        return "folder" if self._path.is_dir() else "file"

    @property
    def file_size(self) -> int:
        """File size in bytes."""
        return self._stat.st_size if self._stat and not self._path.is_dir() else 0

    @property
    def hash(self) -> str:
        """Content hash (MD5)."""
        if self._path.is_dir() or not self._path.exists():
            return ""
        with open(self._path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    @property
    def name(self) -> str:
        """File or folder name."""
        return self._path.name

    @property
    def updated_at(self) -> Optional[str]:
        """ISO timestamp of last modification."""
        if self._stat:
            return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self._stat.st_mtime))
        return None


class LocalStorageClient:
    """A mock cloud client that uses local filesystem operations.

    This simulates cloud storage by using a local directory as the "cloud".
    """

    def __init__(self, storage_root: Path):
        """Initialize the local storage client.

        Args:
            storage_root: Root directory that simulates cloud storage
        """
        self.storage_root = storage_root
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self._next_id = 1
        self._id_map: dict[str, int] = {}  # path -> id mapping

    def _get_id(self, path: str) -> int:
        """Get or create an ID for a path."""
        if path not in self._id_map:
            self._id_map[path] = self._next_id
            self._next_id += 1
        return self._id_map[path]

    def upload_file(
        self,
        file_path: Path,
        relative_path: str,
        storage_id: int = 0,
        chunk_size: int = 1024 * 1024,
        use_multipart_threshold: int = 10 * 1024 * 1024,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> dict[str, Any]:
        """Upload a local file to the simulated cloud storage.

        Args:
            file_path: Local path to the file to upload
            relative_path: Relative path in cloud storage
            storage_id: Storage identifier (ignored for local storage)
            chunk_size: Chunk size (ignored for local storage)
            use_multipart_threshold: Multipart threshold (ignored)
            progress_callback: Progress callback

        Returns:
            Upload result with file ID and status
        """
        dest_path = self.storage_root / relative_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, dest_path)

        file_id = self._get_id(relative_path)

        if progress_callback:
            size = file_path.stat().st_size
            progress_callback(size, size)

        return {"id": file_id, "name": dest_path.name, "status": "success"}

    def download_file(
        self,
        hash_value: str,
        output_path: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Path:
        """Download a file from simulated cloud storage.

        Note: For this mock, we need to find the file by hash which is inefficient.
        In real usage, we'd use the file path directly.

        Args:
            hash_value: Content hash of the file
            output_path: Local path where file should be saved
            progress_callback: Progress callback

        Returns:
            Path where file was saved
        """
        # Search for file with matching hash in storage
        for file_path in self.storage_root.rglob("*"):
            if file_path.is_file():
                with open(file_path, "rb") as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                if file_hash == hash_value:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, output_path)

                    if progress_callback:
                        size = file_path.stat().st_size
                        progress_callback(size, size)

                    return output_path

        raise FileNotFoundError(f"No file with hash {hash_value} found in storage")

    def delete_file_entries(
        self,
        entry_ids: list[int],
        delete_forever: bool = False,
    ) -> dict[str, Any]:
        """Delete file entries from simulated cloud storage.

        Args:
            entry_ids: List of entry IDs to delete
            delete_forever: If True, permanently delete

        Returns:
            Delete result
        """
        # Find paths by ID and delete them
        deleted = 0
        for path, entry_id in list(self._id_map.items()):
            if entry_id in entry_ids:
                full_path = self.storage_root / path
                if full_path.exists():
                    if full_path.is_dir():
                        shutil.rmtree(full_path)
                    else:
                        full_path.unlink()
                    deleted += 1

        return {"deleted": deleted, "status": "success"}

    def create_folder(
        self,
        name: str,
        parent_id: Optional[int] = None,
        storage_id: int = 0,
    ) -> dict[str, Any]:
        """Create a folder in simulated cloud storage.

        Args:
            name: Folder name (can include path separators)
            parent_id: Parent folder ID (ignored, we use full paths)
            storage_id: Storage identifier (ignored in mock)

        Returns:
            Dictionary with status and id
        """
        folder_path = self.storage_root / name
        folder_path.mkdir(parents=True, exist_ok=True)

        folder_id = self._get_id(name)
        return {"status": "success", "id": folder_id}

    def resolve_path_to_id(
        self,
        path: str,
        storage_id: int = 0,
    ) -> Optional[int]:
        """Resolve a path to its folder ID.

        Args:
            path: Path to resolve
            storage_id: Storage identifier (ignored)

        Returns:
            Folder ID if found, None otherwise
        """
        full_path = self.storage_root / path
        if full_path.exists():
            return self._get_id(path)
        return None

    def move_file_entries(
        self,
        entry_ids: list[int],
        destination_id: int,
    ) -> dict[str, Any]:
        """Move file entries to a different folder.

        Args:
            entry_ids: List of entry IDs to move
            destination_id: Destination folder ID

        Returns:
            Move result
        """
        # Find destination path by ID
        dest_path = None
        for path, entry_id in self._id_map.items():
            if entry_id == destination_id:
                dest_path = self.storage_root / path
                break

        if not dest_path:
            return {"status": "error", "message": "Destination not found"}

        moved = 0
        for path, entry_id in list(self._id_map.items()):
            if entry_id in entry_ids:
                src_path = self.storage_root / path
                if src_path.exists():
                    new_path = dest_path / src_path.name
                    shutil.move(str(src_path), str(new_path))
                    moved += 1

        return {"moved": moved, "status": "success"}

    def update_file_entry(
        self,
        entry_id: int,
        name: str,
    ) -> dict[str, Any]:
        """Update a file entry (rename).

        Args:
            entry_id: ID of entry to update
            name: New name for the entry

        Returns:
            Update result
        """
        for path, eid in list(self._id_map.items()):
            if eid == entry_id:
                src_path = self.storage_root / path
                if src_path.exists():
                    new_path = src_path.parent / name
                    src_path.rename(new_path)
                    # Update ID map
                    new_relative = str(new_path.relative_to(self.storage_root))
                    self._id_map[new_relative] = entry_id
                    del self._id_map[path]
                    return {"status": "success", "name": name}

        return {"status": "error", "message": "Entry not found"}


class LocalEntriesManager:
    """Manager for file entries in local storage (simulating cloud)."""

    def __init__(self, client: LocalStorageClient, storage_id: int = 0):
        """Initialize the entries manager.

        Args:
            client: Local storage client
            storage_id: Storage identifier (ignored)
        """
        self.client = client

    def find_folder_by_name(
        self, name: str, parent_id: int = 0
    ) -> Optional[FileEntryProtocol]:
        """Find a folder by name within the storage.

        Args:
            name: Folder name to find
            parent_id: Parent folder ID (ignored, we search from root)

        Returns:
            FileEntry if found, None otherwise
        """
        folder_path = self.client.storage_root / name
        if folder_path.exists() and folder_path.is_dir():
            return LocalFileEntry(folder_path, name, self.client._get_id(name))
        return None

    def get_all_recursive(
        self,
        folder_id: Optional[int],
        path_prefix: str,
    ) -> list[tuple[FileEntryProtocol, str]]:
        """Get all entries recursively under a folder.

        Args:
            folder_id: Folder ID to start from (ignored, we use path_prefix)
            path_prefix: Prefix path to start from

        Returns:
            List of (entry, relative_path) tuples
        """
        results: list[tuple[FileEntryProtocol, str]] = []
        start_path = (
            self.client.storage_root / path_prefix
            if path_prefix
            else self.client.storage_root
        )

        if not start_path.exists():
            return []

        for file_path in start_path.rglob("*"):
            if file_path.is_file():
                relative = str(file_path.relative_to(self.client.storage_root))
                entry: FileEntryProtocol = LocalFileEntry(
                    file_path, relative, self.client._get_id(relative)
                )
                results.append((entry, relative))

        return results

    def iter_all_recursive(
        self,
        folder_id: Optional[int],
        path_prefix: str,
        batch_size: int,
    ) -> Iterator[list[tuple[FileEntryProtocol, str]]]:
        """Iterate over entries recursively in batches.

        Args:
            folder_id: Folder ID to start from
            path_prefix: Prefix path to start from
            batch_size: Number of entries per batch

        Yields:
            Batches of (entry, relative_path) tuples
        """
        all_entries = self.get_all_recursive(folder_id, path_prefix)
        for i in range(0, len(all_entries), batch_size):
            yield all_entries[i : i + batch_size]


def create_entries_manager_factory(
    client: LocalStorageClient,
) -> Callable[[Any, int], FileEntriesManagerProtocol]:
    """Create an entries manager factory for the local storage client.

    Args:
        client: Local storage client

    Returns:
        Factory function
    """

    def factory(cli: Any, storage_id: int) -> FileEntriesManagerProtocol:
        return LocalEntriesManager(client, storage_id)

    return factory


def create_test_files(directory: Path, count: int = 10, size_kb: int = 1) -> list[Path]:
    """Create test files with random content.

    Args:
        directory: Directory to create files in
        count: Number of files to create
        size_kb: Size of each file in KB

    Returns:
        List of created file paths
    """
    directory.mkdir(parents=True, exist_ok=True)
    created_files = []

    print(f"\n[INFO] Creating {count} test files ({size_kb}KB each) in {directory}")

    for i in range(count):
        file_path = directory / f"test_file_{i:03d}.txt"
        # Create random content
        content = f"Test file {i}\n" + (os.urandom(size_kb * 1024 - 20).hex())
        file_path.write_text(content)
        created_files.append(file_path)
        print(f"  [OK] Created: {file_path.name}")

    return created_files


def count_files(directory: Path) -> int:
    """Count files in a directory recursively, excluding trash directories.

    Args:
        directory: Directory to count files in

    Returns:
        Number of files found (excluding trash directories)
    """
    if not directory.exists():
        return 0
    count = 0
    for f in directory.rglob("*"):
        if f.is_file():
            # Skip files in syncengine trash directories
            if ".syncengine.trash" not in str(f):
                count += 1
    return count


def modify_file_with_timestamp(
    file_path: Path, content: str, timestamp_offset: float = 3.0
) -> None:
    """Modify a file and set its mtime to be offset from current time.

    This ensures the file has a clearly different timestamp that won't trigger
    conflict detection due to the 2-second tolerance in the sync engine.

    Args:
        file_path: Path to the file to modify
        content: New content for the file
        timestamp_offset: Seconds to add to current time for the file's mtime.
                         Default 3.0 ensures it's > 2 second threshold.
    """
    import os
    import time

    # Write the new content
    file_path.write_text(content)

    # Set the mtime to be clearly in the future relative to any previous sync
    # This avoids the < 2 second conflict detection window
    new_time = time.time() + timestamp_offset
    os.utime(file_path, (new_time, new_time))  # (atime, mtime)
