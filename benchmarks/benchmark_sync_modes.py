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

import sys
import tempfile
import uuid
from pathlib import Path

# Add syncengine to path if running directly
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import utility classes and functions from test_utils module
from benchmarks.test_utils import (
    LocalStorageClient,
    count_files,
    create_entries_manager_factory,
    create_test_files,
)
from syncengine.engine import SyncEngine
from syncengine.modes import SyncMode
from syncengine.pair import SyncPair
from syncengine.protocols import DefaultOutputHandler


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
