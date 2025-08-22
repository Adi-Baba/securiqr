"""
SecuriQR - Dual-Layer Authenticated Barcode System
A secure QR code system that combines public data with cryptographic signatures.
"""

__version__ = "1.0.0"

from .core.generator import BarcodeGenerator
from .core.verifier import BarcodeVerifier
from .processing.decoder import BarcodeDecoder
from .processing.image_processor import ImageProcessor

__all__ = [
    'BarcodeGenerator',
    'BarcodeVerifier',
    'BarcodeDecoder',
    'ImageProcessor',
]