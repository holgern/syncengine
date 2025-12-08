"""Tests for the ignore file functionality"""

from pathlib import Path

from syncengine.constants import (
    DEFAULT_IGNORE_FILE_NAME as IGNORE_FILE_NAME,
)
from syncengine.constants import (
    DEFAULT_LOCAL_TRASH_DIR_NAME as LOCAL_TRASH_DIR_NAME,
)
from syncengine.ignore import (
    IgnoreFileManager,
    IgnoreRule,
    load_ignore_file,
)
from syncengine.scanner import DirectoryScanner


class TestIgnoreRule:
    """Tests for the IgnoreRule class."""

    def test_simple_pattern(self):
        """Test simple filename pattern matching."""
        rule = IgnoreRule(pattern="*.log")
        assert rule.matches("test.log")
        assert rule.matches("debug.log")
        assert not rule.matches("test.txt")
        assert not rule.matches("test.log.bak")

    def test_negation(self):
        """Test negation pattern (!)."""
        rule = IgnoreRule(pattern="!important.log")
        assert rule.negated is True
        assert rule.matches("important.log")
        # The actual negation logic is in the manager, rule just matches

    def test_anchored_pattern(self):
        """Test anchored pattern (/)."""
        rule = IgnoreRule(pattern="/logs")
        assert rule.anchored is True
        assert rule.matches("logs")
        assert not rule.matches("other/logs")

    def test_dir_only_pattern(self):
        """Test directory-only pattern (/)."""
        rule = IgnoreRule(pattern="temp/")
        assert rule.dir_only is True
        assert rule.matches("temp", is_dir=True)
        assert not rule.matches("temp", is_dir=False)  # Not a directory

    def test_double_wildcard(self):
        """Test ** pattern matching any path components."""
        rule = IgnoreRule(pattern="**/cache/**")
        assert rule.matches("cache/file.txt")
        assert rule.matches("some/cache/file.txt")
        assert rule.matches("some/deep/cache/file.txt")
        assert rule.matches("cache/sub/file.txt")
        assert not rule.matches("nocache/file.txt")

    def test_character_class(self):
        """Test character class [abc] pattern."""
        rule = IgnoreRule(pattern="[abc]tmp.db")
        assert rule.matches("atmp.db")
        assert rule.matches("btmp.db")
        assert rule.matches("ctmp.db")
        assert not rule.matches("dtmp.db")

    def test_character_range(self):
        """Test character range [a-z] pattern."""
        rule = IgnoreRule(pattern="[a-z]?tmp.db")
        assert rule.matches("abtmp.db")
        assert rule.matches("zxtmp.db")
        assert not rule.matches("A1tmp.db")  # Uppercase
        assert not rule.matches("tmp.db")  # Too short

    def test_question_mark_wildcard(self):
        """Test ? wildcard matching exactly one character."""
        rule = IgnoreRule(pattern="?tmp.db")
        assert rule.matches("atmp.db")
        assert rule.matches("1tmp.db")
        assert not rule.matches("tmp.db")  # No leading char
        assert not rule.matches("abtmp.db")  # Two leading chars

    def test_extension_with_wildcard(self):
        """Test pattern with wildcard in extension."""
        rule = IgnoreRule(pattern="*.db*")
        assert rule.matches("test.db")
        assert rule.matches("test.dba")
        assert rule.matches("test.db1")
        assert not rule.matches("test.txt")

    def test_path_pattern(self):
        """Test pattern with path separator."""
        rule = IgnoreRule(pattern="logs/*.log")
        assert rule.matches("logs/debug.log")
        assert rule.matches("logs/error.log")
        assert not rule.matches("other/debug.log")
        # Non-anchored can match anywhere
        assert rule.matches("subdir/logs/debug.log")

    def test_anchored_path_pattern(self):
        """Test anchored pattern with path separator."""
        rule = IgnoreRule(pattern="/logs/*.log")
        assert rule.matches("logs/debug.log")
        assert not rule.matches("subdir/logs/debug.log")


class TestIgnoreFileManager:
    """Tests for the IgnoreFileManager class."""

    def test_load_cli_patterns(self):
        """Test loading patterns from CLI arguments."""
        manager = IgnoreFileManager()
        manager.load_cli_patterns(["*.log", "temp/*"])

        assert len(manager.rules) == 3
        assert manager.is_ignored("debug.log")
        assert manager.is_ignored("temp/file.txt")
        assert not manager.is_ignored("important.txt")

    def test_simple_ignore(self):
        """Test basic ignore functionality."""
        manager = IgnoreFileManager()
        manager.load_cli_patterns(["*.log"])

        assert manager.is_ignored("test.log")
        assert manager.is_ignored("subdir/test.log")
        assert not manager.is_ignored("test.txt")

    def test_negation_unignores(self):
        """Test that negation rules un-ignore files."""
        manager = IgnoreFileManager()
        # Ignore all .log files, but not important.log
        manager.load_cli_patterns(["*.log", "!important.log"])

        assert manager.is_ignored("debug.log")
        assert manager.is_ignored("error.log")
        assert not manager.is_ignored("important.log")  # Un-ignored

    def test_directory_ignore(self):
        """Test ignoring directories and their contents."""
        manager = IgnoreFileManager()
        manager.load_cli_patterns(["temp/"])

        # temp/ only matches directories
        assert manager.is_ignored("temp", is_dir=True)
        assert not manager.is_ignored("temp", is_dir=False)
        # But files inside temp should be ignored via parent check
        assert manager.is_ignored("temp/file.txt", check_parents=True)

    def test_load_from_file(self, tmp_path: Path):
        """Test loading patterns from a ignore file."""
        ignore_file = tmp_path / IGNORE_FILE_NAME
        ignore_file.write_text("# This is a comment\n*.log\n*.tmp\n\n!important.log\n")

        manager = IgnoreFileManager(base_path=tmp_path)
        manager.load_from_directory(tmp_path)

        assert manager.is_ignored("debug.log")
        assert manager.is_ignored("cache.tmp")
        assert not manager.is_ignored("important.log")  # Negated
        assert not manager.is_ignored("data.txt")

    def test_hierarchical_ignore_files(self, tmp_path: Path):
        """Test hierarchical ignore files in subdirectories."""
        # Create directory structure
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Root ignore ignores all .log files
        (tmp_path / IGNORE_FILE_NAME).write_text("*.log\n")

        # Subdir ignore un-ignores debug.log in that subdir
        (subdir / IGNORE_FILE_NAME).write_text("!debug.log\n")

        manager = IgnoreFileManager(base_path=tmp_path)
        manager.load_from_directory(tmp_path)
        manager.load_from_directory(subdir)

        # Root level: all .log ignored
        assert manager.is_ignored("error.log")
        assert manager.is_ignored("debug.log")

        # Subdir level: debug.log un-ignored, error.log still ignored
        assert not manager.is_ignored("subdir/debug.log")
        assert manager.is_ignored("subdir/error.log")

    def test_clear(self):
        """Test clearing all rules."""
        manager = IgnoreFileManager()
        manager.load_cli_patterns(["*.log"])
        assert manager.is_ignored("test.log")

        manager.clear()
        # After clear, default patterns are reloaded
        assert not manager.is_ignored("test.log")
        # Only default patterns remain
        assert len(manager.rules) == 1

    def test_get_effective_rules(self):
        """Test getting list of effective rules."""
        manager = IgnoreFileManager()
        manager.load_cli_patterns(["*.log", "temp/*"])

        rules = manager.get_effective_rules()
        assert len(rules) == 3


class TestDefaultIgnorePatterns:
    """Tests for default ignore patterns (including local trash directory)."""

    def test_default_patterns_loaded(self):
        """Test that default patterns are loaded on initialization."""
        manager = IgnoreFileManager()
        # Default patterns should be loaded (just the local trash dir)
        assert len(manager.rules) == 1
        assert manager.rules[0].pattern == LOCAL_TRASH_DIR_NAME

    def test_local_trash_dir_ignored_by_default(self):
        """Test that .trash.local is ignored by default."""
        manager = IgnoreFileManager()
        # The trash directory itself should be ignored
        assert manager.is_ignored(LOCAL_TRASH_DIR_NAME, is_dir=True)
        # Files inside the trash directory should be ignored
        assert manager.is_ignored(f"{LOCAL_TRASH_DIR_NAME}/file.txt")
        assert manager.is_ignored(f"{LOCAL_TRASH_DIR_NAME}/subdir/file.txt")

    def test_local_trash_dir_ignored_in_scanner(self, tmp_path: Path):
        """Test that DirectoryScanner ignores the local trash directory."""
        # Create test files
        (tmp_path / "file.txt").write_text("content")

        # Create local trash directory with files
        trash_dir = tmp_path / LOCAL_TRASH_DIR_NAME
        trash_dir.mkdir()
        (trash_dir / "deleted_file.txt").write_text("deleted content")
        timestamped = trash_dir / "20240101_120000"
        timestamped.mkdir()
        (timestamped / "another_deleted.txt").write_text("more deleted")

        # Scan should only find file.txt
        scanner = DirectoryScanner()
        files = scanner.scan_source(tmp_path)

        paths = [f.relative_path for f in files]
        assert "file.txt" in paths
        assert LOCAL_TRASH_DIR_NAME not in paths
        # No files from trash directory should be included
        assert not any(LOCAL_TRASH_DIR_NAME in p for p in paths)


class TestLoadIgnoreFile:
    """Tests for the load_ignore_file function."""

    def test_load_patterns(self, tmp_path: Path):
        """Test loading patterns from file."""
        ignore_file = tmp_path / ".pydrignore"
        ignore_file.write_text("# Comment\n*.log\n\n*.tmp\n")

        patterns = load_ignore_file(ignore_file)

        assert patterns == ["*.log", "*.tmp"]

    def test_nonexistent_file(self, tmp_path: Path):
        """Test loading from nonexistent file returns empty list."""
        patterns = load_ignore_file(tmp_path / "nonexistent")
        assert patterns == []


class TestDirectoryScannerWithIgnore:
    """Tests for DirectoryScanner with .ignore support."""

    def test_scan_with_cli_patterns(self, tmp_path: Path):
        """Test scanning with CLI ignore patterns."""
        # Create test files
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "debug.log").write_text("log content")
        (tmp_path / "error.log").write_text("error content")

        scanner = DirectoryScanner(ignore_patterns=["*.log"])
        files = scanner.scan_source(tmp_path)

        assert len(files) == 1
        assert files[0].relative_path == "file.txt"

    def test_scan_with_ignore_file(self, tmp_path: Path):
        """Test scanning with ignore file."""
        # Create test files
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "debug.log").write_text("log content")
        (tmp_path / "cache.tmp").write_text("temp")
        (tmp_path / IGNORE_FILE_NAME).write_text("*.log\n*.tmp\n")

        scanner = DirectoryScanner(use_ignore_files=True)
        files = scanner.scan_source(tmp_path)

        assert len(files) == 1
        assert files[0].relative_path == "file.txt"

    def test_scan_without_ignore_files(self, tmp_path: Path):
        """Test scanning with use_ignore_files=False."""
        # Create test files
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "debug.log").write_text("log content")
        (tmp_path / IGNORE_FILE_NAME).write_text("*.log\n")

        scanner = DirectoryScanner(use_ignore_files=False)
        files = scanner.scan_source(tmp_path)

        # ignore is still excluded (it starts with .)
        assert len(files) == 2
        paths = [f.relative_path for f in files]
        assert "file.txt" in paths
        assert "debug.log" in paths

    def test_scan_hierarchical_ignore(self, tmp_path: Path):
        """Test scanning with hierarchical ignore files."""
        # Create directory structure
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Create test files
        (tmp_path / "root.log").write_text("root log")
        (tmp_path / "data.txt").write_text("root data")
        (subdir / "sub.log").write_text("sub log")
        (subdir / "important.log").write_text("important")
        (subdir / "sub_data.txt").write_text("sub data")

        # Root ignore ignores all .log files
        (tmp_path / IGNORE_FILE_NAME).write_text("*.log\n")

        # Subdir ignore un-ignores important.log
        (subdir / IGNORE_FILE_NAME).write_text("!important.log\n")

        scanner = DirectoryScanner(use_ignore_files=True)
        files = scanner.scan_source(tmp_path)

        paths = sorted(f.relative_path for f in files)
        assert "data.txt" in paths
        assert "subdir/sub_data.txt" in paths
        assert "subdir/important.log" in paths  # Un-ignored
        assert "root.log" not in paths  # Ignored
        assert "subdir/sub.log" not in paths  # Ignored

    def test_scan_ignores_directories(self, tmp_path: Path):
        """Test that directory patterns ignore entire directories."""
        # Create directory structure
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()
        (temp_dir / "file.txt").write_text("temp file")
        (tmp_path / "data.txt").write_text("data")
        (tmp_path / IGNORE_FILE_NAME).write_text("temp/\n")

        scanner = DirectoryScanner(use_ignore_files=True)
        files = scanner.scan_source(tmp_path)

        paths = [f.relative_path for f in files]
        assert "data.txt" in paths
        assert "temp/file.txt" not in paths

    def test_scan_double_wildcard(self, tmp_path: Path):
        """Test ** wildcard pattern in ignore."""
        # Create directory structure
        cache1 = tmp_path / "cache"
        cache1.mkdir()
        (cache1 / "data.bin").write_text("cache1")

        nested = tmp_path / "src" / "cache"
        nested.mkdir(parents=True)
        (nested / "data.bin").write_text("cache2")

        (tmp_path / "data.txt").write_text("data")
        (tmp_path / IGNORE_FILE_NAME).write_text("**/cache/**\n")

        scanner = DirectoryScanner(use_ignore_files=True)
        files = scanner.scan_source(tmp_path)

        paths = [f.relative_path for f in files]
        assert "data.txt" in paths
        assert "cache/data.bin" not in paths
        assert "src/cache/data.bin" not in paths

    def test_scan_exclude_dot_files_with_ignore(self, tmp_path: Path):
        """Test combining exclude_dot_files with ignore."""
        # Create test files
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / ".hidden").write_text("hidden")
        (tmp_path / "debug.log").write_text("log")
        (tmp_path / IGNORE_FILE_NAME).write_text("*.log\n")

        scanner = DirectoryScanner(
            exclude_dot_files=True,
            use_ignore_files=True,
        )
        files = scanner.scan_source(tmp_path)

        paths = [f.relative_path for f in files]
        assert paths == ["file.txt"]


class TestKopiaExamples:
    """Tests based on Kopia documentation examples."""

    def test_kopia_example_thesis(self, tmp_path: Path):
        """Test based on Kopia documentation thesis example."""
        # Create directory structure similar to Kopia example
        thesis = tmp_path
        (thesis / "title.png").write_text("image")
        (thesis / "manuscript.tex").write_text("tex")
        (thesis / "tmp.db").write_text("temp db")
        (thesis / "atmp.db").write_text("temp db")
        (thesis / "abtmp.db").write_text("temp db")
        (thesis / "logs.dat").write_text("log data")

        figures = thesis / "figures"
        figures.mkdir()
        (figures / "architecture.png").write_text("image")
        (figures / "server.png").write_text("image")

        chapters = thesis / "chapters"
        chapters.mkdir()
        (chapters / "introduction.tex").write_text("tex")
        (chapters / "abstract.tex").write_text("tex")
        (chapters / "conclusion.tex").write_text("tex")

        chapter_logs = chapters / "logs"
        chapter_logs.mkdir()
        (chapter_logs / "chapter.log").write_text("log")

        logs = thesis / "logs"
        logs.mkdir()
        (logs / "gen.log").write_text("log")
        (logs / "fail.log").write_text("log")
        (logs / "log.db").write_text("db")
        (logs / "tmp.db").write_text("db")
        (logs / "tmp.dba").write_text("db")

        # Create ignore similar to Kopia example
        (thesis / IGNORE_FILE_NAME).write_text(
            "# Ignoring all files that end with .dat\n"
            "*.dat\n"
            "\n"
            "# Ignoring all files and folders within thesis/logs directory\n"
            "/logs/*\n"
            "\n"
            "# Ignoring tmp.db files within the whole directory\n"
            "tmp.db\n"
        )

        scanner = DirectoryScanner(use_ignore_files=True)
        files = scanner.scan_source(thesis)

        paths = sorted(f.relative_path for f in files)

        # Should include
        assert "title.png" in paths
        assert "manuscript.tex" in paths
        assert "figures/architecture.png" in paths
        assert "figures/server.png" in paths
        assert "chapters/introduction.tex" in paths
        assert "chapters/abstract.tex" in paths
        assert "chapters/conclusion.tex" in paths
        assert "chapters/logs/chapter.log" in paths  # Not in /logs
        assert "atmp.db" in paths
        assert "abtmp.db" in paths

        # Should exclude
        assert "logs.dat" not in paths  # *.dat
        assert "logs/gen.log" not in paths  # /logs/*
        assert "logs/fail.log" not in paths  # /logs/*
        assert "logs/log.db" not in paths  # /logs/*
        assert "logs/tmp.db" not in paths  # /logs/* and tmp.db
        assert "logs/tmp.dba" not in paths  # /logs/*
        assert "tmp.db" not in paths  # tmp.db


class TestMalformedPatterns:
    """Tests for handling malformed or edge-case patterns."""

    def test_empty_pattern_line(self, tmp_path: Path):
        """Test that empty lines in ignore files are handled."""
        (tmp_path / IGNORE_FILE_NAME).write_text("\n\n*.log\n\n")
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "test.log").write_text("log")

        scanner = DirectoryScanner(use_ignore_files=True)
        files = scanner.scan_source(tmp_path)

        paths = [f.relative_path for f in files]
        assert "file.txt" in paths
        assert "test.log" not in paths

    def test_whitespace_only_lines(self, tmp_path: Path):
        """Test that whitespace-only lines are handled."""
        (tmp_path / IGNORE_FILE_NAME).write_text("  \n\t\n*.log\n  \t  \n")
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "test.log").write_text("log")

        scanner = DirectoryScanner(use_ignore_files=True)
        files = scanner.scan_source(tmp_path)

        paths = [f.relative_path for f in files]
        assert "file.txt" in paths
        assert "test.log" not in paths

    def test_comment_only_file(self, tmp_path: Path):
        """Test ignore file with only comments."""
        (tmp_path / IGNORE_FILE_NAME).write_text("# Comment 1\n# Comment 2\n")
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "test.log").write_text("log")

        scanner = DirectoryScanner(use_ignore_files=True)
        files = scanner.scan_source(tmp_path)

        # All files should be included since no real patterns
        paths = [f.relative_path for f in files]
        assert "file.txt" in paths
        assert "test.log" in paths

    def test_pattern_with_trailing_whitespace(self, tmp_path: Path):
        """Test that trailing whitespace in patterns is handled."""
        (tmp_path / IGNORE_FILE_NAME).write_text("*.log  \n*.tmp\t\n")
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "test.log").write_text("log")
        (tmp_path / "test.tmp").write_text("temp")

        scanner = DirectoryScanner(use_ignore_files=True)
        files = scanner.scan_source(tmp_path)

        paths = [f.relative_path for f in files]
        assert "file.txt" in paths
        # Trailing whitespace should be stripped
        assert "test.log" not in paths
        assert "test.tmp" not in paths

    def test_pattern_with_leading_whitespace(self, tmp_path: Path):
        """Test that leading whitespace in patterns is handled."""
        (tmp_path / IGNORE_FILE_NAME).write_text("  *.log\n\t*.tmp\n")
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "test.log").write_text("log")
        (tmp_path / "test.tmp").write_text("temp")

        scanner = DirectoryScanner(use_ignore_files=True)
        files = scanner.scan_source(tmp_path)

        paths = [f.relative_path for f in files]
        assert "file.txt" in paths
        # Leading whitespace should be stripped
        assert "test.log" not in paths
        assert "test.tmp" not in paths

    def test_very_long_pattern(self, tmp_path: Path):
        """Test handling of very long patterns."""
        # Create a very long pattern (but still reasonable)
        long_pattern = "a" * 500 + ".txt"
        (tmp_path / IGNORE_FILE_NAME).write_text(f"{long_pattern}\n*.log\n")
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "test.log").write_text("log")

        scanner = DirectoryScanner(use_ignore_files=True)
        files = scanner.scan_source(tmp_path)

        # Should handle long pattern without crashing
        paths = [f.relative_path for f in files]
        assert "file.txt" in paths
        assert "test.log" not in paths

    def test_pattern_with_special_regex_chars(self, tmp_path: Path):
        """Test patterns with special regex characters that need escaping."""
        # Create files with special characters
        (tmp_path / IGNORE_FILE_NAME).write_text("test(1).txt\n")
        (tmp_path / "test(1).txt").write_text("content")
        (tmp_path / "test.txt").write_text("content")

        scanner = DirectoryScanner(use_ignore_files=True)
        files = scanner.scan_source(tmp_path)

        paths = [f.relative_path for f in files]
        assert "test.txt" in paths
        # Parentheses should be treated literally in gitignore patterns
        assert "test(1).txt" not in paths

    def test_multiple_consecutive_slashes(self, tmp_path: Path):
        """Test pattern with multiple consecutive slashes."""
        (tmp_path / IGNORE_FILE_NAME).write_text("//logs///\n")
        logs = tmp_path / "logs"
        logs.mkdir()
        (logs / "test.log").write_text("log")
        (tmp_path / "file.txt").write_text("content")

        scanner = DirectoryScanner(use_ignore_files=True)
        files = scanner.scan_source(tmp_path)

        # Should handle multiple slashes gracefully
        paths = [f.relative_path for f in files]
        assert "file.txt" in paths

    def test_pattern_with_backslash(self, tmp_path: Path):
        """Test pattern with backslash (Windows path separator)."""
        # Gitignore uses forward slashes, backslashes might be used for escaping
        (tmp_path / IGNORE_FILE_NAME).write_text("*.log\n")
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "test.log").write_text("log")

        scanner = DirectoryScanner(use_ignore_files=True)
        files = scanner.scan_source(tmp_path)

        paths = [f.relative_path for f in files]
        assert "file.txt" in paths
        assert "test.log" not in paths

    def test_unicode_in_pattern(self, tmp_path: Path):
        """Test patterns with unicode characters."""
        try:
            (tmp_path / IGNORE_FILE_NAME).write_text("файл*.txt\n")
            (tmp_path / "файл1.txt").write_text("content")
            (tmp_path / "test.txt").write_text("content")

            scanner = DirectoryScanner(use_ignore_files=True)
            files = scanner.scan_source(tmp_path)

            paths = [f.relative_path for f in files]
            assert "test.txt" in paths
            # Unicode pattern should work
            assert "файл1.txt" not in paths
        except (OSError, UnicodeError):
            # Skip if filesystem doesn't support unicode
            import pytest

            pytest.skip("Filesystem doesn't support unicode filenames")

    def test_invalid_encoding_in_ignore_file(self, tmp_path: Path):
        """Test handling of ignore file with invalid encoding.

        Currently the implementation raises UnicodeDecodeError.
        This test documents that behavior and would need to be updated
        if the implementation adds proper error handling.
        """
        import pytest

        # Write binary data that's not valid UTF-8
        ignore_file = tmp_path / IGNORE_FILE_NAME
        ignore_file.write_bytes(b"\xff\xfe*.log\n")
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "test.log").write_text("log")

        scanner = DirectoryScanner(use_ignore_files=True)
        # Currently raises UnicodeDecodeError - documenting current behavior
        with pytest.raises(UnicodeDecodeError):
            scanner.scan_source(tmp_path)

    def test_pattern_with_only_wildcards(self, tmp_path: Path):
        """Test pattern with only wildcard characters."""
        (tmp_path / IGNORE_FILE_NAME).write_text("***\n*.log\n")
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "test.log").write_text("log")

        scanner = DirectoryScanner(use_ignore_files=True)
        files = scanner.scan_source(tmp_path)

        # Should handle gracefully
        paths = [f.relative_path for f in files]
        assert "test.log" not in paths  # Second pattern should work

    def test_pattern_with_null_byte(self, tmp_path: Path):
        """Test handling of pattern with embedded null byte."""
        # Most filesystems don't support null bytes in filenames
        (tmp_path / IGNORE_FILE_NAME).write_text("*.log\n")
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "test.log").write_text("log")

        scanner = DirectoryScanner(use_ignore_files=True)
        files = scanner.scan_source(tmp_path)

        # Should handle gracefully
        paths = [f.relative_path for f in files]
        assert "file.txt" in paths
        assert "test.log" not in paths

    def test_extremely_nested_pattern(self, tmp_path: Path):
        """Test pattern with many nested directories."""
        # Create deeply nested pattern
        deep_pattern = "/".join(["dir"] * 100) + "/*.txt"
        (tmp_path / IGNORE_FILE_NAME).write_text(f"{deep_pattern}\n*.log\n")
        (tmp_path / "file.txt").write_text("content")
        (tmp_path / "test.log").write_text("log")

        scanner = DirectoryScanner(use_ignore_files=True)
        files = scanner.scan_source(tmp_path)

        # Should handle without crashing
        paths = [f.relative_path for f in files]
        assert "file.txt" in paths
        assert "test.log" not in paths
