"""
Benchmark script to validate sync behavior for all 5 sync modes.

This script tests all sync modes using local filesystem operations
(simulating destination storage with a local directory):

1. TWO_WAY - Mirror every action in both directions
2. SOURCE_TO_DESTINATION - Mirror source to destination, ignore dest changes
3. SOURCE_BACKUP - Upload to destination, never delete or act on dest changes
4. DESTINATION_TO_SOURCE - Mirror dest to source, never act on source changes
5. DESTINATION_BACKUP - Download from destination, never delete at source

All operations use the syncengine library directly with a mock storage client
that uses local filesystem operations.
"""

import hashlib
import os
import shutil
import sys
import tempfile
import time
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Callable, Optional

# Add syncengine to path if running directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from syncengine.engine import SyncEngine
from syncengine.modes import SyncMode
from syncengine.pair import SyncPair
from syncengine.protocols import (
    DefaultOutputHandler,
    FileEntriesManagerProtocol,
    FileEntryProtocol,
)


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
    ) -> dict[str, Any]:
        """Create a folder in simulated cloud storage.

        Args:
            name: Folder name (can include path separators)
            parent_id: Parent folder ID (ignored, we use full paths)

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
    """Count files in a directory recursively, excluding trash directories."""
    if not directory.exists():
        return 0
    count = 0
    for f in directory.rglob("*"):
        if f.is_file():
            # Skip files in syncengine trash directories
            if ".syncengine.trash" not in str(f):
                count += 1
    return count


def test_source_backup(
    source_dir: Path, dest_dir: Path, output: DefaultOutputHandler
) -> bool:
    """Test SOURCE_BACKUP sync mode.

    SOURCE_BACKUP: Only upload data to the destination, never delete anything
    or act on destination changes.

    Args:
        source_dir: Source directory
        dest_dir: Simulated destination storage directory
        output: Output handler

    Returns:
        True if test passed
    """
    print("\n" + "=" * 80)
    print("TEST: SOURCE_BACKUP MODE")
    print("=" * 80)
    print("Behavior: Upload to destination, never delete or act on destination changes")

    # Setup
    source_src = source_dir / "source_backup_src"
    dest_storage = dest_dir / "source_backup_dest"

    # Create test files in source
    create_test_files(source_src, count=5, size_kb=1)

    # Create client and engine
    client = LocalStorageClient(dest_storage)
    factory = create_entries_manager_factory(client)
    engine = SyncEngine(client, factory, output=output)

    pair = SyncPair(
        source=source_src,
        destination="",  # Sync to root of destination storage
        sync_mode=SyncMode.SOURCE_BACKUP,
    )

    # First sync - should upload all files
    print("\n[SYNC] First sync (should upload 5 files)...")
    stats = engine.sync_pair(pair)
    print(f"[STATS] {stats}")

    if stats["uploads"] != 5:
        print(f"[FAIL] Expected 5 uploads, got {stats['uploads']}")
        return False

    # Verify files exist in destination
    dest_count = count_files(dest_storage)
    if dest_count != 5:
        print(f"[FAIL] Expected 5 files in destination, found {dest_count}")
        return False

    print("[PASS] First sync uploaded 5 files")

    # Second sync - should upload nothing (idempotency)
    print("\n[SYNC] Second sync (should upload 0 files - idempotency)...")
    stats = engine.sync_pair(pair)
    print(f"[STATS] {stats}")

    if stats["uploads"] != 0:
        print(f"[FAIL] Expected 0 uploads (idempotency), got {stats['uploads']}")
        return False

    print("[PASS] Second sync uploaded 0 files - idempotency confirmed")

    # Delete a source file - should NOT delete from destination (backup mode)
    deleted_file = source_src / "test_file_000.txt"
    deleted_file.unlink()
    print(f"\n[INFO] Deleted source file: {deleted_file.name}")

    print(
        "\n[SYNC] Third sync after source deletion "
        "(should NOT delete from destination)..."
    )
    stats = engine.sync_pair(pair)
    print(f"[STATS] {stats}")

    dest_count = count_files(dest_storage)
    if dest_count != 5:
        print(f"[FAIL] Destination should still have 5 files, found {dest_count}")
        return False

    print(
        "[PASS] SOURCE_BACKUP mode correctly preserved destination files "
        "after source delete"
    )

    return True


def test_source_to_destination(
    source_dir: Path, dest_dir: Path, output: DefaultOutputHandler
) -> bool:
    """Test SOURCE_TO_DESTINATION sync mode.

    SOURCE_TO_DESTINATION: Mirror every action done at source to destination but
    never act on destination changes.

    Args:
        source_dir: Source directory
        dest_dir: Simulated destination storage directory
        output: Output handler

    Returns:
        True if test passed
    """
    print("\n" + "=" * 80)
    print("TEST: SOURCE_TO_DESTINATION MODE")
    print("=" * 80)
    print("Behavior: Mirror source actions to destination, including deletions")

    # Setup
    source_src = source_dir / "source_to_dest_src"
    dest_storage = dest_dir / "source_to_dest_dest"

    # Create test files in source
    create_test_files(source_src, count=5, size_kb=1)

    # Create client and engine
    client = LocalStorageClient(dest_storage)
    factory = create_entries_manager_factory(client)
    engine = SyncEngine(client, factory, output=output)

    pair = SyncPair(
        source=source_src,
        destination="",
        sync_mode=SyncMode.SOURCE_TO_DESTINATION,
    )

    # First sync - should upload all files
    print("\n[SYNC] First sync (should upload 5 files)...")
    stats = engine.sync_pair(pair)
    print(f"[STATS] {stats}")

    if stats["uploads"] != 5:
        print(f"[FAIL] Expected 5 uploads, got {stats['uploads']}")
        return False

    print("[PASS] First sync uploaded 5 files")

    # Second sync - idempotency
    print("\n[SYNC] Second sync (should upload 0 files)...")
    stats = engine.sync_pair(pair)
    print(f"[STATS] {stats}")

    if stats["uploads"] != 0:
        print(f"[FAIL] Expected 0 uploads, got {stats['uploads']}")
        return False

    print("[PASS] Idempotency confirmed")

    # Delete a source file - SHOULD delete from destination
    deleted_file = source_src / "test_file_000.txt"
    deleted_file.unlink()
    print(f"\n[INFO] Deleted source file: {deleted_file.name}")

    print(
        "\n[SYNC] Third sync after source deletion (should delete from destination)..."
    )
    stats = engine.sync_pair(pair)
    print(f"[STATS] {stats}")

    if stats["deletes_remote"] != 1:
        print(f"[FAIL] Expected 1 destination delete, got {stats['deletes_remote']}")
        return False

    dest_count = count_files(dest_storage)
    if dest_count != 4:
        print(
            f"[FAIL] Destination should have 4 files after deletion, found {dest_count}"
        )
        return False

    print(
        "[PASS] SOURCE_TO_DESTINATION mode correctly mirrored "
        "source deletion to destination"
    )

    return True


def test_destination_backup(
    source_dir: Path, dest_dir: Path, output: DefaultOutputHandler
) -> bool:
    """Test DESTINATION_BACKUP sync mode.

    DESTINATION_BACKUP: Only download data from the destination, never delete anything
    or act on source changes.

    Args:
        source_dir: Source destination directory
        dest_dir: Simulated destination storage directory
        output: Output handler

    Returns:
        True if test passed
    """
    print("\n" + "=" * 80)
    print("TEST: DESTINATION_BACKUP MODE")
    print("=" * 80)
    print(
        "Behavior: Download from destination, never delete at source "
        "or act on source changes"
    )

    # Setup
    source_dest = source_dir / "dest_backup_source"
    dest_storage = dest_dir / "dest_backup_dest"

    # Create test files in "destination" first
    create_test_files(dest_storage, count=5, size_kb=1)

    # Create client and engine
    client = LocalStorageClient(dest_storage)
    factory = create_entries_manager_factory(client)
    engine = SyncEngine(client, factory, output=output)

    # Ensure source directory exists
    source_dest.mkdir(parents=True, exist_ok=True)

    pair = SyncPair(
        source=source_dest,
        destination="",
        sync_mode=SyncMode.DESTINATION_BACKUP,
    )

    # First sync - should download all files
    print("\n[SYNC] First sync (should download 5 files)...")
    stats = engine.sync_pair(pair)
    print(f"[STATS] {stats}")

    if stats["downloads"] != 5:
        print(f"[FAIL] Expected 5 downloads, got {stats['downloads']}")
        return False

    source_count = count_files(source_dest)
    if source_count != 5:
        print(f"[FAIL] Expected 5 source files, found {source_count}")
        return False

    print("[PASS] First sync downloaded 5 files")

    # Second sync - idempotency
    print("\n[SYNC] Second sync (should download 0 files)...")
    stats = engine.sync_pair(pair)
    print(f"[STATS] {stats}")

    if stats["downloads"] != 0:
        print(f"[FAIL] Expected 0 downloads, got {stats['downloads']}")
        return False

    print("[PASS] Idempotency confirmed")

    # Delete a destination file - should NOT delete at source (backup mode)
    dest_file = dest_storage / "test_file_000.txt"
    dest_file.unlink()
    print(f"\n[INFO] Deleted destination file: {dest_file.name}")

    print(
        "\n[SYNC] Third sync after destination deletion "
        "(should NOT delete at source)..."
    )
    stats = engine.sync_pair(pair)
    print(f"[STATS] {stats}")

    source_count = count_files(source_dest)
    if source_count != 5:
        print(f"[FAIL] Source should still have 5 files, found {source_count}")
        return False

    print(
        "[PASS] DESTINATION_BACKUP mode correctly preserved "
        "source files after destination delete"
    )

    return True


def test_destination_to_source(
    source_dir: Path, dest_dir: Path, output: DefaultOutputHandler
) -> bool:
    """Test DESTINATION_TO_SOURCE sync mode.

    DESTINATION_TO_SOURCE: Mirror every action done at destination to source but
    never act on source changes.

    Args:
        source_dir: Source destination directory
        dest_dir: Simulated destination storage directory
        output: Output handler

    Returns:
        True if test passed
    """
    print("\n" + "=" * 80)
    print("TEST: DESTINATION_TO_SOURCE MODE")
    print("=" * 80)
    print("Behavior: Mirror destination actions to source, including deletions")

    # Setup
    source_dest = source_dir / "dest_to_source_source"
    dest_storage = dest_dir / "dest_to_source_dest"

    # Create test files in "destination" first
    create_test_files(dest_storage, count=5, size_kb=1)

    # Create client and engine
    client = LocalStorageClient(dest_storage)
    factory = create_entries_manager_factory(client)
    engine = SyncEngine(client, factory, output=output)

    # Ensure source directory exists
    source_dest.mkdir(parents=True, exist_ok=True)

    pair = SyncPair(
        source=source_dest,
        destination="",
        sync_mode=SyncMode.DESTINATION_TO_SOURCE,
    )

    # First sync - should download all files
    print("\n[SYNC] First sync (should download 5 files)...")
    stats = engine.sync_pair(pair)
    print(f"[STATS] {stats}")

    if stats["downloads"] != 5:
        print(f"[FAIL] Expected 5 downloads, got {stats['downloads']}")
        return False

    print("[PASS] First sync downloaded 5 files")

    # Second sync - idempotency
    print("\n[SYNC] Second sync (should download 0 files)...")
    stats = engine.sync_pair(pair)
    print(f"[STATS] {stats}")

    if stats["downloads"] != 0:
        print(f"[FAIL] Expected 0 downloads, got {stats['downloads']}")
        return False

    print("[PASS] Idempotency confirmed")

    # Delete a destination file - SHOULD delete at source
    dest_file = dest_storage / "test_file_000.txt"
    dest_file.unlink()
    print(f"\n[INFO] Deleted destination file: {dest_file.name}")

    print("\n[SYNC] Third sync after destination deletion (should delete at source)...")
    stats = engine.sync_pair(pair)
    print(f"[STATS] {stats}")

    if stats["deletes_local"] != 1:
        print(f"[FAIL] Expected 1 source delete, got {stats['deletes_local']}")
        return False

    source_count = count_files(source_dest)
    if source_count != 4:
        print(f"[FAIL] Source should have 4 files after deletion, found {source_count}")
        return False

    print(
        "[PASS] DESTINATION_TO_SOURCE mode correctly mirrored "
        "destination deletion to source"
    )

    return True


def test_two_way(
    source_dir: Path, dest_dir: Path, output: DefaultOutputHandler
) -> bool:
    """Test TWO_WAY sync mode.

    TWO_WAY: Mirror every action in both directions.

    Args:
        source_dir: Source directory
        dest_dir: Simulated destination storage directory
        output: Output handler

    Returns:
        True if test passed
    """
    print("\n" + "=" * 80)
    print("TEST: TWO_WAY MODE")
    print("=" * 80)
    print("Behavior: Mirror actions in both directions")

    # Setup
    source_src = source_dir / "two_way_source"
    dest_storage = dest_dir / "two_way_dest"

    # Create test files in source
    create_test_files(source_src, count=3, size_kb=1)

    # Create client and engine
    client = LocalStorageClient(dest_storage)
    factory = create_entries_manager_factory(client)
    engine = SyncEngine(client, factory, output=output)

    pair = SyncPair(
        source=source_src,
        destination="",
        sync_mode=SyncMode.TWO_WAY,
    )

    # First sync - should upload all files
    print("\n[SYNC] First sync (should upload 3 files)...")
    stats = engine.sync_pair(pair)
    print(f"[STATS] {stats}")

    if stats["uploads"] != 3:
        print(f"[FAIL] Expected 3 uploads, got {stats['uploads']}")
        return False

    print("[PASS] First sync uploaded 3 files")

    # Now add files directly to "destination"
    print("\n[INFO] Adding 2 files directly to destination...")
    (dest_storage / "dest_file_001.txt").write_text("Destination content 1")
    (dest_storage / "dest_file_002.txt").write_text("Destination content 2")

    # Second sync - should download destination files
    print("\n[SYNC] Second sync (should download 2 destination files)...")
    stats = engine.sync_pair(pair)
    print(f"[STATS] {stats}")

    if stats["downloads"] != 2:
        print(f"[FAIL] Expected 2 downloads, got {stats['downloads']}")
        return False

    source_count = count_files(source_src)
    if source_count != 5:
        print(f"[FAIL] Expected 5 source files, found {source_count}")
        return False

    print("[PASS] Second sync downloaded destination files")

    # Third sync - idempotency
    print("\n[SYNC] Third sync (should do nothing)...")
    stats = engine.sync_pair(pair)
    print(f"[STATS] {stats}")

    if stats["uploads"] != 0 or stats["downloads"] != 0:
        print(
            f"[FAIL] Expected no actions, got uploads={stats['uploads']}, "
            f"downloads={stats['downloads']}"
        )
        return False

    print("[PASS] TWO_WAY mode works correctly")

    return True


def main():
    """Main benchmark function."""
    print("\n" + "=" * 80)
    print("SYNCENGINE SYNC MODE BENCHMARKS")
    print("=" * 80)
    print("\nThis benchmark tests all 5 sync modes using local filesystem operations.")
    print("A local directory simulates destination storage for testing purposes.\n")

    # Create unique temporary directory
    test_uuid = str(uuid.uuid4())[:8]

    with tempfile.TemporaryDirectory(prefix=f"syncengine_bench_{test_uuid}_") as tmp:
        base_dir = Path(tmp)
        source_dir = base_dir / "source"
        dest_dir = base_dir / "destination"

        source_dir.mkdir(parents=True, exist_ok=True)
        dest_dir.mkdir(parents=True, exist_ok=True)

        print(f"[INFO] Test directory: {base_dir}")
        print(f"[INFO] Source storage: {source_dir}")
        print(f"[INFO] Destination storage: {dest_dir}")

        # Create output handler
        output = DefaultOutputHandler(quiet=True)

        results = {}

        try:
            # Test 1: SOURCE_BACKUP
            results["SOURCE_BACKUP"] = test_source_backup(source_dir, dest_dir, output)

            # Test 2: SOURCE_TO_DESTINATION
            results["SOURCE_TO_DESTINATION"] = test_source_to_destination(
                source_dir, dest_dir, output
            )

            # Test 3: DESTINATION_BACKUP
            results["DESTINATION_BACKUP"] = test_destination_backup(
                source_dir, dest_dir, output
            )

            # Test 4: DESTINATION_TO_SOURCE
            results["DESTINATION_TO_SOURCE"] = test_destination_to_source(
                source_dir, dest_dir, output
            )

            # Test 5: TWO_WAY
            results["TWO_WAY"] = test_two_way(source_dir, dest_dir, output)

        except KeyboardInterrupt:
            print("\n\n[WARN] Benchmark interrupted by user")
            sys.exit(130)
        except Exception as e:
            print(f"\n\n[ERROR] Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)

        # Summary
        print("\n" + "=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)

        all_passed = True
        for mode, passed in results.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {status} {mode}")
            if not passed:
                all_passed = False

        print("=" * 80)

        if all_passed:
            print("[SUCCESS] All sync mode benchmarks passed!")
            sys.exit(0)
        else:
            print("[FAILURE] Some benchmarks failed")
            sys.exit(1)


if __name__ == "__main__":
    main()
