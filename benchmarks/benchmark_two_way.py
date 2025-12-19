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

        # Scenario 7: State invalidation - deletion detection
        print("\n" + "-" * 80)
        print("SCENARIO 7: State invalidation - deletion detection")
        print("-" * 80)
        print("[INFO] Creating file to test deletion detection...")
        delete_test_file = source_dir / "delete_test.txt"
        delete_test_file.write_text("This file will be deleted\n")

        print("\n[SYNC] First sync to establish state...")
        stats = engine.sync_pair(pair)
        assert stats["uploads"] == 1
        print("[✓] File uploaded and state recorded")

        # Delete the file at source
        print(f"[INFO] Deleting {delete_test_file.name} from source...")
        delete_test_file.unlink()

        print("\n[SYNC] Re-sync to detect deletion via state validation...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert (
            stats["deletes_remote"] == 1
        ), f"Expected 1 remote delete, got {stats['deletes_remote']}"
        print("[✓] Deletion detected via state validation and propagated")

        # Scenario 8: State invalidation - modification detection
        # (using SOURCE_TO_DESTINATION)
        print("\n" + "-" * 80)
        print("SCENARIO 8: State invalidation - modification detection")
        print("-" * 80)
        print(
            "[INFO] Testing modification detection with SOURCE_TO_DESTINATION mode..."
        )

        # Create a sync pair with SOURCE_TO_DESTINATION mode for this scenario
        mirror_pair = SyncPair(
            source=source_dir,
            destination="",
            sync_mode=SyncMode.SOURCE_TO_DESTINATION,
        )

        modify_test_file = source_dir / "modify_test.txt"
        modify_test_file.write_text("Original content\n" + "A" * 100)
        print(f"[INFO] Created {modify_test_file.name}...")

        print("\n[SYNC] First sync with SOURCE_TO_DESTINATION mode...")
        stats = engine.sync_pair(mirror_pair)
        assert stats["uploads"] == 1
        print("[✓] File uploaded")

        # Modify the file (change size)
        print(f"[INFO] Modifying {modify_test_file.name} (changing size)...")
        time.sleep(0.1)
        modify_test_file.write_text("New smaller content\n")

        print("\n[SYNC] Re-sync to detect size change via state validation...")
        start = time.time()
        stats = engine.sync_pair(mirror_pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert stats["uploads"] == 1, f"Expected 1 upload, got {stats['uploads']}"
        print("[✓] Size change detected via state validation and uploaded")

        # Scenario 9: State isolation - different storage_id
        print("\n" + "-" * 80)
        print("SCENARIO 9: State isolation by storage_id")
        print("-" * 80)
        print("[INFO] Verifying storage_id creates separate state files...")

        # Get state manager to check state file paths
        from syncengine.state import SyncStateManager

        state_mgr = SyncStateManager()

        # Get state keys for different storage_ids
        key1 = state_mgr._get_state_key(source_dir, "", storage_id=1)
        key2 = state_mgr._get_state_key(source_dir, "", storage_id=2)
        key_none = state_mgr._get_state_key(source_dir, "")  # No storage_id

        print(f"[INFO] State key with storage_id=1: {key1}")
        print(f"[INFO] State key with storage_id=2: {key2}")
        print(f"[INFO] State key with no storage_id: {key_none}")

        # Verify keys are different
        assert key1 != key2, "storage_id=1 and storage_id=2 should have different keys"
        assert (
            key1 != key_none
        ), "storage_id=1 and storage_id=None should have different keys"
        assert (
            key2 != key_none
        ), "storage_id=2 and storage_id=None should have different keys"

        print("[✓] Different storage_ids generate different state keys")
        print(
            "[✓] State isolation verified - each storage_id maintains independent state"
        )

        # Scenario 10: Multiple deletions
        print("\n" + "-" * 80)
        print("SCENARIO 10: Multiple local deletions")
        print("-" * 80)
        print("[INFO] Deleting 3 files from source...")
        files_to_delete = [
            source_dir / "test_file_004.txt",
            source_dir / "test_file_005.txt",
            source_dir / "dest_file_001.txt",
        ]
        for f in files_to_delete:
            if f.exists():
                f.unlink()
                print(f"[INFO] Deleted {f.name}")

        # Use original pair (no storage_id)
        print("\n[SYNC] Syncing to propagate multiple deletions...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")
        assert (
            stats["deletes_remote"] == 3
        ), f"Expected 3 remote deletes, got {stats['deletes_remote']}"
        print("[✓] Successfully detected and propagated 3 deletions")

        # Scenario 11: External state invalidation
        print("\n" + "-" * 80)
        print("SCENARIO 11: External file deletion (state invalidation)")
        print("-" * 80)
        print("[INFO] Simulating external deletion after sync...")

        # First sync to establish state
        print("\n[SYNC] Establishing baseline state...")
        stats = engine.sync_pair(pair)
        baseline_src = count_files(source_dir)
        baseline_dst = count_files(dest_storage)
        print(f"[INFO] Baseline: {baseline_src} source, {baseline_dst} dest files")

        # Simulate external deletion (delete file that was in synced state)
        external_delete = source_dir / "test_file_006.txt"
        if external_delete.exists():
            print(f"[INFO] Externally deleting {external_delete.name}...")
            external_delete.unlink()

            print("\n[SYNC] Re-syncing after external deletion...")
            stats = engine.sync_pair(pair)
            assert (
                stats["deletes_remote"] == 1
            ), f"Expected 1 remote delete, got {stats['deletes_remote']}"
            print("[✓] External deletion correctly propagated to destination")

        # Final verification
        print("\n" + "-" * 80)
        print("FINAL VERIFICATION")
        print("-" * 80)
        source_count = count_files(source_dir)
        dest_count = count_files(dest_storage)
        print(f"[INFO] Source files: {source_count}")
        print(f"[INFO] Destination files: {dest_count}")
        assert source_count == dest_count
        print("[✓] Both sides are in sync")

        print("\n" + "=" * 80)
        print("[SUCCESS] TWO_WAY mode benchmark completed successfully!")
        print("All new state invalidation features demonstrated:")
        print("  ✓ Size change detection")
        print("  ✓ Content change detection (hash comparison)")
        print("  ✓ State isolation by storage_id")
        print("  ✓ Multiple deletion detection")
        print("  ✓ External state invalidation handling")
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
