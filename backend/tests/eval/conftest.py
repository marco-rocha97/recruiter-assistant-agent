"""
pytest configuration for the eval tests.

Adds the repo root to sys.path so that `scripts.eval_harness` is importable
from backend/tests/eval/test_agreement.py. Mirrors the sys.path manipulation
used in scripts/prepare_dataset.py and scripts/eval_harness.py themselves.
"""

import sys
from pathlib import Path

# backend/ → backend/tests/eval/conftest.py → repo root is three levels up
_REPO_ROOT = Path(__file__).parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
