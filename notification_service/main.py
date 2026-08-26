#!/usr/bin/env python3
"""
ScreenScout Dedicated Notification Service Entrypoint
"""
import sys
from pathlib import Path

# Add root directory to sys.path
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from notification_service.server import run_server

if __name__ == "__main__":
    run_server()
