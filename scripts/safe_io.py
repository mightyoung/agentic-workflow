import fcntl
import json
import os
import tempfile
from pathlib import Path
from typing import Any
from contextlib import contextmanager


@contextmanager
def file_lock(path: str | Path, timeout: float = 5.0):
    """
    Context manager for file-based locking using fcntl.

    Uses non-blocking exclusive lock (LOCK_EX | LOCK_NB) with fallback to blocking
    lock after timeout to prevent deadlocks.

    Args:
        path: File to lock
        timeout: Timeout in seconds (default 5.0)

    Raises:
        TimeoutError: If lock cannot be acquired within timeout
    """
    path = Path(path)
    lock_path = path.with_suffix(path.suffix + ".lock")

    # Ensure parent directory exists
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)

    try:
        # Try non-blocking lock first
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            # Lock is held by another process, wait with timeout
            import time
            waited = 0.0
            while waited < timeout:
                time.sleep(0.1)
                waited += 0.1
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    continue
            else:
                raise TimeoutError(f"Could not acquire lock on {lock_path} within {timeout}s")

        yield lock_fd

    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def safe_write_json(path: str | Path, data: Any) -> None:
    """
    Safely write data to a JSON file using an atomic rename operation.
    This prevents concurrent readers from reading partial or corrupted JSON files.

    Note: For core state files (.workflow_state.json, .artifacts.json,
    .task_tracker.json), use safe_write_json_locked() for additional safety.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Create temp file in the same directory to ensure they are on the same filesystem
    # which is required for atomic os.replace
    temp_fd, temp_path_str = tempfile.mkstemp(
        dir=str(path.parent),
        suffix=".tmp",
        prefix=path.name + "_"
    )

    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            if hasattr(data, "to_dict"):
                json.dump(data.to_dict(), f, ensure_ascii=False, indent=2)
            else:
                json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())  # Force write to disk

        # Atomic replacement
        os.replace(temp_path_str, str(path))
    except Exception:
        # Clean up temp file on failure
        if os.path.exists(temp_path_str):
            os.remove(temp_path_str)
        raise


def safe_write_json_locked(path: str | Path, data: Any, timeout: float = 5.0) -> None:
    """
    Safely write data to a JSON file with file locking for concurrent access safety.

    This is the preferred method for core state files that may be accessed by
    multiple processes concurrently.

    Args:
        path: File to write
        data: Data to serialize as JSON
        timeout: Lock acquisition timeout in seconds
    """
    path = Path(path)

    with file_lock(path, timeout=timeout):
        safe_write_json(path, data)


def safe_read_json(path: str | Path) -> Any:
    """
    Safely read a JSON file, returning None if the file doesn't exist
    or is corrupted.

    Args:
        path: JSON file to read

    Returns:
        Parsed JSON data or None on error
    """
    path = Path(path)
    if not path.exists():
        return None

    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def safe_append_jsonl(path: str | Path, record: dict) -> None:
    """
    Safely append a record to a JSONL file with file locking.

    Args:
        path: JSONL file to append to
        record: Dictionary to write as a single JSON line
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with file_lock(path, timeout=5.0):
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
