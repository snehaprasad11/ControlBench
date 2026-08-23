"""Ensure the repository root is importable during tests.

Running the bare ``pytest`` console script does not put the current directory on
``sys.path`` (unlike ``python -m pytest``), so ``import controlbench`` / ``import api``
would fail in CI. pytest adds the directory containing this conftest to ``sys.path``,
and the explicit insert below makes it robust regardless of how pytest is invoked.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
