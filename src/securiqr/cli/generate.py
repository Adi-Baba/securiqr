import os
import argparse
import logging
from ..core.engine import SecuriQREngine

def main():
    """Command-line interface for generating SecuriQR barcodes."""
    parser = argparse.ArgumentParser(description="Generate a SecuriQR dual-layer authenticated barcode")
    parser.add_argument("public_data", help="The public data to encode in the barcode")
    parser.add_argument("-s", "--secret", help="Secret message to embed", default="")
    parser.add_argument("-o", "--output", help="Output directory", default="./output")
    parser.add_argument("-k", "--key", help="Path to secret key file")
    parser.add_argument("-v", "--verbose", help="Increase output verbosity", action="store_true")
    
    args = parser.parse_args()
    
    # Set up logging
    logging_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=logging_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Generate the barcode
    try:
        engine = SecuriQREngine(args.key)
        barcode, data_matrix, version, eclevel, mask = engine.create_barcode(
            args.public_data, args.secret
        )
    except FileNotFoundError:
        print(f"Error: Private key file not found at '{args.key}'.")
        print("Please generate keys first using: from securiqr.core.crypto import CryptoManager; CryptoManager().generate_key_pair('keys')")
        return 1
    except ValueError as e:
        print(f"Error: {e}") 
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1

    # Save the composite barcode
    output_path = os.path.join(args.output, "composite_barcode.png")
    try:
        success = engine.generate_composite_barcode(
            barcode, data_matrix, output_path, version, eclevel, mask
        )
    except OSError as e:
        print(f"Error saving file to '{output_path}': {e}")
        return 1
    except PermissionError:
        print(f"Error: Permission denied when trying to save to '{output_path}'. Check directory permissions.")
        return 1
    
    if success:
        print(f"Successfully generated SecuriQR barcode at: {output_path}")
        print(f"Signature (hex): {barcode.signature.hex()}")
    else:
        print("Failed to generate barcode")
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main())