"""
SecuriQR - Dual-Layer Authenticated Barcode System
A secure QR code system that combines public data with cryptographic signatures.
"""

__version__ = "1.0.0"

from .core.engine import SecuriQREngine
from .processing.decoder import BarcodeDecoder

__all__ = [
    'SecuriQREngine',
    'BarcodeDecoder',
]