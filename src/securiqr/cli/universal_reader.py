import sys
import os
import argparse
import logging
from ..processing.decoder import BarcodeDecoder
from ..core.engine import SecuriQREngine

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
    # Use static methods from BarcodeDecoder
    is_composite = BarcodeDecoder.is_grayscale_or_color(args.image_path)
    
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
        # Engine handles default key path if None is passed, but here we can iterate
        engine = SecuriQREngine(args.key)
        # We can try verification if key exists
        # Since engine init creates a key if missing (which is weird for a reader),
        # we might want to be careful. But keeping logic similar to before:
        
        is_authentic = engine.verify_barcode(barcode, args.verbose)
        
        if is_authentic:
            print("✅ Secure Barcode AUTHENTICATED")
            secret_message = engine.extract_secret_message(barcode)
            print(f"Public Data: {barcode.public_data}")
            if secret_message:
                print(f"Secret Message: {secret_message}")
        else:
            print("❌ Barcode is NOT authentic (or key mismatch)")
            print(f"Public Data: {barcode.public_data}")

    else:
        # Standard barcode
        print("Detected standard barcode. Attempting to decode...")
        results = BarcodeDecoder.read_standard_barcodes(args.image_path)
        
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