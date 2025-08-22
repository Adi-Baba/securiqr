import os
import uuid
import base64
import logging
import hmac
import hashlib
from typing import Tuple, Optional

import numpy as np
import qrcode
from PIL import Image, ImageDraw

from .crypto import CryptoManager
from ..utils.types import DualAuthBarcode

logger = logging.getLogger(__name__)

class BarcodeGenerator(CryptoManager):
    """Generates dual-layer authenticated barcodes"""
    
    def create_barcode(self, public_data: str, secret_message: str = "") -> Tuple[DualAuthBarcode, np.ndarray, int, int, int]:
        """
        Create a signed barcode for `public_data` with optional secret message.
        Returns (DualAuthBarcode, data_matrix, version, eclevel, mask).
        """
        padded_unique_data = f"{public_data}|secret:{secret_message}|uuid:{uuid.uuid4()}"
        logger.info(f"Creating barcode for data: {public_data}")
        
        # Determine final QR version to hold both data and signature
        temp_sig_base64 = base64.b64encode(os.urandom(32)).decode('ascii')
        
        data_version = self._get_qr_version(padded_unique_data, self.FORCED_ECLEVEL)
        sig_version = self._get_qr_version(temp_sig_base64, self.FORCED_ECLEVEL)
        final_version = max(data_version, sig_version)
        
        # Pad the data string with spaces if necessary
        while self._get_qr_version(padded_unique_data, self.FORCED_ECLEVEL) < final_version:
            padded_unique_data += " "
        
        # Build final QR for the public data
        qr = qrcode.QRCode(
            version=final_version,
            error_correction=self.FORCED_ECLEVEL,
            mask_pattern=self.FORCED_MASK,
            box_size=1,
            border=4
        )
        qr.add_data(padded_unique_data)
        qr.make(fit=False)
        data_matrix = np.array(qr.get_matrix(), dtype=bool)
        
        # Sign the PADDED data with the visually-derived key
        session_key = self.derive_visual_key(self.master_key, data_matrix)
        signature = hmac.new(session_key, padded_unique_data.encode('utf-8'), hashlib.sha256).digest()
        
        barcode = DualAuthBarcode(padded_unique_data, signature)
        return (barcode, data_matrix, final_version, self.FORCED_ECLEVEL, self.FORCED_MASK)
    
    def generate_composite_barcode(self, barcode: DualAuthBarcode, data_matrix: np.ndarray, 
                                  output_path: str, forced_version: int, forced_eclevel: int, 
                                  forced_mask: int, scale: int = None) -> bool:
        """Generate composite grayscale barcode using different shades of black."""
        if scale is None:
            scale = self.DEFAULT_BARCODE_SCALE
            
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
                    color = self.COMPOSITE_COLOR_MAP[(data_matrix[r, c], sig_matrix[r, c])]
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
    
    def generate_standard_qr(self, text: str, output_path: str, scale: int = None) -> bool:
        """Generate a standard QR code from text."""
        if scale is None:
            scale = self.DEFAULT_BARCODE_SCALE
            
        logger.info(f"Generating standard QR code for text: {text}")
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=scale,
                border=4
            )
            qr.add_data(text)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(output_path)
            
            logger.info(f"Saved standard QR code to: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to generate standard QR code: {e}")
            return False