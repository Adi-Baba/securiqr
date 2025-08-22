import sys
import os
import argparse
import logging
from ..processing.image_processor import ImageProcessor
from ..processing.decoder import BarcodeDecoder
from ..core.verifier import BarcodeVerifier
from ..utils.key_manager import load_or_generate_secret_key

def main():
    """Universal reader for both standard and SecuriQR barcodes."""
    parser = argparse.ArgumentParser(description="Universal reader for standard and SecuriQR barcodes")
    parser.add_argument("image_path", help="Path to the barcode image to read")
    parser.add_argument("-k", "--key", help="Path to secret key file")
    parser.add_argument("-v", "--verbose", help="Increase output verbosity", action="store_true")
    
    args = parser.parse_args()
    
    # Set up logging
    logging_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=logging_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Determine barcode type
    processor = ImageProcessor()
    is_composite = processor.is_grayscale_or_color(args.image_path)
    
    if is_composite is None:
        print("Error analyzing image")
        return 1
        
    if is_composite:
        # This is likely a composite barcode
        print("Detected composite barcode. Attempting to decode...")
        decoder = BarcodeDecoder()
        result = decoder.read_composite_barcode(args.image_path)
        
        if not result:
            print("Failed to decode composite barcode")
            return 1
            
        barcode, _ = result
        
        # Verify the barcode if we have a key
        key_path = args.key or os.path.join(os.path.dirname(__file__), "..", "..", "config", "manufacturer_secret.key")
        if os.path.exists(key_path):
            verifier = BarcodeVerifier(key_path)
            is_authentic = verifier.verify_barcode(barcode, args.verbose)
            
            if is_authentic:
                print("✅ Secure Barcode AUTHENTICATED")
                secret_message = verifier.extract_secret_message(barcode)
                print(f"Public Data: {barcode.public_data}")
                if secret_message:
                    print(f"Secret Message: {secret_message}")
            else:
                print("❌ Barcode is NOT authentic")
                return 1
        else:
            print("⚠️  No verification key found. Displaying unverified data:")
            print(f"Public Data: {barcode.public_data}")
            
    else:
        # Standard barcode
        print("Detected standard barcode. Attempting to decode...")
        results = processor.read_standard_barcodes(args.image_path)
        
        if results:
            print("✅ Standard Barcode Detected")
            for obj in results:
                print(f"Type: {obj.type}")
                print(f"Data: {obj.data.decode('utf-8')}")
        else:
            print("❌ No standard barcode found")
            return 1
            
    return 0

if __name__ == "__main__":
    exit(main())