import os
import hashlib
import logging
from typing import Tuple, Optional, Union

import numpy as np
import qrcode
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

# Import from the common module
from .common import DualAuthBarcode, get_qr_version

logger = logging.getLogger(__name__)

class CryptoManager:
    """
    Handles cryptographic operations using Asymmetric ECC (SECP256R1).
    Generator uses PRIVATE KEY to Sign.
    Verifier uses PUBLIC KEY to Verify.
    """
    
    DEFAULT_BARCODE_SCALE = 10
    FORCED_ECLEVEL = qrcode.constants.ERROR_CORRECT_M
    FORCED_MASK = 0
    
    # Color Map for Composite Barcode (Unchanged)
    COMPOSITE_COLOR_MAP = {
        (False, False): 255,  # White
        (True, False): 166,   # Light Gray (data_only)
        (False, True): 90,    # Dark Gray (sig_only)
        (True, True): 0,      # Black
    }
    
    def __init__(self, key_path: str = None):
        """
        Initialize with a key path.
        For GENERATION: Points to a Private Key file.
        For VERIFICATION: Points to a Public Key file.
        """
        self.key_path = key_path or "keys/private.pem"
        self._private_key = None
        self._public_key = None
        
        # Try to load keys if they exist
        if os.path.exists(self.key_path):
             self._load_key_from_file(self.key_path)

    def _load_key_from_file(self, path: str):
        """Helper to load key based on content."""
        with open(path, "rb") as f:
            data = f.read()
            
        try:
            # Try loading as Private Key
            self._private_key = serialization.load_pem_private_key(data, password=None)
            self._public_key = self._private_key.public_key()
            logger.info("Loaded PRIVATE KEY.")
        except:
            try:
                # Try loading as Public Key
                self._public_key = serialization.load_pem_public_key(data)
                logger.info("Loaded PUBLIC KEY.")
            except Exception as e:
                logger.error(f"Failed to load key from {path}: {e}")

    def generate_key_pair(self, save_dir: str = "keys"):
        """Generates a new ECC Key Pair and saves to disk."""
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()
        
        os.makedirs(save_dir, exist_ok=True)
        
        # Save Private Key
        pem_priv = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        with open(os.path.join(save_dir, "private.pem"), "wb") as f:
            f.write(pem_priv)
            
        # Save Public Key
        pem_pub = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        with open(os.path.join(save_dir, "public.pem"), "wb") as f:
            f.write(pem_pub)
            
        self._private_key = private_key
        self._public_key = public_key
        logger.info(f"Generated new ECC key pair in '{save_dir}/'")

    def sign_data(self, data_bytes: bytes, visual_matrix: np.ndarray) -> bytes:
        """
        Sign the data combined with the visual matrix using the Private Key.
        Signature = Sign(Hash(Data + VisualBytes))
        """
        if not self._private_key:
            raise ValueError("Private Key required for signing!")
            
        # Create a "Visual Binding" by hashing the matrix
        matrix_bytes = visual_matrix.tobytes()
        visual_hash = hashlib.sha256(matrix_bytes).digest()
        
        # Payload to sign
        payload = data_bytes + visual_hash
        
        signature = self._private_key.sign(
            payload,
            ec.ECDSA(hashes.SHA256())
        )
        return signature

    def verify_signature(self, signature: bytes, data_bytes: bytes, visual_matrix: np.ndarray) -> bool:
        """
        Verify the signature using the Public Key.
        """
        if not self._public_key:
            raise ValueError("Public Key required for verification!")
            
        matrix_bytes = visual_matrix.tobytes()
        visual_hash = hashlib.sha256(matrix_bytes).digest()
        payload = data_bytes + visual_hash
        
        try:
            self._public_key.verify(
                signature,
                payload,
                ec.ECDSA(hashes.SHA256())
            )
            return True
        except InvalidSignature:
            return False