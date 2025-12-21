"""
Benchmark script for testing different ComparisonMode values.

This script tests all comparison modes with different sync scenarios:
- HASH_THEN_MTIME (default): Uses hash+size, falls back to mtime
- SIZE_ONLY: Only compares file size (for encrypted vaults without hash/mtime)
- SIZE_AND_MTIME: Compares size and mtime
- MTIME_ONLY: Only compares modification time
- HASH_ONLY: Only compares content hash

The SIZE_ONLY mode is specifically designed for cloud storage that:
- Doesn't provide content hash (e.g., encrypted vaults)
- Doesn't preserve original file mtime (only tracks upload time)
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
    NoHashNoMtimeStorageClient,
    count_files,
    create_entries_manager_factory,
    create_test_files,
    modify_file_with_timestamp,
)
from syncengine import ComparisonMode, SyncConfig
from syncengine.engine import SyncEngine
from syncengine.modes import SyncMode
from syncengine.pair import SyncPair
from syncengine.protocols import DefaultOutputHandler


def test_comparison_mode(
    comparison_mode: ComparisonMode,
    use_no_hash_client: bool = False,
) -> bool:
    """Test a specific comparison mode with DESTINATION_BACKUP sync.

    Args:
        comparison_mode: The comparison mode to test
        use_no_hash_client: If True, use NoHashNoMtimeStorageClient

    Returns:
        True if test passed, False otherwise
    """
    print("\n" + "=" * 80)
    print(f"TESTING COMPARISON MODE: {comparison_mode.value}")
    print("=" * 80)
    if use_no_hash_client:
        print("Using NoHashNoMtimeStorageClient (no hash, no mtime)")
    else:
        print("Using LocalStorageClient (has hash and mtime)")
    print("=" * 80)

    test_uuid = str(uuid.uuid4())[:8]

    with tempfile.TemporaryDirectory(
        prefix=f"bench_compare_{comparison_mode.value}_{test_uuid}_"
    ) as tmp:
        base_dir = Path(tmp)
        source_dir = base_dir / "source"
        dest_storage = base_dir / "destination"

        source_dir.mkdir(parents=True, exist_ok=True)
        dest_storage.mkdir(parents=True, exist_ok=True)

        print(f"\n[INFO] Test directory: {base_dir}")

        # Create appropriate client based on test scenario
        if use_no_hash_client:
            client = NoHashNoMtimeStorageClient(dest_storage)
        else:
            client = LocalStorageClient(dest_storage)

        factory = create_entries_manager_factory(client)
        output = DefaultOutputHandler(quiet=True)

        # Create config with specific comparison mode
        config = SyncConfig(comparison_mode=comparison_mode)
        engine = SyncEngine(client, factory, output=output, config=config)

        pair = SyncPair(
            source=source_dir,
            destination="",
            sync_mode=SyncMode.DESTINATION_BACKUP,
        )

        # Scenario 1: Initial download from destination (files only in cloud)
        print("\n" + "-" * 80)
        print("SCENARIO 1: Initial download - files only exist in cloud")
        print("-" * 80)
        create_test_files(dest_storage, count=5, size_kb=5)

        print("\n[SYNC] First sync - downloading files from cloud...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")

        # CRITICAL: Check if downloads succeeded
        local_count = count_files(source_dir)
        if stats["downloads"] != 5:
            print(f"[FAIL] Expected 5 downloads, got {stats['downloads']}")
            return False
        if local_count != 5:
            print(f"[FAIL] Expected 5 local files, found {local_count}")
            return False
        print("[✓] Successfully downloaded 5 files from cloud")

        # Scenario 2: Idempotency - sync again (should skip all)
        print("\n" + "-" * 80)
        print("SCENARIO 2: Idempotency - files match, should skip")
        print("-" * 80)
        print("\n[SYNC] Syncing again (should skip all)...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")

        if stats["downloads"] != 0:
            print(f"[FAIL] Expected 0 downloads, got {stats['downloads']}")
            return False
        if stats["skips"] != 5:
            print(f"[FAIL] Expected 5 skips, got {stats['skips']}")
            return False
        print("[✓] Idempotency verified - all files skipped")

        # Scenario 3: Add new file to cloud
        print("\n" + "-" * 80)
        print("SCENARIO 3: New file in cloud - should download")
        print("-" * 80)
        new_file = dest_storage / "test_file_005.txt"
        new_file.write_text("New cloud file\n" + os.urandom(5 * 1024).hex())

        print("\n[SYNC] Syncing to download new file...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")

        if stats["downloads"] != 1:
            print(f"[FAIL] Expected 1 download, got {stats['downloads']}")
            return False
        if count_files(source_dir) != 6:
            print("[FAIL] Expected 6 local files after new download")
            return False
        print("[✓] New file downloaded successfully")

        # Scenario 4: Modify file size in cloud
        print("\n" + "-" * 80)
        print("SCENARIO 4: Modify file size in cloud - should download")
        print("-" * 80)
        modified_file = dest_storage / "test_file_000.txt"
        modify_file_with_timestamp(
            modified_file,
            "Modified content (different size)\n" + os.urandom(10 * 1024).hex(),
        )

        print("\n[SYNC] Syncing to download modified file...")
        start = time.time()
        stats = engine.sync_pair(pair)
        elapsed = time.time() - start

        print(f"[STATS] {stats}")
        print(f"[TIME] Sync completed in {elapsed:.3f}s")

        # For SIZE_ONLY mode, different size should trigger download
        # For other modes, hash/mtime changes should also trigger download
        expected_downloads = 1
        if stats["downloads"] != expected_downloads:
            print(
                f"[FAIL] Expected {expected_downloads} download(s), "
                f"got {stats['downloads']}"
            )
            return False
        print("[✓] Modified file downloaded successfully")

        # Final verification
        print("\n" + "-" * 80)
        print("FINAL VERIFICATION")
        print("-" * 80)
        final_count = count_files(source_dir)
        print(f"[INFO] Local files: {final_count}")
        if final_count != 6:
            print(f"[FAIL] Expected 6 local files, found {final_count}")
            return False

        print("\n" + "=" * 80)
        print(f"[SUCCESS] {comparison_mode.value} mode test completed!")
        print("=" * 80)
        return True


def benchmark_all_comparison_modes():
    """Run benchmarks for all comparison modes."""
    print("\n" + "=" * 80)
    print("BENCHMARK: ALL COMPARISON MODES")
    print("=" * 80)
    print("Testing: HASH_THEN_MTIME, SIZE_ONLY, SIZE_AND_MTIME, MTIME_ONLY, HASH_ONLY")
    print("=" * 80)

    results = {}

    # Test 1: HASH_THEN_MTIME (default) with regular storage
    print("\n" + "#" * 80)
    print("TEST 1: HASH_THEN_MTIME mode with LocalStorageClient")
    print("#" * 80)
    results["HASH_THEN_MTIME"] = test_comparison_mode(
        ComparisonMode.HASH_THEN_MTIME, use_no_hash_client=False
    )

    # Test 2: SIZE_ONLY with NoHashNoMtimeStorageClient (critical test!)
    print("\n" + "#" * 80)
    print("TEST 2: SIZE_ONLY mode with NoHashNoMtimeStorageClient")
    print("        (CRITICAL: This tests the encrypted vault scenario)")
    print("#" * 80)
    results["SIZE_ONLY_NO_HASH"] = test_comparison_mode(
        ComparisonMode.SIZE_ONLY, use_no_hash_client=True
    )

    # Test 3: SIZE_ONLY with regular storage (for comparison)
    print("\n" + "#" * 80)
    print("TEST 3: SIZE_ONLY mode with LocalStorageClient")
    print("#" * 80)
    results["SIZE_ONLY"] = test_comparison_mode(
        ComparisonMode.SIZE_ONLY, use_no_hash_client=False
    )

    # Test 4: SIZE_AND_MTIME with regular storage
    print("\n" + "#" * 80)
    print("TEST 4: SIZE_AND_MTIME mode with LocalStorageClient")
    print("#" * 80)
    results["SIZE_AND_MTIME"] = test_comparison_mode(
        ComparisonMode.SIZE_AND_MTIME, use_no_hash_client=False
    )

    # Test 5: MTIME_ONLY with regular storage
    print("\n" + "#" * 80)
    print("TEST 5: MTIME_ONLY mode with LocalStorageClient")
    print("#" * 80)
    results["MTIME_ONLY"] = test_comparison_mode(
        ComparisonMode.MTIME_ONLY, use_no_hash_client=False
    )

    # Test 6: HASH_ONLY with regular storage
    print("\n" + "#" * 80)
    print("TEST 6: HASH_ONLY mode with LocalStorageClient")
    print("#" * 80)
    results["HASH_ONLY"] = test_comparison_mode(
        ComparisonMode.HASH_ONLY, use_no_hash_client=False
    )

    # Summary
    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY")
    print("=" * 80)
    for mode, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {mode}")

    all_passed = all(results.values())
    print("=" * 80)
    if all_passed:
        print("[SUCCESS] All comparison mode tests passed!")
    else:
        print("[FAILURE] Some comparison mode tests failed!")
    print("=" * 80)

    return all_passed


if __name__ == "__main__":
    try:
        success = benchmark_all_comparison_modes()
        sys.exit(0 if success else 1)
    except AssertionError as e:
        print(f"\n[FAIL] Assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
