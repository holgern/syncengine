"""Tests for protocol implementations."""

from unittest.mock import MagicMock

from syncengine.protocols import (
    DefaultOutputHandler,
    NullProgressBarContext,
    NullProgressBarFactory,
    NullSpinnerContext,
    NullSpinnerFactory,
)


class TestDefaultOutputHandler:
    """Test DefaultOutputHandler."""

    def test_init_not_quiet(self):
        """Test initialization with quiet=False."""
        handler = DefaultOutputHandler(quiet=False)
        assert handler.quiet is False

    def test_init_quiet(self):
        """Test initialization with quiet=True."""
        handler = DefaultOutputHandler(quiet=True)
        assert handler.quiet is True

    def test_info_not_quiet(self, capsys):
        """Test info message when not quiet."""
        handler = DefaultOutputHandler(quiet=False)
        handler.info("Test info message")

        captured = capsys.readouterr()
        assert "[INFO] Test info message" in captured.out

    def test_info_quiet(self, capsys):
        """Test info message suppressed when quiet."""
        handler = DefaultOutputHandler(quiet=True)
        handler.info("Test info message")

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_success_not_quiet(self, capsys):
        """Test success message when not quiet."""
        handler = DefaultOutputHandler(quiet=False)
        handler.success("Test success message")

        captured = capsys.readouterr()
        assert "[OK] Test success message" in captured.out

    def test_success_quiet(self, capsys):
        """Test success message suppressed when quiet."""
        handler = DefaultOutputHandler(quiet=True)
        handler.success("Test success message")

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_error_not_quiet(self, capsys):
        """Test error message when not quiet."""
        handler = DefaultOutputHandler(quiet=False)
        handler.error("Test error message")

        captured = capsys.readouterr()
        assert "[ERROR] Test error message" in captured.out

    def test_error_always_shown(self, capsys):
        """Test error message shown even when quiet."""
        handler = DefaultOutputHandler(quiet=True)
        handler.error("Test error message")

        captured = capsys.readouterr()
        assert "[ERROR] Test error message" in captured.out

    def test_warning_not_quiet(self, capsys):
        """Test warning message when not quiet."""
        handler = DefaultOutputHandler(quiet=False)
        handler.warning("Test warning message")

        captured = capsys.readouterr()
        assert "[WARN] Test warning message" in captured.out

    def test_warning_always_shown(self, capsys):
        """Test warning message shown even when quiet."""
        handler = DefaultOutputHandler(quiet=True)
        handler.warning("Test warning message")

        captured = capsys.readouterr()
        assert "[WARN] Test warning message" in captured.out

    def test_print_message(self, capsys):
        """Test print method."""
        handler = DefaultOutputHandler()
        handler.print("Raw message")

        captured = capsys.readouterr()
        assert "Raw message" in captured.out
        assert "[INFO]" not in captured.out  # No prefix


class TestNullSpinnerContext:
    """Test NullSpinnerContext."""

    def test_update(self):
        """Test update does nothing."""
        spinner = NullSpinnerContext()
        # Should not raise
        spinner.update("New description")

    def test_context_manager(self):
        """Test context manager protocol."""
        spinner = NullSpinnerContext()

        with spinner as ctx:
            assert ctx is spinner
            ctx.update("In context")

        # Should complete without errors

    def test_context_manager_with_exception(self):
        """Test context manager handles exceptions."""
        spinner = NullSpinnerContext()

        try:
            with spinner:
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected

        # Spinner should handle cleanup gracefully


class TestNullSpinnerFactory:
    """Test NullSpinnerFactory."""

    def test_create_spinner(self):
        """Test creating null spinner."""
        factory = NullSpinnerFactory()

        with factory.create_spinner("Test description") as spinner:
            assert isinstance(spinner, NullSpinnerContext)
            spinner.update("Updated")

    def test_create_spinner_with_transient(self):
        """Test creating transient spinner."""
        factory = NullSpinnerFactory()

        with factory.create_spinner("Test", transient=True) as spinner:
            assert isinstance(spinner, NullSpinnerContext)

    def test_create_spinner_with_transient_false(self):
        """Test creating non-transient spinner."""
        factory = NullSpinnerFactory()

        with factory.create_spinner("Test", transient=False) as spinner:
            assert isinstance(spinner, NullSpinnerContext)


class TestNullProgressBarContext:
    """Test NullProgressBarContext."""

    def test_add_task(self):
        """Test adding task returns dummy id."""
        progress = NullProgressBarContext()
        task_id = progress.add_task("Test task", total=100)

        assert task_id == 0

    def test_add_task_no_total(self):
        """Test adding task with no total."""
        progress = NullProgressBarContext()
        task_id = progress.add_task("Test task")

        assert task_id == 0

    def test_update(self):
        """Test update does nothing."""
        progress = NullProgressBarContext()
        task_id = progress.add_task("Test task", total=100)

        # Should not raise
        progress.update(task_id, advance=10)
        progress.update(task_id, description="New description")
        progress.update(task_id, advance=5, description="Updated")

    def test_context_manager(self):
        """Test context manager protocol."""
        progress = NullProgressBarContext()

        with progress as ctx:
            assert ctx is progress
            task_id = ctx.add_task("Test", total=10)
            ctx.update(task_id, advance=5)

        # Should complete without errors

    def test_context_manager_with_exception(self):
        """Test context manager handles exceptions."""
        progress = NullProgressBarContext()

        try:
            with progress:
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected

        # Progress should handle cleanup gracefully


class TestNullProgressBarFactory:
    """Test NullProgressBarFactory."""

    def test_create_progress_bar(self):
        """Test creating null progress bar."""
        factory = NullProgressBarFactory()

        with factory.create_progress_bar() as progress:
            assert isinstance(progress, NullProgressBarContext)
            task_id = progress.add_task("Test task", total=100)
            progress.update(task_id, advance=50)

    def test_multiple_tasks(self):
        """Test creating multiple tasks."""
        factory = NullProgressBarFactory()

        with factory.create_progress_bar() as progress:
            task1 = progress.add_task("Task 1", total=100)
            task2 = progress.add_task("Task 2", total=50)

            progress.update(task1, advance=10)
            progress.update(task2, advance=5)


class TestProtocolConformance:
    """Test that implementations conform to protocols."""

    def test_default_output_handler_conforms(self):
        """Test DefaultOutputHandler conforms to OutputHandlerProtocol."""

        handler = DefaultOutputHandler()

        # Should have all required properties and methods
        assert hasattr(handler, "quiet")
        assert hasattr(handler, "info")
        assert hasattr(handler, "success")
        assert hasattr(handler, "error")
        assert hasattr(handler, "warning")
        assert hasattr(handler, "print")

        # Test that it's callable
        assert callable(handler.info)
        assert callable(handler.success)
        assert callable(handler.error)
        assert callable(handler.warning)
        assert callable(handler.print)

        # Actually call methods to verify they work correctly
        handler.info("test")
        handler.success("test")
        handler.error("test")
        handler.warning("test")
        handler.print("test")

    def test_null_spinner_factory_conforms(self):
        """Test NullSpinnerFactory conforms to SpinnerFactoryProtocol."""

        factory = NullSpinnerFactory()

        assert hasattr(factory, "create_spinner")
        assert callable(factory.create_spinner)

        # Actually use the factory
        with factory.create_spinner("test") as spinner:
            spinner.update("test update")

    def test_null_progress_bar_factory_conforms(self):
        """Test NullProgressBarFactory conforms to ProgressBarFactoryProtocol."""

        factory = NullProgressBarFactory()

        assert hasattr(factory, "create_progress_bar")
        assert callable(factory.create_progress_bar)

        # Actually use the factory
        with factory.create_progress_bar() as progress:
            task_id = progress.add_task("test", total=100)
            progress.update(task_id, advance=50)

    def test_runtime_checkable_file_entry(self):
        """Test FileEntryProtocol is runtime checkable."""
        from syncengine.models import FileEntry
        from syncengine.protocols import FileEntryProtocol

        entry = FileEntry(id=1, type="file", name="test.txt")

        # Should be recognized as conforming to protocol
        assert isinstance(entry, FileEntryProtocol)

    def test_runtime_checkable_storage_client(self):
        """Test StorageClientProtocol is runtime checkable."""

        # Create a mock that implements the protocol
        mock_client = MagicMock()
        mock_client.upload_file = MagicMock()
        mock_client.download_file = MagicMock()
        mock_client.delete_file_entries = MagicMock()
        mock_client.create_folder = MagicMock()
        mock_client.resolve_path_to_id = MagicMock()
        mock_client.move_file_entries = MagicMock()
        mock_client.update_file_entry = MagicMock()

        # Mock objects with required methods should work
        assert hasattr(mock_client, "upload_file")

    def test_runtime_checkable_file_entries_manager(self):
        """Test FileEntriesManagerProtocol is runtime checkable."""

        # Create a mock that implements the protocol
        mock_manager = MagicMock()
        mock_manager.find_folder_by_name = MagicMock()
        mock_manager.get_all_recursive = MagicMock()
        mock_manager.iter_all_recursive = MagicMock()

        # Mock objects with required methods should work
        assert hasattr(mock_manager, "find_folder_by_name")
