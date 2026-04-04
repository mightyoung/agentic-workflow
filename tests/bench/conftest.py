# Benchmark tests use relative imports from scripts/utils
# Add project root to sys.path so bench tests work from tests/bench/ subdirectory
import os
import sys

# Get project root (parent of tests/)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Insert at position 0 so it takes precedence over test-file-local path manipulations
sys.path.insert(0, project_root)
# Also add scripts/utils for string_utils, lru_cache imports
sys.path.insert(0, os.path.join(project_root, "scripts", "utils"))
