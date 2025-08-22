#!/usr/bin/env python3
"""
Basic usage example for SecuriQR.
Demonstrates how to generate and verify a dual-layer authenticated barcode.
"""

import os
import tempfile
from pathlib import Path

# Add the src directory to the Python path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from securiqr.core.generator import BarcodeGenerator
from securiqr.core.verifier import BarcodeVerifier
from securiqr.processing.decoder import BarcodeDecoder

def basic_usage_example():
    """Basic example of generating and verifying a SecuriQR barcode."""
    print("=== SecuriQR Basic Usage Example ===\n")
    
    # Create a temporary directory for output
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "composite_barcode.png"
    key_path = output_dir / "secret.key"
    
    # Initialize components
    generator = BarcodeGenerator(str(key_path))
    decoder = BarcodeDecoder()
    verifier = BarcodeVerifier(str(key_path))
    
    # Generate a barcode
    public_data = "Product ID: SKU-12345"
    secret_message = "This is a genuine product"
    
    print(f"Generating barcode for: {public_data}")
    print(f"With secret message: {secret_message}")
    
    barcode, data_matrix, version, eclevel, mask = generator.create_barcode(
        public_data, secret_message
    )
    
    # Save the composite barcode
    success = generator.generate_composite_barcode(
        barcode, data_matrix, str(output_path), version, eclevel, mask
    )
    
    if not success:
        print("Failed to generate barcode")
        return False
    
    print(f"Barcode saved to: {output_path}")
    print(f"Signature (hex): {barcode.signature.hex()}\n")
    
    # Decode the barcode
    print("Decoding the barcode...")
    result = decoder.read_composite_barcode(str(output_path))
    
    if not result:
        print("Failed to decode barcode")
        return False
    
    decoded_barcode, _ = result
    print(f"Decoded public data: {decoded_barcode.public_data}")
    
    # Verify the barcode
    print("\nVerifying the barcode...")
    is_authentic = verifier.verify_barcode(decoded_barcode)
    
    if is_authentic:
        print("✅ Barcode is AUTHENTIC")
        secret = verifier.extract_secret_message(decoded_barcode)
        print(f"Secret message: {secret}")
        return True
    else:
        print("❌ Barcode is NOT authentic")
        return False

if __name__ == "__main__":
    success = basic_usage_example()
    sys.exit(0 if success else 1)