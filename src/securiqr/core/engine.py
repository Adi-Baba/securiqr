import os
import uuid
import base64
import json
import logging
from typing import Tuple, Optional

import numpy as np
import qrcode
from PIL import Image, ImageDraw

from .crypto import CryptoManager
from .common import DualAuthBarcode, get_qr_version

logger = logging.getLogger(__name__)

class SecuriQREngine:
    """
    Unified engine for generating and verifying SecuriQR codes.
    Uses composition with CryptoManager for security operations.
    """
    
    def __init__(self, key_path: str = None):
        self.crypto = CryptoManager(key_path)

    # --- Generation Logic ---

    def create_barcode(self, public_data: str, secret_message: str = "") -> Tuple[DualAuthBarcode, np.ndarray, int, int, int]:
        """
        Create a signed barcode for `public_data` with optional secret message.
        Returns (DualAuthBarcode, data_matrix, version, eclevel, mask).
        """
        # Use JSON for structured, safe payload
        payload = {
            "d": public_data,
            "s": secret_message,
            "u": str(uuid.uuid4())
        }
        # Separators=(',', ':') removes whitespace for minification
        padded_unique_data = json.dumps(payload, separators=(',', ':'))
        
        logger.info(f"Creating barcode for data: {public_data}")
        
        # Determine final QR version to hold both data and signature
        temp_sig_base64 = base64.b64encode(os.urandom(32)).decode('ascii')
        
        data_version = get_qr_version(padded_unique_data, self.crypto.FORCED_ECLEVEL)
        sig_version = get_qr_version(temp_sig_base64, self.crypto.FORCED_ECLEVEL)
        final_version = max(data_version, sig_version)
        
        # Pad the data string with spaces if necessary
        # Note: JSON payload allows padding if we just append space after the closed brace, 
        # BUT standard JSON parsers might stop at the brace. 
        # A safer way to pad for QR version consistency is to add a padding field to JSON.
        # However, for now preserving original logic: simply creating the QR object handles usage.
        # But wait, original code did: while get_qr_version(...) < final_version: data += " "
        # We need to respect that to ensure the matrix size matches the signature matrix size.
        
        while get_qr_version(padded_unique_data, self.crypto.FORCED_ECLEVEL) < final_version:
             padded_unique_data += " "
        
        # Build final QR for the public data
        qr = qrcode.QRCode(
            version=final_version,
            error_correction=self.crypto.FORCED_ECLEVEL,
            mask_pattern=self.crypto.FORCED_MASK,
            box_size=1,
            border=4
        )
        qr.add_data(padded_unique_data)
        qr.make(fit=False)
        data_matrix = np.array(qr.get_matrix(), dtype=bool)
        
        # Sign the PADDED data combined with visual matrix
        try:
             signature = self.crypto.sign_data(padded_unique_data.encode('utf-8'), data_matrix)
        except ValueError as e:
             logger.error(f"Signing failed: {e}. Do you have a private key?")
             raise e
        
        barcode = DualAuthBarcode(padded_unique_data, signature)
        return (barcode, data_matrix, final_version, self.crypto.FORCED_ECLEVEL, self.crypto.FORCED_MASK)
    
    def generate_composite_barcode(self, barcode: DualAuthBarcode, data_matrix: np.ndarray, 
                                  output_path: str, forced_version: int, forced_eclevel: int, 
                                  forced_mask: int, scale: int = None) -> bool:
        """Generate composite grayscale barcode using different shades of black."""
        if scale is None:
            scale = self.crypto.DEFAULT_BARCODE_SCALE
            
        logger.info("Generating composite grayscale barcode...")
        try:
            # Generate the signature QR
            signature_base64 = base64.b64encode(barcode.signature).decode('ascii')
            sig_qr = qrcode.QRCode(
                version=forced_version,
                error_correction=forced_eclevel,
                mask_pattern=forced_mask,
                box_size=1,
                border=4
            )
            sig_qr.add_data(signature_base64)
            sig_qr.make(fit=False)
            sig_matrix = np.array(sig_qr.get_matrix(), dtype=bool)
            
            # Create the image canvas
            h, w = data_matrix.shape
            img = Image.new('L', (w * scale, h * scale), 255)
            draw = ImageDraw.Draw(img)
            
            # Iterate through each module and set the gray level
            for r in range(h):
                for c in range(w):
                    color = self.crypto.COMPOSITE_COLOR_MAP[(data_matrix[r, c], sig_matrix[r, c])]
                    top_left = (c * scale, r * scale)
                    bottom_right = ((c + 1) * scale, (r + 1) * scale)
                    draw.rectangle([top_left, bottom_right], fill=color)
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            img.save(output_path)
            logger.info(f"Saved composite barcode to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate composite barcode: {e}")
            return False

    # --- Verification Logic ---

    def verify_barcode(self, barcode: DualAuthBarcode, verbose: bool = True) -> bool:
        """
        Verify the HMAC using visually-derived key.
        Returns True if authentic, False otherwise.
        """
        public_data = barcode.public_data
        signature = barcode.signature
        
        if verbose:
            logger.info(f"Verifying barcode with public data length: {len(public_data)}")
        
        # Re-generate the QR matrix for the public data part EXACTLY
        version = get_qr_version(public_data, self.crypto.FORCED_ECLEVEL)
        
        qr = qrcode.QRCode(
            version=version,
            error_correction=self.crypto.FORCED_ECLEVEL,
            mask_pattern=self.crypto.FORCED_MASK,
            box_size=1,
            border=4
        )
        qr.add_data(public_data)
        qr.make(fit=False)
        data_matrix = np.array(qr.get_matrix(), dtype=bool)
        
        # Verify using Public Key
        is_authentic = self.crypto.verify_signature(signature, public_data.encode('utf-8'), data_matrix)
        
        if verbose:
            if is_authentic:
                logger.info("SUCCESS: Barcode is authentic.")
            else:
                logger.error("FAILURE: Barcode is NOT authentic. Signature verification failed.")
        
        return is_authentic
    
    def extract_secret_message(self, barcode: DualAuthBarcode) -> Optional[str]:
        """Extract the secret message from a verified barcode."""
        # Try JSON first
        try:
            # We need to strip trailing spaces used for padding before parsing JSON
            # However, json.loads might just ignore them if we are lucky, or fail.
            # Let's try direct parse. If it fails, strip.
            payload = json.loads(barcode.public_data.strip())
            return payload.get("s", "")
        except json.JSONDecodeError:
             logger.warning("Failed to parse barcode payload as JSON. Attempting fallback.")
             return None
