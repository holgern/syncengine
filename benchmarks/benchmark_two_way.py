"""
Benchmark script for TWO_WAY sync mode.

TWO_WAY mode mirrors every action in both directions - changes from source
are uploaded to destination, and changes from destination are downloaded to source.
Both deletions and additions are synchronized bidirectionally.
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


def benchmark_two_way():
    """Benchmark TWO_WAY sync mode with various scenarios."""
    print("\n" + "=" * 80)
    print("BENCHMARK: TWO_WAY SYNC MODE")
    print("=" * 80)
    print("Mode: Mirror every action in both directions")
    print("=" * 80)

    test_uuid = str(uuid.uuid4())[:8]

    with tempfile.TemporaryDirectory(prefix=f"bench_two_way_{test_uuid}_") as tmp:
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
            sync_mode=SyncMode.TWO_WAY,
        )

        # Scenario 1: Initial upload from source
        print("\n" + "-" * 80)
        print("SCENARIO 1: Initial upload from source")
        print("-" * 80)
        create_test_files(source_dir, count=10, size_kb=5)

        print("\n[SYNC] First sync - uploading source files...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert stats["uploads"] == 10, f"Expected 10 uploads, got {stats['uploads']}"
        assert count_files(dest_storage) == 10
        print("[✓] Successfully uploaded 10 files")

        # Scenario 2: Add files to destination
        print("\n" + "-" * 80)
        print("SCENARIO 2: Add files to destination")
        print("-" * 80)
        print("[INFO] Adding 5 files directly to destination...")
        for i in range(5):
            dest_file = dest_storage / f"dest_file_{i:03d}.txt"
            dest_file.write_text(
                f"Destination content {i}\n" + os.urandom(5 * 1024).hex()
            )
        print("[INFO] Created 5 destination files")

        print("\n[SYNC] Syncing to download destination files...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert (
            stats["downloads"] == 5
        ), f"Expected 5 downloads, got {stats['downloads']}"
        assert count_files(source_dir) == 15
        print("[✓] Successfully downloaded 5 files from destination")

        # Scenario 3: Idempotency check
        print("\n" + "-" * 80)
        print("SCENARIO 3: Idempotency check")
        print("-" * 80)
        print("\n[SYNC] Syncing again (should do nothing)...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert stats["uploads"] == 0 and stats["downloads"] == 0
        print("[✓] Idempotency confirmed - no unnecessary transfers")

        # Scenario 4: Modify file at source
        print("\n" + "-" * 80)
        print("SCENARIO 4: Modify file at source")
        print("-" * 80)
        modified_file = source_dir / "test_file_000.txt"
        print(f"[INFO] Modifying {modified_file.name}...")
        modify_file_with_timestamp(
            modified_file, "Modified content at source\n" + os.urandom(5 * 1024).hex()
        )

        print("\n[SYNC] Syncing to upload modified file...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert stats["uploads"] == 1, f"Expected 1 upload, got {stats['uploads']}"
        print("[✓] Successfully uploaded modified file")

        # Scenario 5: Delete file at destination
        print("\n" + "-" * 80)
        print("SCENARIO 5: Delete file at destination")
        print("-" * 80)
        dest_file = dest_storage / "dest_file_000.txt"
        print(f"[INFO] Deleting {dest_file.name}...")
        dest_file.unlink()

        print("\n[SYNC] Syncing to propagate deletion to source...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert (
            stats["deletes_local"] == 1
        ), f"Expected 1 local delete, got {stats['deletes_local']}"
        assert count_files(source_dir) == 14
        print("[✓] Successfully propagated deletion to source")

        # Scenario 6: Delete file at source
        print("\n" + "-" * 80)
        print("SCENARIO 6: Delete file at source")
        print("-" * 80)
        source_file = source_dir / "test_file_001.txt"
        print(f"[INFO] Deleting {source_file.name}...")
        source_file.unlink()

        print("\n[SYNC] Syncing to propagate deletion to destination...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert (
            stats["deletes_remote"] == 1
        ), f"Expected 1 remote delete, got {stats['deletes_remote']}"
        assert count_files(dest_storage) == 13
        print("[✓] Successfully propagated deletion to destination")

        # Final verification
        print("\n" + "-" * 80)
        print("FINAL VERIFICATION")
        print("-" * 80)
        source_count = count_files(source_dir)
        dest_count = count_files(dest_storage)
        print(f"[INFO] Source files: {source_count}")
        print(f"[INFO] Destination files: {dest_count}")
        assert source_count == dest_count == 13
        print("[✓] Both sides are in sync")

        print("\n" + "=" * 80)
        print("[SUCCESS] TWO_WAY mode benchmark completed successfully!")
        print("=" * 80)


if __name__ == "__main__":
    try:
        benchmark_two_way()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAIL] Assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
