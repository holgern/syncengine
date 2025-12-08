"""
Benchmark script for SOURCE_TO_DESTINATION sync mode.

SOURCE_TO_DESTINATION mode mirrors every action done at source to destination,
including deletions. Destination changes are ignored and never propagated back.
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


def benchmark_source_to_destination():
    """Benchmark SOURCE_TO_DESTINATION sync mode with various scenarios."""
    print("\n" + "=" * 80)
    print("BENCHMARK: SOURCE_TO_DESTINATION SYNC MODE")
    print("=" * 80)
    print("Mode: Mirror source actions to destination, ignore destination changes")
    print("=" * 80)

    test_uuid = str(uuid.uuid4())[:8]

    with tempfile.TemporaryDirectory(prefix=f"bench_s2d_{test_uuid}_") as tmp:
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
            sync_mode=SyncMode.SOURCE_TO_DESTINATION,
        )

        # Scenario 1: Initial upload
        print("\n" + "-" * 80)
        print("SCENARIO 1: Initial upload from source")
        print("-" * 80)
        create_test_files(source_dir, count=15, size_kb=10)

        print("\n[SYNC] First sync - uploading source files...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert stats["uploads"] == 15, f"Expected 15 uploads, got {stats['uploads']}"
        assert count_files(dest_storage) == 15
        print("[✓] Successfully uploaded 15 files")

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

        # Scenario 3: Add file at source
        print("\n" + "-" * 80)
        print("SCENARIO 3: Add new file at source")
        print("-" * 80)
        new_file = source_dir / "new_file.txt"
        print(f"[INFO] Creating {new_file.name}...")
        new_file.write_text("New file content\n" + os.urandom(10 * 1024).hex())

        print("\n[SYNC] Syncing to upload new file...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert stats["uploads"] == 1, f"Expected 1 upload, got {stats['uploads']}"
        assert count_files(dest_storage) == 16
        print("[✓] Successfully uploaded new file")

        # Scenario 4: Modify file at source
        print("\n" + "-" * 80)
        print("SCENARIO 4: Modify file at source")
        print("-" * 80)
        modified_file = source_dir / "test_file_000.txt"
        print(f"[INFO] Modifying {modified_file.name}...")
        # Wait 2+ seconds to ensure clear timestamp difference
        # (avoid conflict detection)
        modify_file_with_timestamp(
            modified_file, "Modified content\n" + os.urandom(10 * 1024).hex()
        )

        print("\n[SYNC] Syncing to upload modified file...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert stats["uploads"] == 1, f"Expected 1 upload, got {stats['uploads']}"
        print("[✓] Successfully uploaded modified file")

        # Scenario 5: Delete file at source (should delete at destination)
        print("\n" + "-" * 80)
        print("SCENARIO 5: Delete file at source")
        print("-" * 80)
        deleted_file = source_dir / "test_file_001.txt"
        print(f"[INFO] Deleting {deleted_file.name}...")
        deleted_file.unlink()

        print("\n[SYNC] Syncing to propagate deletion to destination...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert (
            stats["deletes_remote"] == 1
        ), f"Expected 1 remote delete, got {stats['deletes_remote']}"
        assert count_files(dest_storage) == 15
        print("[✓] Successfully propagated deletion to destination")

        # Scenario 6: Add file at destination (should be ignored)
        print("\n" + "-" * 80)
        print("SCENARIO 6: Add file at destination (should be ignored)")
        print("-" * 80)
        dest_file = dest_storage / "dest_only_file.txt"
        print(f"[INFO] Creating {dest_file.name} at destination...")
        dest_file.write_text("Destination only content")

        print("\n[SYNC] Syncing (should ignore destination changes)...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert (
            stats["downloads"] == 0
        ), f"Expected 0 downloads, got {stats['downloads']}"
        assert not (source_dir / "dest_only_file.txt").exists()
        print("[✓] Destination changes correctly ignored")

        # Scenario 7: Delete file at destination (should be re-uploaded)
        print("\n" + "-" * 80)
        print("SCENARIO 7: Delete file at destination (should be re-uploaded)")
        print("-" * 80)
        dest_file = dest_storage / "test_file_002.txt"
        print(f"[INFO] Deleting {dest_file.name} from destination...")
        dest_file.unlink()

        print("\n[SYNC] Syncing (should re-upload deleted file)...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert stats["uploads"] == 1, f"Expected 1 upload, got {stats['uploads']}"
        assert (dest_storage / "test_file_002.txt").exists()
        print("[✓] Successfully re-uploaded deleted file")

        # Final verification
        print("\n" + "-" * 80)
        print("FINAL VERIFICATION")
        print("-" * 80)
        source_count = count_files(source_dir)
        dest_count = count_files(dest_storage)
        print(f"[INFO] Source files: {source_count}")
        print(f"[INFO] Destination files: {dest_count}")
        # Both should be equal - SOURCE_TO_DESTINATION mirrors source to destination
        assert source_count == 15
        assert dest_count == 15  # dest_only_file.txt was deleted to maintain mirror
        print("[✓] Source correctly mirrored to destination")

        print("\n" + "=" * 80)
        print("[SUCCESS] SOURCE_TO_DESTINATION mode benchmark completed successfully!")
        print("=" * 80)


if __name__ == "__main__":
    try:
        benchmark_source_to_destination()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAIL] Assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
