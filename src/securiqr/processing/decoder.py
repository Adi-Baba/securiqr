import base64
import logging
import json
from typing import Optional, Tuple, List

import numpy as np
from PIL import Image
from PIL import Image

from ..core.common import DualAuthBarcode

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
        
        try:
            from pyzbar import pyzbar
            decoded_objects = pyzbar.decode(img)
            if decoded_objects:
                return decoded_objects[0].data.decode('utf-8')
        except ImportError:
            logger.error("Could not import pyzbar. Is the 'zbar' shared library installed?")
            logger.error("See README.md for OS-specific installation instructions.")
        except Exception as e:
            # pyzbar can throw confusing errors if DLLs are missing on Windows
            if "Could not find module" in str(e) or "DLL load failed" in str(e):
                 logger.error("Failed to load zbar shared library.")
                 logger.error("On Windows, you may need the Visual C++ Redistributable.")
                 logger.error("On Linux/macOS, ensure 'libzbar0' or 'zbar' is installed.")
            else:
                 logger.warning(f"Decoding failed: {e}")
        
        return None
    
    def _simple_1d_kmeans(self, values: np.ndarray, k: int = 4, max_iter: int = 10) -> np.ndarray:
        """Lightweight 1D K-Means using NumPy."""
        if len(values) < k:
            return np.array(sorted(values))
            
        # Initialize centers linearly spread across the range
        min_val, max_val = np.min(values), np.max(values)
        centers = np.linspace(min_val, max_val, k)
        
        for _ in range(max_iter):
            # Assign points to nearest center
            distances = np.abs(values - centers)
            labels = np.argmin(distances, axis=1)
            
            new_centers = []
            for i in range(k):
                cluster_points = values[labels == i]
                if len(cluster_points) > 0:
                    new_centers.append(np.mean(cluster_points))
                else:
                    new_centers.append(centers[i])
            
            new_centers = np.array(new_centers)
            if np.allclose(centers, new_centers, atol=1.0):
                break
            centers = new_centers
            
        return centers

    def _find_and_sort_color_centers(self, img: Image.Image, n_clusters: int = 4) -> Optional[np.ndarray]:
        """Dynamically finds the N grayscale color centers in the image using custom K-Means."""
        w, h = img.size
        # Protect against zero division if scaling is weird, though unlikely
        if self.scale <= 0: return None

        out_w, out_h = w // self.scale, h // self.scale
        
        # Collect a sample of median gray values from the modules
        pixel_samples = []
        for r in range(0, out_h, 2):
            for c in range(0, out_w, 2):
                r_start, r_end = r * self.scale, (r + 1) * self.scale
                c_start, c_end = c * self.scale, (c + 1) * self.scale
                
                # Bounds check
                if c_end > w or r_end > h: continue
                
                module_img = img.crop((c_start, r_start, c_end, r_end))
                # Ensure module_img is not empty
                if module_img.size[0] == 0 or module_img.size[1] == 0: continue
                
                median_gray = np.median(np.array(module_img))
                pixel_samples.append(median_gray)
        
        if len(pixel_samples) < n_clusters:
            logger.error("Not enough pixel samples to perform clustering.")
            return None
            
        samples_array = np.array(pixel_samples).reshape(-1, 1)
        
        # Use custom K-Means to find the 4 color centers
        centers = self._simple_1d_kmeans(samples_array, k=n_clusters)
        centers = centers.flatten()
        centers.sort()
        
        if len(centers) != n_clusters:
            logger.warning(f"K-Means returned {len(centers)} clusters, expected {n_clusters}.")
            
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
            
            # If we got fewer than 4 centers, we can't reliably separate layers
            if len(color_centers) < 4:
                 logger.error("Insufficient color separation.")
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
                    
                    if c_end > w or r_end > h: continue

                    module_img = img.crop((c_start, r_start, c_end, r_end))
                    pixel_gray_level = np.median(np.array(module_img))
                    
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
        except Exception as e:
            logger.exception(f"An unexpected error occurred while processing {image_path}")
            return None
            
    # --- Methods absorbed from ImageProcessor ---
    
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
            from pyzbar import pyzbar
            img = Image.open(image_path)
            decoded_objects = pyzbar.decode(img)
            return decoded_objects if decoded_objects else None
        except ImportError:
             logger.error("Could not import pyzbar. Is the 'zbar' shared library installed?")
             return None
        except Exception as e:
            logger.error(f"Error reading standard barcodes: {e}")
            return None