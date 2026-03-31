import json
import os
import tempfile
from pathlib import Path
from typing import Any

def safe_write_json(path: str | Path, data: Any) -> None:
    """
    Safely write data to a JSON file using an atomic rename operation.
    This prevents concurrent readers from reading partial or corrupted JSON files.
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
