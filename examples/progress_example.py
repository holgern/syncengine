#!/usr/bin/env python3
"""
Quick Start Example: Using syncengine with Progress Tracking

This example demonstrates how to use the enhanced sync_pair() method
with full file-level progress tracking.

Run this example:
    python examples/progress_example.py
"""

from syncengine.progress import (
    SyncProgressEvent,
    SyncProgressInfo,
)


def progress_callback(info: SyncProgressInfo):
    """Simple progress callback that prints events to console."""

    if info.event == SyncProgressEvent.SCAN_DIR_START:
        print(f"📁 Scanning: {info.directory}")

    elif info.event == SyncProgressEvent.SCAN_DIR_COMPLETE:
        print(f"✓ Found {info.files_in_batch} files in {info.directory}")

    elif info.event == SyncProgressEvent.UPLOAD_BATCH_START:
        print(f"\n📤 Starting upload batch: {info.directory}")
        print(f"   Files: {info.folder_files_total}")
        print(f"   Size: {info.folder_bytes_total / 1024 / 1024:.2f} MB")

    elif info.event == SyncProgressEvent.UPLOAD_FILE_START:
        print(f"⬆️  Uploading: {info.file_path}")

    elif info.event == SyncProgressEvent.UPLOAD_FILE_PROGRESS:
        # Show progress for this file
        progress = (
            (info.current_file_bytes / info.current_file_total * 100)
            if info.current_file_total > 0
            else 0
        )
        uploaded_kb = info.current_file_bytes / 1024
        total_kb = info.current_file_total / 1024
        msg = f"   Progress: {progress:.1f}% "
        msg += f"({uploaded_kb:.1f}/{total_kb:.1f} KB)"
        print(msg)

    elif info.event == SyncProgressEvent.UPLOAD_FILE_COMPLETE:
        print(f"✓ Completed: {info.file_path}")

    elif info.event == SyncProgressEvent.UPLOAD_FILE_ERROR:
        print(f"❌ Error: {info.file_path} - {info.error_message}")

    elif info.event == SyncProgressEvent.UPLOAD_BATCH_COMPLETE:
        uploaded = info.folder_files_uploaded
        total = info.folder_files_total
        print(f"✓ Batch complete: {uploaded}/{total} files uploaded")


def example_basic_upload():
    """Example 1: Basic upload with progress tracking."""
    print("=" * 60)
    print("Example 1: Basic Upload with Progress")
    print("=" * 60)

    # Note: This is a skeleton example. You need to provide:
    # - A real StorageClientProtocol implementation
    # - A real FileEntriesManagerProtocol factory

    # from syncengine import SyncEngine
    #
    # engine = SyncEngine(client, entries_manager_factory)
    #
    # pair = SyncPair(
    #     source=Path("/path/to/local/folder"),
    #     destination="/remote_folder",
    #     sync_mode=SyncMode.SOURCE_TO_DESTINATION,
    #     storage_id=0,
    # )
    #
    # tracker = SyncProgressTracker(callback=progress_callback)
    #
    # stats = engine.sync_pair(
    #     pair,
    #     sync_progress_tracker=tracker,
    #     max_workers=4,
    # )
    #
    # print(f"\n✓ Upload complete!")
    # print(f"  Uploaded: {stats['uploads']} files")
    # print(f"  Skipped: {stats['skips']} files")
    # print(f"  Errors: {stats['errors']} files")

    print("See PYDRIME_INTEGRATION_GUIDE.md for complete implementation")


def example_with_skip_and_rename():
    """Example 2: Upload with skip and rename support."""
    print("\n" + "=" * 60)
    print("Example 2: Upload with Skip and Rename")
    print("=" * 60)

    # Files to skip (e.g., duplicates)
    files_to_skip = {  # noqa: F841
        "folder/duplicate1.txt",
        "folder/duplicate2.txt",
    }

    # Files to rename during upload
    file_renames = {  # noqa: F841
        "old_name.txt": "new_name.txt",
        "folder/old.txt": "folder/renamed.txt",
    }

    # from syncengine import SyncEngine
    #
    # engine = SyncEngine(client, entries_manager_factory)
    #
    # pair = SyncPair(
    #     source=Path("/path/to/local/folder"),
    #     destination="/remote_folder",
    #     sync_mode=SyncMode.SOURCE_TO_DESTINATION,
    #     storage_id=0,
    # )
    #
    # tracker = SyncProgressTracker(callback=progress_callback)
    #
    # stats = engine.sync_pair(
    #     pair,
    #     sync_progress_tracker=tracker,
    #     files_to_skip=files_to_skip,      # NEW: Skip these files
    #     file_renames=file_renames,        # NEW: Rename during upload
    #     max_workers=4,
    # )
    #
    # print(f"\n✓ Upload complete!")
    # print(f"  Uploaded: {stats['uploads']} files")
    # print(f"  Skipped: {stats['skips']} files (including filtered)")

    print("See PYDRIME_INTEGRATION_GUIDE.md for complete implementation")


def example_with_parent_id():
    """Example 3: Upload into specific folder using parent_id."""
    print("\n" + "=" * 60)
    print("Example 3: Upload into Specific Folder")
    print("=" * 60)

    # Upload into folder ID 1234 (instead of resolving by path)
    current_folder_id = 1234  # noqa: F841

    # from syncengine import SyncEngine
    #
    # engine = SyncEngine(client, entries_manager_factory)
    #
    # pair = SyncPair(
    #     source=Path("/path/to/local/folder"),
    #     destination="/remote_folder",
    #     sync_mode=SyncMode.SOURCE_TO_DESTINATION,
    #     storage_id=0,
    #     parent_id=current_folder_id,  # NEW: Upload into this folder
    # )
    #
    # tracker = SyncProgressTracker(callback=progress_callback)
    #
    # stats = engine.sync_pair(
    #     pair,
    #     sync_progress_tracker=tracker,
    #     max_workers=4,
    # )
    #
    # print(f"\n✓ Upload complete!")
    # print(f"  Uploaded: {stats['uploads']} files")

    print("See PYDRIME_INTEGRATION_GUIDE.md for complete implementation")


def example_rich_progress():
    """Example 4: Using Rich for beautiful progress bars."""
    print("\n" + "=" * 60)
    print("Example 4: Rich Progress Bars")
    print("=" * 60)

    # from rich.progress import (
    #     Progress,
    #     SpinnerColumn,
    #     TextColumn,
    #     BarColumn,
    #     DownloadColumn,
    #     TransferSpeedColumn,
    #     TimeRemainingColumn,
    # )
    #
    # progress = Progress(
    #     SpinnerColumn(),
    #     TextColumn("[bold blue]{task.description}"),
    #     BarColumn(),
    #     DownloadColumn(),
    #     TransferSpeedColumn(),
    #     TimeRemainingColumn(),
    # )
    #
    # progress.start()
    # tasks = {}
    #
    # def rich_callback(info: SyncProgressInfo):
    #     if info.event == SyncProgressEvent.UPLOAD_BATCH_START:
    #         task = progress.add_task(
    #             f"Uploading {info.directory}",
    #             total=info.folder_bytes_total
    #         )
    #         tasks[info.directory] = task
    #
    #     elif info.event == SyncProgressEvent.UPLOAD_FILE_PROGRESS:
    #         if info.directory in tasks:
    #             progress.update(
    #                 tasks[info.directory],
    #                 completed=info.folder_bytes_uploaded,
    #                 description=f"Uploading {info.file_path}",
    #             )
    #
    # tracker = SyncProgressTracker(callback=rich_callback)
    #
    # try:
    #     stats = engine.sync_pair(
    #         pair,
    #         sync_progress_tracker=tracker,
    #         max_workers=4,
    #     )
    # finally:
    #     progress.stop()

    print("See PYDRIME_INTEGRATION_GUIDE.md for complete implementation")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("SyncEngine Progress Tracking Examples")
    print("=" * 60)
    print("\nThese examples demonstrate the new progress tracking features.")
    print("For complete, working code, see PYDRIME_INTEGRATION_GUIDE.md\n")

    example_basic_upload()
    example_with_skip_and_rename()
    example_with_parent_id()
    example_rich_progress()

    print("\n" + "=" * 60)
    print("Next Steps:")
    print("=" * 60)
    print("1. Read PYDRIME_INTEGRATION_GUIDE.md for detailed integration steps")
    print("2. Read SYNCENGINE_MODIFICATIONS.md for technical changes")
    print("3. Implement progress callback in your CLI application")
    print("4. Replace upload_folder() with sync_pair()")
    print("5. Test with various file sizes and counts")
    print()


if __name__ == "__main__":
    main()
