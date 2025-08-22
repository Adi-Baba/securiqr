import os
import uuid
import base64
import hashlib
import hmac
import logging
from typing import Tuple

import numpy as np
import qrcode
from PIL import Image, ImageDraw

from ..utils.types import DualAuthBarcode
from ..utils.key_manager import load_or_generate_secret_key

logger = logging.getLogger(__name__)

class CryptoManager:
    """Handles cryptographic operations for SecuriQR"""
    
    HMAC_ALGORITHM = "sha256"
    DEFAULT_BARCODE_SCALE = 10
    FORCED_ECLEVEL = qrcode.constants.ERROR_CORRECT_M
    FORCED_MASK = 0
    
    # Color Map for Composite Barcode
    COMPOSITE_COLOR_MAP = {
        (False, False): 255,  # White
        (True, False): 166,   # Light Gray (data_only)
        (False, True): 90,    # Dark Gray (sig_only)
        (True, True): 0,      # Black
    }
    
    def __init__(self, key_path: str = None):
        self.key_path = key_path or os.path.join(os.path.dirname(__file__), "..", "..", "config", "manufacturer_secret.key")
        self.master_key = load_or_generate_secret_key(self.key_path)
    
    def generate_secret_key(self) -> bytes:
        """Generates a new random secret key."""
        return os.urandom(32)
    
    def derive_visual_key(self, master_key: bytes, data_matrix: np.ndarray) -> bytes:
        """
        Derive a per-barcode session key from the visual (QR) structure.
        """
        byte_representation = data_matrix.tobytes()
        visual_fingerprint = hmac.new(b'', byte_representation, hashlib.sha256).digest()
        
        session_key_list = list(master_key)
        for i in range(len(session_key_list)):
            session_key_list[i] ^= visual_fingerprint[i % len(visual_fingerprint)]
        return bytes(session_key_list)
    
    def _get_qr_version(self, data: str, error_correction) -> int:
        """Helper to determine the version of a QR code for given data."""
        qr = qrcode.QRCode(error_correction=error_correction)
        qr.add_data(data)
        qr.make(fit=True)
        return qr.version