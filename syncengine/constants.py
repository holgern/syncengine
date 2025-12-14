"""Constants and default configuration values for syncengine.

This module contains default values for various sync operations that can
be overridden by users or cloud service implementations.
"""

# Default chunk size for multipart uploads (5 MB)
# Most cloud services use 5MB as the minimum chunk size
DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024  # 5 MB

# Default threshold for using multipart upload (100 MB)
# Files larger than this will use multipart/chunked upload
DEFAULT_MULTIPART_THRESHOLD = 100 * 1024 * 1024  # 100 MB

# Default retry settings
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0  # seconds

# Default timeout for future.result() to allow Ctrl+C handling
# This is needed for proper KeyboardInterrupt handling on Windows
FUTURE_RESULT_TIMEOUT = 0.5  # seconds

# Default concurrency limits
DEFAULT_TRANSFERS_LIMIT = 10  # Max concurrent uploads/downloads
DEFAULT_OPERATIONS_LIMIT = 20  # Max concurrent normal operations (deletes, renames)

# Default batch sizes
DEFAULT_BATCH_SIZE = 50  # Number of files per batch in streaming mode

# Default names for sync-related files and directories
# These can be overridden via SyncConfig
DEFAULT_IGNORE_FILE_NAME = ".syncignore"
DEFAULT_LOCAL_TRASH_DIR_NAME = (
    ".syncengine.trash.source"  # Deprecated, use DEFAULT_SOURCE_TRASH_DIR_NAME
)
DEFAULT_SOURCE_TRASH_DIR_NAME = ".syncengine.trash.source"
DEFAULT_STATE_DIR_NAME = "syncengine"  # Under ~/.config/


def format_size(size_bytes: int) -> str:
    """Format bytes into human-readable size string.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable size string (e.g., "1.5 MB", "256 KB")

    Examples:
        >>> format_size(1024)
        '1.00 KB'
        >>> format_size(1536000)
        '1.46 MB'
        >>> format_size(1073741824)
        '1.00 GB'
    """
    if size_bytes < 0:
        return "0 B"

    size_float = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if abs(size_float) < 1024.0:
            if unit == "B":
                return f"{int(size_float)} {unit}"
            return f"{size_float:.2f} {unit}"
        size_float /= 1024.0

    return f"{size_float:.2f} EB"
