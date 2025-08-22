import os
import argparse
import logging
from ..core.generator import BarcodeGenerator

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
    generator = BarcodeGenerator(args.key)
    barcode, data_matrix, version, eclevel, mask = generator.create_barcode(
        args.public_data, args.secret
    )
    
    # Save the composite barcode
    output_path = os.path.join(args.output, "composite_barcode.png")
    success = generator.generate_composite_barcode(
        barcode, data_matrix, output_path, version, eclevel, mask
    )
    
    if success:
        print(f"Successfully generated SecuriQR barcode at: {output_path}")
        print(f"Signature (hex): {barcode.signature.hex()}")
    else:
        print("Failed to generate barcode")
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main())