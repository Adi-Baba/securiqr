import logging
import hmac
import hashlib
from typing import Optional

import numpy as np
import qrcode

from .crypto import CryptoManager
from ..utils.types import DualAuthBarcode

logger = logging.getLogger(__name__)

class BarcodeVerifier(CryptoManager):
    """Verifies the authenticity of dual-layer barcodes"""
    
    def verify_barcode(self, barcode: DualAuthBarcode, verbose: bool = True) -> bool:
        """
        Verify the HMAC using visually-derived key.
        Returns True if authentic, False otherwise.
        """
        public_data = barcode.public_data
        signature = barcode.signature
        
        if verbose:
            logger.info(f"Verifying barcode with public data: {public_data}")
        
        # Re-generate the QR matrix for the public data part EXACTLY
        version = self._get_qr_version(public_data, self.FORCED_ECLEVEL)
        
        qr = qrcode.QRCode(
            version=version,
            error_correction=self.FORCED_ECLEVEL,
            mask_pattern=self.FORCED_MASK,
            box_size=1,
            border=4
        )
        qr.add_data(public_data)
        qr.make(fit=False)
        data_matrix = np.array(qr.get_matrix(), dtype=bool)
        
        # Derive the session key and verify the signature
        expected_session_key = self.derive_visual_key(self.master_key, data_matrix)
        expected_signature = hmac.new(expected_session_key, public_data.encode('utf-8'), hashlib.sha256).digest()
        
        is_authentic = hmac.compare_digest(signature, expected_signature)
        
        if verbose:
            if is_authentic:
                logger.info("SUCCESS: Barcode is authentic.")
            else:
                logger.error("FAILURE: Barcode is NOT authentic. Signature mismatch.")
                logger.debug(f"Expected: {expected_signature.hex()}")
                logger.debug(f"Received: {signature.hex()}")
        
        return is_authentic
    
    def extract_secret_message(self, barcode: DualAuthBarcode) -> Optional[str]:
        """Extract the secret message from a verified barcode."""
        data_parts = barcode.public_data.split('|')
        for part in data_parts:
            if part.startswith("secret:"):
                return part.split(":", 1)[1]
        return None