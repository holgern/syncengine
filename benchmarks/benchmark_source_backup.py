"""
Benchmark script for SOURCE_BACKUP sync mode.

SOURCE_BACKUP mode only uploads data to the destination and never deletes
anything or acts on destination changes. It's designed for backup scenarios
where you want to preserve everything that was ever uploaded.
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


def benchmark_source_backup():
    """Benchmark SOURCE_BACKUP sync mode with various scenarios."""
    print("\n" + "=" * 80)
    print("BENCHMARK: SOURCE_BACKUP SYNC MODE")
    print("=" * 80)
    print("Mode: Upload to destination, never delete or act on destination changes")
    print("=" * 80)

    test_uuid = str(uuid.uuid4())[:8]

    with tempfile.TemporaryDirectory(prefix=f"bench_src_backup_{test_uuid}_") as tmp:
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
            sync_mode=SyncMode.SOURCE_BACKUP,
        )

        # Scenario 1: Initial backup
        print("\n" + "-" * 80)
        print("SCENARIO 1: Initial backup from source")
        print("-" * 80)
        create_test_files(source_dir, count=20, size_kb=5)

        print("\n[SYNC] First sync - backing up source files...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert stats["uploads"] == 20, f"Expected 20 uploads, got {stats['uploads']}"
        assert count_files(dest_storage) == 20
        print("[✓] Successfully backed up 20 files")

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
        assert stats["uploads"] == 0
        print("[✓] Idempotency confirmed - no unnecessary uploads")

        # Scenario 3: Add new files at source
        print("\n" + "-" * 80)
        print("SCENARIO 3: Add new files at source")
        print("-" * 80)
        print("[INFO] Creating 5 new files at source...")
        for i in range(20, 25):
            new_file = source_dir / f"test_file_{i:03d}.txt"
            new_file.write_text(f"New file {i}\n" + os.urandom(5 * 1024).hex())

        print("\n[SYNC] Syncing to upload new files...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert stats["uploads"] == 5, f"Expected 5 uploads, got {stats['uploads']}"
        assert count_files(dest_storage) == 25
        print("[✓] Successfully uploaded 5 new files")

        # Scenario 4: Modify file at source
        print("\n" + "-" * 80)
        print("SCENARIO 4: Modify file at source")
        print("-" * 80)
        modified_file = source_dir / "test_file_000.txt"
        print(f"[INFO] Modifying {modified_file.name}...")
        modify_file_with_timestamp(
            modified_file, "Modified backup content\n" + os.urandom(5 * 1024).hex()
        )

        print("\n[SYNC] Syncing to upload modified file...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert stats["uploads"] == 1, f"Expected 1 upload, got {stats['uploads']}"
        print("[✓] Successfully uploaded modified file")

        # Scenario 5: Delete file at source (should NOT delete at destination)
        print("\n" + "-" * 80)
        print("SCENARIO 5: Delete file at source (backup preserved)")
        print("-" * 80)
        deleted_file = source_dir / "test_file_001.txt"
        print(f"[INFO] Deleting {deleted_file.name} from source...")
        deleted_file.unlink()

        print("\n[SYNC] Syncing (should NOT delete from destination)...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert (
            stats["deletes_remote"] == 0
        ), f"Expected 0 remote deletes, got {stats['deletes_remote']}"
        assert count_files(dest_storage) == 25  # File still exists in backup
        assert (dest_storage / "test_file_001.txt").exists()
        print("[✓] Backup correctly preserved - file NOT deleted from destination")

        # Scenario 6: Delete multiple files at source
        print("\n" + "-" * 80)
        print("SCENARIO 6: Delete multiple files at source")
        print("-" * 80)
        print("[INFO] Deleting 5 files from source...")
        for i in range(2, 7):
            (source_dir / f"test_file_{i:03d}.txt").unlink()

        print("\n[SYNC] Syncing (should NOT delete from destination)...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert stats["deletes_remote"] == 0
        assert count_files(dest_storage) == 25  # All files still in backup
        print("[✓] All 25 files preserved in backup despite source deletions")

        # Scenario 7: Add file at destination (should be ignored)
        print("\n" + "-" * 80)
        print("SCENARIO 7: Add file at destination (should be ignored)")
        print("-" * 80)
        dest_file = dest_storage / "dest_added_file.txt"
        print(f"[INFO] Creating {dest_file.name} at destination...")
        dest_file.write_text("Destination added content")

        print("\n[SYNC] Syncing (should ignore destination changes)...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert stats["downloads"] == 0
        assert not (source_dir / "dest_added_file.txt").exists()
        print("[✓] Destination changes correctly ignored")

        # Scenario 8: Delete file at destination (should be re-uploaded)
        print("\n" + "-" * 80)
        print("SCENARIO 8: Delete file at destination (should be re-uploaded)")
        print("-" * 80)
        dest_file = dest_storage / "test_file_010.txt"
        print(f"[INFO] Deleting {dest_file.name} from destination...")
        dest_file.unlink()

        print("\n[SYNC] Syncing (should re-upload to maintain backup)...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert stats["uploads"] == 1, f"Expected 1 upload, got {stats['uploads']}"
        assert (dest_storage / "test_file_010.txt").exists()
        print("[✓] Successfully re-uploaded deleted file to maintain backup")

        # Final verification
        print("\n" + "-" * 80)
        print("FINAL VERIFICATION")
        print("-" * 80)
        source_count = count_files(source_dir)
        dest_count = count_files(dest_storage)
        print(f"[INFO] Source files: {source_count}")
        print(f"[INFO] Destination files (backup): {dest_count}")
        assert source_count == 19  # Original 20 + 5 new - 6 deleted
        assert dest_count == 26  # All 25 original + dest_added_file.txt
        print("[✓] Backup preserved all uploaded files despite source deletions")

        print("\n" + "=" * 80)
        print("[SUCCESS] SOURCE_BACKUP mode benchmark completed successfully!")
        print("=" * 80)


if __name__ == "__main__":
    try:
        benchmark_source_backup()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAIL] Assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
