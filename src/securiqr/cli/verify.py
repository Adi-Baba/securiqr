import argparse
import logging
from ..processing.decoder import BarcodeDecoder
from ..core.engine import SecuriQREngine

def main():
    """Command-line interface for verifying SecuriQR barcodes."""
    parser = argparse.ArgumentParser(description="Verify a SecuriQR dual-layer authenticated barcode")
    parser.add_argument("image_path", help="Path to the barcode image to verify")
    parser.add_argument("-k", "--key", help="Path to secret key file")
    parser.add_argument("-v", "--verbose", help="Increase output verbosity", action="store_true")
    
    args = parser.parse_args()
    
    # Set up logging
    logging_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=logging_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Decode the barcode
    decoder = BarcodeDecoder()
    result = decoder.read_composite_barcode(args.image_path)
    
    if not result:
        print("Failed to decode barcode")
        return 1
        
    barcode, _ = result
    
    # Verify the barcode
    try:
        engine = SecuriQREngine(args.key)
        is_authentic = engine.verify_barcode(barcode, args.verbose)
    except FileNotFoundError:
        print(f"Error: Public key file not found at '{args.key}'.")
        return 1
    except ValueError as e:
        print(f"Error: {e}. Ensure you are using the correct Public Key.")
        return 1
    except Exception as e:
        print(f"Unexpected error during verification: {e}")
        return 1
    
    if is_authentic:
        print("✅ Barcode is AUTHENTIC")
        secret_message = engine.extract_secret_message(barcode)
        if secret_message:
            print(f"Secret message: {secret_message}")
    else:
        print("❌ Barcode is NOT authentic")
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main())