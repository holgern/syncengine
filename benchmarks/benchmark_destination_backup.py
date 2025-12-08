"""
Benchmark script for DESTINATION_BACKUP sync mode.

DESTINATION_BACKUP mode only downloads data from the destination and never deletes
anything or acts on source changes. It's designed for downloading backups where
you want to preserve everything that was ever downloaded.
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


def benchmark_destination_backup():
    """Benchmark DESTINATION_BACKUP sync mode with various scenarios."""
    print("\n" + "=" * 80)
    print("BENCHMARK: DESTINATION_BACKUP SYNC MODE")
    print("=" * 80)
    print("Mode: Download from destination, never delete or act on source changes")
    print("=" * 80)

    test_uuid = str(uuid.uuid4())[:8]

    with tempfile.TemporaryDirectory(prefix=f"bench_dst_backup_{test_uuid}_") as tmp:
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
            sync_mode=SyncMode.DESTINATION_BACKUP,
        )

        # Scenario 1: Initial backup download
        print("\n" + "-" * 80)
        print("SCENARIO 1: Initial backup download from destination")
        print("-" * 80)
        create_test_files(dest_storage, count=20, size_kb=5)

        print("\n[SYNC] First sync - downloading backup files...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert (
            stats["downloads"] == 20
        ), f"Expected 20 downloads, got {stats['downloads']}"
        assert count_files(source_dir) == 20
        print("[✓] Successfully downloaded 20 backup files")

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

        # Scenario 3: Add new files at destination
        print("\n" + "-" * 80)
        print("SCENARIO 3: Add new files at destination")
        print("-" * 80)
        print("[INFO] Creating 5 new files at destination...")
        for i in range(20, 25):
            new_file = dest_storage / f"test_file_{i:03d}.txt"
            new_file.write_text(f"New backup file {i}\n" + os.urandom(5 * 1024).hex())

        print("\n[SYNC] Syncing to download new backup files...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert (
            stats["downloads"] == 5
        ), f"Expected 5 downloads, got {stats['downloads']}"
        assert count_files(source_dir) == 25
        print("[✓] Successfully downloaded 5 new backup files")

        # Scenario 4: Modify file at destination
        print("\n" + "-" * 80)
        print("SCENARIO 4: Modify file at destination")
        print("-" * 80)
        modified_file = dest_storage / "test_file_000.txt"
        print(f"[INFO] Modifying {modified_file.name} at destination...")
        modify_file_with_timestamp(
            modified_file, "Modified backup content\n" + os.urandom(5 * 1024).hex()
        )

        print("\n[SYNC] Syncing to download modified backup file...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert stats["downloads"] == 1, f"Expected 1 download, got {stats['downloads']}"
        print("[✓] Successfully downloaded modified backup file")

        # Scenario 5: Delete file at destination (should NOT delete at source)
        print("\n" + "-" * 80)
        print("SCENARIO 5: Delete file at destination (backup preserved at source)")
        print("-" * 80)
        deleted_file = dest_storage / "test_file_001.txt"
        print(f"[INFO] Deleting {deleted_file.name} from destination...")
        deleted_file.unlink()

        print("\n[SYNC] Syncing (should NOT delete from source)...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert (
            stats["deletes_local"] == 0
        ), f"Expected 0 local deletes, got {stats['deletes_local']}"
        assert count_files(source_dir) == 25  # File still exists in local backup
        assert (source_dir / "test_file_001.txt").exists()
        print("[✓] Local backup correctly preserved - file NOT deleted from source")

        # Scenario 6: Delete multiple files at destination
        print("\n" + "-" * 80)
        print("SCENARIO 6: Delete multiple files at destination")
        print("-" * 80)
        print("[INFO] Deleting 5 files from destination...")
        for i in range(2, 7):
            (dest_storage / f"test_file_{i:03d}.txt").unlink()

        print("\n[SYNC] Syncing (should NOT delete from source)...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert stats["deletes_local"] == 0
        assert count_files(source_dir) == 25  # All files still in local backup
        print(
            "[✓] All 25 files preserved in local backup despite destination deletions"
        )

        # Scenario 7: Add file at source (should be ignored)
        print("\n" + "-" * 80)
        print("SCENARIO 7: Add file at source (should be ignored)")
        print("-" * 80)
        source_file = source_dir / "source_added_file.txt"
        print(f"[INFO] Creating {source_file.name} at source...")
        source_file.write_text("Source added content")

        print("\n[SYNC] Syncing (should ignore source changes)...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert stats["uploads"] == 0
        assert not (dest_storage / "source_added_file.txt").exists()
        print("[✓] Source changes correctly ignored")

        # Scenario 8: Delete file at source (should be re-downloaded)
        print("\n" + "-" * 80)
        print("SCENARIO 8: Delete file at source (should be re-downloaded)")
        print("-" * 80)
        source_file = source_dir / "test_file_010.txt"
        print(f"[INFO] Deleting {source_file.name} from source...")
        source_file.unlink()

        print("\n[SYNC] Syncing (should re-download to maintain backup)...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert stats["downloads"] == 1, f"Expected 1 download, got {stats['downloads']}"
        assert (source_dir / "test_file_010.txt").exists()
        print("[✓] Successfully re-downloaded deleted file to maintain backup")

        # Scenario 9: Modify file at source - should be skipped (backup mode)
        print("\n" + "-" * 80)
        print("SCENARIO 9: Modify file at source (should be skipped)")
        print("-" * 80)
        source_file = source_dir / "test_file_011.txt"
        print(f"[INFO] Modifying {source_file.name} at source...")
        # Use modify_file_with_timestamp to set it in the future
        modify_file_with_timestamp(
            source_file, "Modified at source - should be skipped"
        )

        print("\n[SYNC] Syncing (should skip - backup mode ignores source changes)...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        # In DESTINATION_BACKUP mode, source modifications are ignored
        assert (
            stats["downloads"] == 0
        ), f"Expected 0 downloads, got {stats['downloads']}"
        assert stats["uploads"] == 0, f"Expected 0 uploads, got {stats['uploads']}"
        print("[✓] Source modification correctly ignored in backup mode")

        # Final verification
        print("\n" + "-" * 80)
        print("FINAL VERIFICATION")
        print("-" * 80)
        source_count = count_files(source_dir)
        dest_count = count_files(dest_storage)
        print(f"[INFO] Source files (backup): {source_count}")
        print(f"[INFO] Destination files: {dest_count}")
        assert source_count == 26  # All 25 backup files + source_added_file.txt
        assert dest_count == 19  # Original 20 + 5 new - 6 deleted
        print(
            "[✓] Local backup preserved all downloaded files "
            "despite destination deletions"
        )

        print("\n" + "=" * 80)
        print("[SUCCESS] DESTINATION_BACKUP mode benchmark completed successfully!")
        print("=" * 80)


if __name__ == "__main__":
    try:
        benchmark_destination_backup()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAIL] Assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
