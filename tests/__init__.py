"""Test package initialization for PreDoc AI.

Ensures both project root and src/ directory are on sys.path for test discovery.
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"

for p in [str(_ROOT), str(_SRC)]:
    if p not in sys.path:
        sys.path.insert(0, p)
