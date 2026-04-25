"""Shared pytest fixtures.

Heavy runtime deps (PySide6, NeMo, sounddevice, pynput) are not needed for the
pure-logic tests in this directory. The tests import only from modules that
themselves avoid those imports at module top level (or we stub them).
"""
import os
import sys
from pathlib import Path

# Make `app/` importable when running `pytest` from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Tell NeMo / sounddevice not to look at hardware in case any test imports them.
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PA_ALSA_PLUGHW", "1")
