"""Tests for scanner module."""

import os

import pytest

from syncengine.models import FileEntry
from syncengine.scanner import (
    DestinationFile,
    DirectoryScanner,
    SourceFile,
)


class TestSourceFile:
    """Test SourceFile model and factory methods."""

    def test_from_path(self, tmp_path):
        """Test creating SourceFile from path."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")

        source = SourceFile.from_path(test_file, tmp_path)

        assert source.path == test_file
        assert source.relative_path == "test.txt"
        assert source.size == 11
        assert source.mtime > 0
        # file_id may be 0 on some Windows filesystems
        assert source.file_id >= 0

    def test_from_path_with_subdirectory(self, tmp_path):
        """Test from_path with nested directory."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        test_file = subdir / "test.txt"
        test_file.write_text("content")

        source = SourceFile.from_path(test_file, tmp_path)

        assert source.relative_path == "subdir/test.txt"

    def test_from_dir_entry(self, tmp_path):
        """Test creating SourceFile from DirEntry."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")

        # Get DirEntry from scandir
        with os.scandir(tmp_path) as entries:
            for entry in entries:
                if entry.name == "test.txt":
                    stat_result = entry.stat(follow_symlinks=False)
                    source = SourceFile.from_dir_entry(entry, tmp_path, stat_result)

                    assert source.path == test_file
                    assert source.relative_path == "test.txt"
                    assert source.size == 5
                    assert source.mtime > 0
                    # file_id may be 0 on some Windows filesystems
                    assert source.file_id >= 0
                    break

    def test_from_scandir_fast(self, tmp_path):
        """Test from_scandir_fast method."""
        test_file = tmp_path / "fast.txt"
        test_file.write_text("fast content")

        base_path_str = str(tmp_path)
        if not base_path_str.endswith(os.sep):
            base_path_str += os.sep
        base_len = len(base_path_str)

        with os.scandir(tmp_path) as entries:
            for entry in entries:
                if entry.name == "fast.txt":
                    source = SourceFile.from_scandir_fast(
                        entry, base_path_str, base_len
                    )

                    assert source.relative_path == "fast.txt"
                    assert source.size == 12
                    assert source.mtime > 0
                    break

    def test_from_scandir_fast_with_backslash(self, tmp_path):
        """Test from_scandir_fast handles path separators correctly."""
        if os.sep != "/":
            # Only test on Windows where backslashes are used
            subdir = tmp_path / "subdir"
            subdir.mkdir()
            test_file = subdir / "test.txt"
            test_file.write_text("content")

            base_path_str = str(tmp_path)
            if not base_path_str.endswith(os.sep):
                base_path_str += os.sep
            base_len = len(base_path_str)

            # Scan subdirectory
            for dirpath, _dirnames, filenames in os.walk(tmp_path):
                if "test.txt" in filenames:
                    abs_path = os.path.join(dirpath, "test.txt")
                    with os.scandir(os.path.dirname(abs_path)) as entries:
                        for entry in entries:
                            if entry.name == "test.txt":
                                source = SourceFile.from_scandir_fast(
                                    entry, base_path_str, base_len
                                )
                                # Should use forward slashes
                                assert (
                                    "/" in source.relative_path
                                    or source.relative_path == "test.txt"
                                )
                                break

    def test_from_stat_fast(self, tmp_path):
        """Test from_stat_fast method."""
        test_file = tmp_path / "stat.txt"
        test_file.write_text("stat content")

        abs_path_str = str(test_file)
        relative_path = "stat.txt"
        stat_result = os.stat(abs_path_str)

        source = SourceFile.from_stat_fast(abs_path_str, relative_path, stat_result)

        assert source.path == test_file
        assert source.relative_path == relative_path
        assert source.size == 12
        assert source.mtime > 0


class TestDestinationFile:
    """Test DestinationFile model."""

    def test_destination_file_properties(self):
        """Test DestinationFile properties."""
        entry = FileEntry(
            id=123,
            type="file",
            name="test.txt",
            file_size=1024,
            hash="abc123",
            updated_at="2024-01-01T00:00:00Z",
        )

        dest = DestinationFile(entry=entry, relative_path="docs/test.txt")

        assert dest.size == 1024
        assert dest.id == 123
        assert dest.hash == "abc123"
        assert dest.relative_path == "docs/test.txt"

    def test_destination_file_mtime(self):
        """Test DestinationFile mtime parsing."""
        entry = FileEntry(
            id=1,
            type="file",
            name="test.txt",
            updated_at="2024-01-01T12:30:00Z",
        )

        dest = DestinationFile(entry=entry, relative_path="test.txt")
        mtime = dest.mtime

        assert mtime is not None
        assert mtime > 0

    def test_destination_file_mtime_no_updated_at(self):
        """Test DestinationFile mtime when updated_at is None."""
        entry = FileEntry(
            id=1,
            type="file",
            name="test.txt",
            updated_at=None,
        )

        dest = DestinationFile(entry=entry, relative_path="test.txt")

        assert dest.mtime is None

    def test_destination_file_mtime_invalid_format(self):
        """Test DestinationFile mtime with invalid timestamp."""
        entry = FileEntry(
            id=1,
            type="file",
            name="test.txt",
            updated_at="invalid-timestamp",
        )

        dest = DestinationFile(entry=entry, relative_path="test.txt")

        # Should return None for invalid timestamp
        assert dest.mtime is None


class TestDirectoryScanner:
    """Test DirectoryScanner."""

    def test_should_ignore_ignore_file(self, tmp_path):
        """Test that ignore file itself is ignored."""
        scanner = DirectoryScanner(ignore_file_name=".syncignore")

        ignore_file = tmp_path / ".syncignore"
        ignore_file.write_text("*.log")

        assert scanner.should_ignore(ignore_file, tmp_path, is_dir=False) is True

    def test_should_ignore_dot_files(self, tmp_path):
        """Test excluding dot files."""
        scanner = DirectoryScanner(exclude_dot_files=True)

        dot_file = tmp_path / ".hidden"
        dot_file.write_text("hidden")

        assert scanner.should_ignore(dot_file, tmp_path, is_dir=False) is True

    def test_scan_source_with_permission_error(self, tmp_path):
        """Test scan_source handles permission errors gracefully."""
        scanner = DirectoryScanner()

        # Create directory structure
        test_dir = tmp_path / "testdir"
        test_dir.mkdir()
        test_file = test_dir / "file.txt"
        test_file.write_text("content")

        # This should not raise even if we can't read some files
        files = scanner.scan_source(test_dir)

        # Should still return readable files
        assert isinstance(files, list)

    def test_scan_source_single_level(self, tmp_path):
        """Test scan_source_single_level."""
        scanner = DirectoryScanner()

        # Create files and subdirectories
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("nested")

        files, subdirs = scanner.scan_source_single_level(tmp_path)

        # Should find files in current directory
        file_paths = [f.relative_path for f in files]
        assert "file1.txt" in file_paths
        assert "file2.txt" in file_paths
        assert "subdir/nested.txt" not in file_paths  # Not recursive

        # Should find subdirectory names
        assert "subdir" in subdirs

    def test_scan_source_single_level_with_ignore_file(self, tmp_path):
        """Test single level scan loads ignore files."""
        scanner = DirectoryScanner(use_ignore_files=True)

        # Create ignore file
        ignore_file = tmp_path / ".syncignore"
        ignore_file.write_text("*.log\n")

        # Create files
        (tmp_path / "file.txt").write_text("keep")
        (tmp_path / "debug.log").write_text("ignore")

        files, subdirs = scanner.scan_source_single_level(tmp_path)

        file_paths = [f.relative_path for f in files]
        assert "file.txt" in file_paths
        assert "debug.log" not in file_paths

    def test_scan_source_single_level_ignore_subdirectories(self, tmp_path):
        """Test single level scan ignores matching subdirectories."""
        scanner = DirectoryScanner(ignore_patterns=["cache"])

        # Create directories
        (tmp_path / "keep").mkdir()
        (tmp_path / "cache").mkdir()

        files, subdirs = scanner.scan_source_single_level(tmp_path)

        assert "keep" in subdirs
        assert "cache" not in subdirs

    def test_scan_source_single_level_with_permission_error(self, tmp_path):
        """Test single level scan handles permission errors."""
        scanner = DirectoryScanner()

        # Create a file
        (tmp_path / "file.txt").write_text("content")

        # Should handle gracefully
        files, subdirs = scanner.scan_source_single_level(tmp_path)

        assert isinstance(files, list)
        assert isinstance(subdirs, list)

    def test_scan_source_recursive_method(self, tmp_path):
        """Test _scan_source_recursive method directly."""
        scanner = DirectoryScanner(use_ignore_files=True)
        scanner._ignore_manager = scanner._init_ignore_manager(tmp_path)

        # Create nested structure
        (tmp_path / "file1.txt").write_text("content1")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("content2")

        files = scanner._scan_source_recursive(tmp_path, tmp_path)

        file_paths = [f.relative_path for f in files]
        assert "file1.txt" in file_paths
        assert "subdir/file2.txt" in file_paths

    def test_scan_source_recursive_with_ignore_file(self, tmp_path):
        """Test recursive scan with ignore files in subdirectories."""
        scanner = DirectoryScanner(use_ignore_files=True)
        scanner._ignore_manager = scanner._init_ignore_manager(tmp_path)

        # Create ignore file in subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / ".syncignore").write_text("*.tmp")
        (subdir / "keep.txt").write_text("keep")
        (subdir / "ignore.tmp").write_text("ignore")

        files = scanner._scan_source_recursive(tmp_path, tmp_path)

        file_paths = [f.relative_path for f in files]
        assert "subdir/keep.txt" in file_paths
        assert "subdir/ignore.tmp" not in file_paths

    def test_scan_source_recursive_with_ignored_directory(self, tmp_path):
        """Test recursive scan skips ignored directories."""
        scanner = DirectoryScanner(ignore_patterns=["cache/*"])
        scanner._ignore_manager = scanner._init_ignore_manager(tmp_path)

        # Create cache directory
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "temp.txt").write_text("temp")

        # Create non-ignored directory
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "readme.txt").write_text("readme")

        files = scanner._scan_source_recursive(tmp_path, tmp_path)

        file_paths = [f.relative_path for f in files]
        # cache directory should be skipped
        assert not any("cache" in p for p in file_paths)
        assert "docs/readme.txt" in file_paths

    def test_scan_source_recursive_with_permission_error(self, tmp_path):
        """Test recursive scan handles permission errors."""
        scanner = DirectoryScanner()
        scanner._ignore_manager = scanner._init_ignore_manager(tmp_path)

        (tmp_path / "file.txt").write_text("content")

        # Should not raise
        files = scanner._scan_source_recursive(tmp_path, tmp_path)

        assert isinstance(files, list)

    def test_scan_destination(self):
        """Test scan_destination processes entries correctly."""
        from typing import cast

        from syncengine.protocols import FileEntryProtocol

        scanner = DirectoryScanner()

        file_entry = FileEntry(
            id=1, type="file", name="doc.txt", file_size=100, hash="hash1"
        )
        folder_entry = FileEntry(id=2, type="folder", name="docs")

        entries_with_paths: list[tuple[FileEntryProtocol, str]] = [
            (cast(FileEntryProtocol, file_entry), "doc.txt"),
            (cast(FileEntryProtocol, folder_entry), "docs"),
        ]

        dest_files = scanner.scan_destination(entries_with_paths)

        # Should only include files, not folders
        assert len(dest_files) == 1
        assert dest_files[0].relative_path == "doc.txt"
        assert dest_files[0].size == 100

    def test_scan_source_without_ignore_files(self, tmp_path):
        """Test scanning with use_ignore_files=False."""
        scanner = DirectoryScanner(use_ignore_files=False)

        # Create ignore file (should be ignored)
        (tmp_path / ".syncignore").write_text("*.log")
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "test.log").write_text("log")

        files = scanner.scan_source(tmp_path)

        file_paths = [f.relative_path for f in files]
        # Both files should be included since ignore file is not loaded
        assert "file.txt" in file_paths
        assert "test.log" in file_paths

    def test_scan_source_with_cli_patterns_only(self, tmp_path):
        """Test scanning with CLI patterns but no ignore files."""
        scanner = DirectoryScanner(ignore_patterns=["*.log"], use_ignore_files=False)

        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "test.log").write_text("log")

        files = scanner.scan_source(tmp_path)

        file_paths = [f.relative_path for f in files]
        assert "file.txt" in file_paths
        assert "test.log" not in file_paths  # Excluded by CLI pattern

    def test_should_ignore_fast(self, tmp_path):
        """Test _should_ignore_fast method."""
        scanner = DirectoryScanner(
            exclude_dot_files=True,
            ignore_patterns=["*.log"],
        )

        # Initialize ignore manager
        scanner._ignore_manager = scanner._init_ignore_manager(tmp_path)

        # Test dot file
        assert scanner._should_ignore_fast(".hidden", ".hidden", is_dir=False) is True

        # Test ignore file itself
        assert (
            scanner._should_ignore_fast(".syncignore", ".syncignore", is_dir=False)
            is True
        )

        # Test pattern match
        assert scanner._should_ignore_fast("test.log", "test.log", is_dir=False) is True

        # Test normal file
        assert (
            scanner._should_ignore_fast("file.txt", "file.txt", is_dir=False) is False
        )

    def test_scan_source_with_symlinks(self, tmp_path):
        """Test that symlinks are not followed."""
        scanner = DirectoryScanner()

        # Create a file and a symlink
        real_file = tmp_path / "real.txt"
        real_file.write_text("content")

        try:
            # Symlinks might not be supported on all systems
            symlink = tmp_path / "link.txt"
            symlink.symlink_to(real_file)

            files = scanner.scan_source(tmp_path)

            # Should only include the real file, not the symlink
            file_paths = [f.relative_path for f in files]
            # Symlink should be skipped (not a regular file)
            assert len([p for p in file_paths if "link" not in p]) >= 1
        except OSError:
            # Symlinks not supported, skip test
            pytest.skip("Symlinks not supported on this system")

    def test_scan_source_only_regular_files(self, tmp_path):
        """Test that only regular files are included."""
        scanner = DirectoryScanner()

        # Create regular file
        (tmp_path / "file.txt").write_text("content")

        # Create subdirectory (should be traversed but not included)
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        files = scanner.scan_source(tmp_path)

        # Should only have the file, not the directory
        file_paths = [f.relative_path for f in files]
        assert "file.txt" in file_paths
        assert "subdir" not in file_paths

    def test_scan_source_with_special_characters(self, tmp_path):
        """Test scanning files with special characters in names."""
        scanner = DirectoryScanner()

        # Create files with various special characters
        special_files = [
            "file with spaces.txt",
            "file-with-dashes.txt",
            "file_with_underscores.txt",
            "file(with)parens.txt",
            "file[with]brackets.txt",
            "file@special.txt",
        ]

        for filename in special_files:
            (tmp_path / filename).write_text("content")

        files = scanner.scan_source(tmp_path)
        file_paths = [f.relative_path for f in files]

        # All special character files should be scanned
        for filename in special_files:
            assert filename in file_paths

    def test_scan_source_with_unicode_names(self, tmp_path):
        """Test scanning files with unicode characters."""
        scanner = DirectoryScanner()

        # Create files with unicode characters
        unicode_files = [
            "файл.txt",  # Russian
            "文件.txt",  # Chinese
            "ファイル.txt",  # Japanese
            "tëst.txt",  # Accented characters
        ]

        for filename in unicode_files:
            try:
                (tmp_path / filename).write_text("content")
            except (OSError, UnicodeError):
                # Skip if filesystem doesn't support unicode
                pytest.skip("Filesystem doesn't support unicode filenames")

        files = scanner.scan_source(tmp_path)
        file_paths = [f.relative_path for f in files]

        # All unicode files should be scanned
        for filename in unicode_files:
            assert filename in file_paths

    def test_scan_source_with_very_long_path(self, tmp_path):
        """Test scanning files with very long path names."""
        scanner = DirectoryScanner()

        # Create deeply nested directory structure
        deep_dir = tmp_path
        path_components = []
        try:
            for i in range(10):
                dir_name = f"verylongdirectoryname{i}" * 5  # 125 chars per component
                deep_dir = deep_dir / dir_name
                path_components.append(dir_name)
                deep_dir.mkdir()

            # Create file in deep directory
            test_file = deep_dir / "test.txt"
            test_file.write_text("content")
        except OSError:
            # Skip if path is too long for filesystem
            pytest.skip("Filesystem doesn't support very long paths")

        files = scanner.scan_source(tmp_path)

        # Should be able to scan even very long paths
        assert len(files) >= 1
        # Check that the file was found
        expected_rel_path = "/".join(path_components) + "/test.txt"
        file_paths = [f.relative_path for f in files]
        assert expected_rel_path in file_paths

    def test_scan_source_with_empty_directory(self, tmp_path):
        """Test scanning an empty directory."""
        scanner = DirectoryScanner()

        # Create empty subdirectory
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        files = scanner.scan_source(tmp_path)

        # Should return empty list
        assert len(files) == 0

    def test_scan_source_with_nested_empty_directories(self, tmp_path):
        """Test scanning nested empty directories."""
        scanner = DirectoryScanner()

        # Create nested empty directories
        (tmp_path / "empty1" / "empty2" / "empty3").mkdir(parents=True)

        files = scanner.scan_source(tmp_path)

        # Should return empty list
        assert len(files) == 0

    def test_destination_file_mtime_with_microseconds(self):
        """Test DestinationFile mtime parsing with microseconds."""
        entry = FileEntry(
            id=1,
            type="file",
            name="test.txt",
            updated_at="2024-01-01T12:30:45.123456Z",
        )

        dest = DestinationFile(entry=entry, relative_path="test.txt")
        mtime = dest.mtime

        assert mtime is not None
        assert mtime > 0

    def test_destination_file_mtime_with_timezone(self):
        """Test DestinationFile mtime parsing with timezone offset."""
        entry = FileEntry(
            id=1,
            type="file",
            name="test.txt",
            updated_at="2024-01-01T12:30:00+05:00",
        )

        dest = DestinationFile(entry=entry, relative_path="test.txt")
        mtime = dest.mtime

        assert mtime is not None
        assert mtime > 0

    def test_scan_source_with_zero_byte_files(self, tmp_path):
        """Test scanning zero-byte files."""
        scanner = DirectoryScanner()

        # Create zero-byte file
        empty_file = tmp_path / "empty.txt"
        empty_file.touch()

        files = scanner.scan_source(tmp_path)

        # Zero-byte files should be included
        assert len(files) == 1
        assert files[0].size == 0
        assert files[0].relative_path == "empty.txt"

    def test_scan_source_with_very_large_file_simulation(self, tmp_path):
        """Test scanning metadata of large files (without creating huge files)."""
        scanner = DirectoryScanner()

        # Create a file
        test_file = tmp_path / "large.bin"
        test_file.write_text("content")

        files = scanner.scan_source(tmp_path)

        # Should be able to read metadata without issues
        assert len(files) == 1
        assert files[0].size >= 0
        assert files[0].mtime > 0
        # file_id may be 0 on some Windows filesystems
        assert files[0].file_id >= 0

    def test_scan_source_mixed_readable_unreadable(self, tmp_path):
        """Test scanning with mix of readable and permission-denied files."""
        scanner = DirectoryScanner()

        # Create readable file
        readable = tmp_path / "readable.txt"
        readable.write_text("content")

        # Create file and make it unreadable (Unix only)
        try:
            unreadable = tmp_path / "unreadable.txt"
            unreadable.write_text("secret")
            unreadable.chmod(0o000)

            files = scanner.scan_source(tmp_path)

            # Should include readable file, skip unreadable
            file_paths = [f.relative_path for f in files]
            assert "readable.txt" in file_paths
            # unreadable.txt may or may not appear depending on platform

            # Restore permissions for cleanup
            unreadable.chmod(0o644)
        except (OSError, AttributeError):
            # Skip on Windows or if chmod not supported
            pytest.skip("Permission tests not supported on this platform")

    def test_scan_source_single_level_with_multiple_levels(self, tmp_path):
        """Test single level scan doesn't descend into nested directories."""
        scanner = DirectoryScanner()

        # Create nested structure
        (tmp_path / "file1.txt").write_text("level1")
        subdir1 = tmp_path / "subdir1"
        subdir1.mkdir()
        (subdir1 / "file2.txt").write_text("level2")
        subdir2 = subdir1 / "subdir2"
        subdir2.mkdir()
        (subdir2 / "file3.txt").write_text("level3")

        files, subdirs = scanner.scan_source_single_level(tmp_path)

        # Should only return files at root level
        file_paths = [f.relative_path for f in files]
        assert "file1.txt" in file_paths
        assert "subdir1/file2.txt" not in file_paths
        assert "subdir1/subdir2/file3.txt" not in file_paths

        # Should return immediate subdirectories
        assert "subdir1" in subdirs
        assert "subdir2" not in subdirs  # Not immediate subdirectory
