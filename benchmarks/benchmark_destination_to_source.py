"""
Benchmark script for DESTINATION_TO_SOURCE sync mode.

DESTINATION_TO_SOURCE mode mirrors every action done at destination to source,
including deletions. Source changes are ignored and never propagated to destination.
"""

import os
import sys
import tempfile
import time
import uuid
from pathlib import Path

# Add syncengine to path if running directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmarks.test_utils import (
    LocalStorageClient,
    count_files,
    create_entries_manager_factory,
    create_test_files,
    modify_file_with_timestamp,
)
from syncengine.engine import SyncEngine
from syncengine.modes import SyncMode
from syncengine.pair import SyncPair
from syncengine.protocols import DefaultOutputHandler


def benchmark_destination_to_source():
    """Benchmark DESTINATION_TO_SOURCE sync mode with various scenarios."""
    print("\n" + "=" * 80)
    print("BENCHMARK: DESTINATION_TO_SOURCE SYNC MODE")
    print("=" * 80)
    print("Mode: Mirror destination actions to source, ignore source changes")
    print("=" * 80)

    test_uuid = str(uuid.uuid4())[:8]

    with tempfile.TemporaryDirectory(prefix=f"bench_d2s_{test_uuid}_") as tmp:
        base_dir = Path(tmp)
        source_dir = base_dir / "source"
        dest_storage = base_dir / "destination"

        source_dir.mkdir(parents=True, exist_ok=True)
        dest_storage.mkdir(parents=True, exist_ok=True)

        print(f"\n[INFO] Test directory: {base_dir}")

        # Create client and engine
        client = LocalStorageClient(dest_storage)
        factory = create_entries_manager_factory(client)
        output = DefaultOutputHandler(quiet=True)
        engine = SyncEngine(client, factory, output=output)

        pair = SyncPair(
            source=source_dir,
            destination="",
            sync_mode=SyncMode.DESTINATION_TO_SOURCE,
        )

        # Scenario 1: Initial download from destination
        print("\n" + "-" * 80)
        print("SCENARIO 1: Initial download from destination")
        print("-" * 80)
        create_test_files(dest_storage, count=15, size_kb=10)

        print("\n[SYNC] First sync - downloading destination files...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert (
            stats["downloads"] == 15
        ), f"Expected 15 downloads, got {stats['downloads']}"
        assert count_files(source_dir) == 15
        print("[✓] Successfully downloaded 15 files")

        # Scenario 2: Idempotency check
        print("\n" + "-" * 80)
        print("SCENARIO 2: Idempotency check")
        print("-" * 80)
        print("\n[SYNC] Syncing again (should do nothing)...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert stats["downloads"] == 0
        print("[✓] Idempotency confirmed - no unnecessary downloads")

        # Scenario 3: Add file at destination
        print("\n" + "-" * 80)
        print("SCENARIO 3: Add new file at destination")
        print("-" * 80)
        new_file = dest_storage / "new_dest_file.txt"
        print(f"[INFO] Creating {new_file.name} at destination...")
        new_file.write_text("New destination file\n" + os.urandom(10 * 1024).hex())

        print("\n[SYNC] Syncing to download new file...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert stats["downloads"] == 1, f"Expected 1 download, got {stats['downloads']}"
        assert count_files(source_dir) == 16
        assert (source_dir / "new_dest_file.txt").exists()
        print("[✓] Successfully downloaded new file")

        # Scenario 4: Modify file at destination
        print("\n" + "-" * 80)
        print("SCENARIO 4: Modify file at destination")
        print("-" * 80)
        modified_file = dest_storage / "test_file_000.txt"
        print(f"[INFO] Modifying {modified_file.name} at destination...")
        modify_file_with_timestamp(
            modified_file, "Modified at destination\n" + os.urandom(10 * 1024).hex()
        )

        print("\n[SYNC] Syncing to download modified file...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert stats["downloads"] == 1, f"Expected 1 download, got {stats['downloads']}"
        print("[✓] Successfully downloaded modified file")

        # Scenario 5: Delete file at destination (should delete at source)
        print("\n" + "-" * 80)
        print("SCENARIO 5: Delete file at destination")
        print("-" * 80)
        deleted_file = dest_storage / "test_file_001.txt"
        print(f"[INFO] Deleting {deleted_file.name} from destination...")
        deleted_file.unlink()

        print("\n[SYNC] Syncing to propagate deletion to source...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert (
            stats["deletes_local"] == 1
        ), f"Expected 1 local delete, got {stats['deletes_local']}"
        assert count_files(source_dir) == 15
        assert not (source_dir / "test_file_001.txt").exists()
        print("[✓] Successfully propagated deletion to source")

        # Scenario 6: Add file at source (should be ignored)
        print("\n" + "-" * 80)
        print("SCENARIO 6: Add file at source (should be ignored)")
        print("-" * 80)
        source_file = source_dir / "source_only_file.txt"
        print(f"[INFO] Creating {source_file.name} at source...")
        source_file.write_text("Source only content")

        print("\n[SYNC] Syncing (should ignore source changes)...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert stats["uploads"] == 0, f"Expected 0 uploads, got {stats['uploads']}"
        assert not (dest_storage / "source_only_file.txt").exists()
        print("[✓] Source changes correctly ignored")

        # Scenario 7: Delete file at source (should be re-downloaded)
        print("\n" + "-" * 80)
        print("SCENARIO 7: Delete file at source (should be re-downloaded)")
        print("-" * 80)
        source_file = source_dir / "test_file_002.txt"
        print(f"[INFO] Deleting {source_file.name} from source...")
        source_file.unlink()

        print("\n[SYNC] Syncing (should re-download deleted file)...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert stats["downloads"] == 1, f"Expected 1 download, got {stats['downloads']}"
        assert (source_dir / "test_file_002.txt").exists()
        print("[✓] Successfully re-downloaded deleted file")

        # Scenario 8: Delete multiple files at destination
        print("\n" + "-" * 80)
        print("SCENARIO 8: Delete multiple files at destination")
        print("-" * 80)
        print("[INFO] Deleting 3 files from destination...")
        for i in range(3, 6):
            (dest_storage / f"test_file_{i:03d}.txt").unlink()

        print("\n[SYNC] Syncing to propagate deletions to source...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert (
            stats["deletes_local"] == 3
        ), f"Expected 3 local deletes, got {stats['deletes_local']}"
        actual_count = count_files(source_dir)
        assert (
            actual_count == 12
        ), f"Expected 12 files, got {actual_count}"  # 15 - 3 deletions
        print("[✓] Successfully propagated 3 deletions to source")

        # Final verification
        print("\n" + "-" * 80)
        print("FINAL VERIFICATION")
        print("-" * 80)
        source_count = count_files(source_dir)
        dest_count = count_files(dest_storage)
        print(f"[INFO] Source files: {source_count}")
        print(f"[INFO] Destination files: {dest_count}")
        # After all operations: 12 files remain at both locations
        assert source_count == 12
        assert dest_count == 12
        print("[✓] Destination correctly mirrored to source")

        print("\n" + "=" * 80)
        print("[SUCCESS] DESTINATION_TO_SOURCE mode benchmark completed successfully!")
        print("=" * 80)


if __name__ == "__main__":
    try:
        benchmark_destination_to_source()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAIL] Assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
