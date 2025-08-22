import logging
from typing import List, Optional

from PIL import Image
from pyzbar import pyzbar

logger = logging.getLogger(__name__)

class ImageProcessor:
    """Processes images for barcode detection and analysis"""
    
    @staticmethod
    def is_grayscale_or_color(image_path: str) -> Optional[bool]:
        """Check if an image is grayscale/color or black and white."""
        try:
            img = Image.open(image_path)
            colors = img.getcolors(maxcolors=256)
            return colors is not None and len(colors) > 2
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return None
    
    @staticmethod
    def read_standard_barcodes(image_path: str) -> Optional[List]:
        """Reads any standard barcodes from an image file."""
        try:
            img = Image.open(image_path)
            decoded_objects = pyzbar.decode(img)
            return decoded_objects if decoded_objects else None
        except Exception as e:
            logger.error(f"Error reading standard barcodes: {e}")
            return None