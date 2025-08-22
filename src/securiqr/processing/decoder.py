import base64
import logging
from typing import Optional, Tuple

import numpy as np
from PIL import Image
from pyzbar import pyzbar
from sklearn.cluster import KMeans

from ..utils.types import DualAuthBarcode

logger = logging.getLogger(__name__)

class BarcodeDecoder:
    """Decodes dual-layer barcodes from images"""
    
    DEFAULT_BARCODE_SCALE = 10
    
    def __init__(self, scale: int = None):
        self.scale = scale or self.DEFAULT_BARCODE_SCALE
    
    def _decode_matrix(self, matrix: np.ndarray) -> Optional[str]:
        """Helper function to decode a boolean matrix by converting it to a scaled image."""
        img_array = np.uint8(~matrix) * 255
        img = Image.fromarray(img_array, 'L')
        
        if self.scale > 1:
            img = img.resize((img.width * self.scale, img.height * self.scale), Image.NEAREST)
        
        decoded_objects = pyzbar.decode(img)
        if decoded_objects:
            return decoded_objects[0].data.decode('utf-8')
        return None
    
    def _find_and_sort_color_centers(self, img: Image.Image, n_clusters: int = 4) -> Optional[np.ndarray]:
        """Dynamically finds the N grayscale color centers in the image using K-Means clustering."""
        w, h = img.size
        out_w, out_h = w // self.scale, h // self.scale
        
        # Collect a sample of median gray values from the modules
        pixel_samples = []
        for r in range(0, out_h, 2):
            for c in range(0, out_w, 2):
                r_start, r_end = r * self.scale, (r + 1) * self.scale
                c_start, c_end = c * self.scale, (c + 1) * self.scale
                module_img = img.crop((c_start, r_start, c_end, r_end))
                median_gray = np.median(np.array(module_img))
                pixel_samples.append([median_gray])
        
        if len(pixel_samples) < n_clusters:
            logger.error("Not enough pixel samples to perform clustering.")
            return None
        
        # Use K-Means to find the 4 color centers
        kmeans = KMeans(n_clusters=n_clusters, random_state=0, n_init='auto').fit(pixel_samples)
        centers = kmeans.cluster_centers_.flatten()
        
        # Sort the centers from darkest (0) to brightest (255)
        centers.sort()
        
        if len(centers) != n_clusters:
            logger.error(f"K-Means failed to find {n_clusters} distinct color centers.")
            return None
            
        logger.info(f"Dynamically found color centers: {[int(c) for c in centers]}")
        return centers
    
    def read_composite_barcode(self, image_path: str) -> Optional[Tuple[DualAuthBarcode, np.ndarray]]:
        """Rebuild the two boolean matrices from the composite grayscale image and decode them."""
        logger.info(f"Reading composite barcode from: {image_path}")
        try:
            img = Image.open(image_path).convert('L')
            
            color_centers = self._find_and_sort_color_centers(img)
            if color_centers is None:
                logger.error("Failed to determine color centers from the image.")
                return None
            
            black_center, dark_gray_center, light_gray_center, white_center = color_centers
            
            w, h = img.size
            out_w, out_h = w // self.scale, h // self.scale
            
            data_matrix = np.zeros((out_h, out_w), dtype=bool)
            sig_matrix = np.zeros((out_h, out_w), dtype=bool)
            
            for r in range(out_h):
                for c in range(out_w):
                    r_start, r_end = r * self.scale, (r + 1) * self.scale
                    c_start, c_end = c * self.scale, (c + 1) * self.scale
                    module_img = img.crop((c_start, r_start, c_end, r_end))
                    pixel_gray_level = np.median(np.array(module_img))
                    
                    # Classify the pixel by finding the closest color center
                    distances = np.abs(color_centers - pixel_gray_level)
                    closest_center_idx = np.argmin(distances)
                    
                    data_matrix[r, c] = (closest_center_idx == 0 or closest_center_idx == 2)
                    sig_matrix[r, c] = (closest_center_idx == 0 or closest_center_idx == 1)
            
            public_data = self._decode_matrix(data_matrix)
            signature_base64 = self._decode_matrix(sig_matrix)
            
            if not public_data or not signature_base64:
                logger.error("Failed to decode one or both layers from the reconstructed matrices.")
                return None
            
            barcode = DualAuthBarcode(public_data, base64.b64decode(signature_base64))
            return (barcode, data_matrix)
            
        except FileNotFoundError:
            logger.error(f"Image file not found at path: {image_path}")
            return None
        except ImportError:
            logger.error("A required library (e.g., scikit-learn) is not installed.")
            return None
        except Exception as e:
            logger.exception(f"An unexpected error occurred while processing {image_path}")
            return None