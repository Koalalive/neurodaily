"""NeuroDaily: daily neuroscience & psychiatry literature/industry digest → HTML.

Public API:
    from neurodaily.digest import run, save_report
    from neurodaily.config import Config, DEFAULT_CONFIG
    from neurodaily.cli import main
"""
from __future__ import annotations

__version__ = "0.1.0"

from .config import Config, DEFAULT_CONFIG
from .digest import run, save_report, DigestResult
from .models import Item

__all__ = ["Config", "DEFAULT_CONFIG", "run", "save_report", "DigestResult",
           "Item", "__version__"]
