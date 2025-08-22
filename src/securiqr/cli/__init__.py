"""
Command-line interface tools for SecuriQR.
"""

from .generate import main as generate_main
from .verify import main as verify_main
from .universal_reader import main as read_main

__all__ = [
    'generate_main',
    'verify_main',
    'read_main',
]