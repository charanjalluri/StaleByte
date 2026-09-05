"""
conftest.py
-----------
Adds the stalebyte/ directory to sys.path so that all test modules can import
from lib/, runtime/, and scenarios/ without per-file sys.path manipulation.
"""
import sys
from pathlib import Path

# Insert stalebyte/ at the front of the path
sys.path.insert(0, str(Path(__file__).parent))
