"""Pytest configuration ensuring backend and frontend directories are on sys.path."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = PROJECT_ROOT / "backend"
FRONTEND_PATH = PROJECT_ROOT / "frontend"

sys.path.insert(0, str(BACKEND_PATH))
sys.path.insert(0, str(FRONTEND_PATH))
