#!/usr/bin/env python3
"""
Advanced usage example for SecuriQR.
Demonstrates batch processing, custom configuration, and error handling.
"""

import os
import tempfile
import logging
from pathlib import Path
from typing import List, Dict, Any

# Add the src directory to the Python path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from securiqr.core.generator import BarcodeGenerator
from securiqr.core.verifier import BarcodeVerifier
from securiqr.processing.decoder import BarcodeDecoder
from securiqr.processing.image_processor import ImageProcessor

def setup_logging(verbose: bool = False):
    """Configure logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("securiqr_advanced.log"),
            logging.StreamHandler()
        ]
    )

class SecuriQRBatchProcessor:
    """Batch processor for generating and verifying multiple SecuriQR barcodes."""
    
    def __init__(self, output_dir: str, key_path: str):
        self.output_dir = Path(output_dir)
        self.key_path = key_path
        self.generator = BarcodeGenerator(key_path)
        self.decoder = BarcodeDecoder()
        self.verifier = BarcodeVerifier(key_path)
        self.processor = ImageProcessor()
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_batch(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate barcodes for a batch of products."""
        results = []
        
        for product in products:
            try:
                product_id = product['id']
                public_data = f"Product: {product_id}"
                secret_message = product.get('secret', f"Authentic {product_id}")
                
                # Generate barcode
                barcode, data_matrix, version, eclevel, mask = self.generator.create_barcode(
                    public_data, secret_message
                )
                
                # Save barcode
                output_path = self.output_dir / f"{product_id}_barcode.png"
                success = self.generator.generate_composite_barcode(
                    barcode, data_matrix, str(output_path), version, eclevel, mask
                )
                
                if success:
                    results.append({
                        'product_id': product_id,
                        'status': 'success',
                        'output_path': str(output_path),
                        'signature': barcode.signature.hex()
                    })
                    logging.info(f"Generated barcode for {product_id}")
                else:
                    results.append({
                        'product_id': product_id,
                        'status': 'error',
                        'error': 'Failed to generate barcode image'
                    })
                    logging.error(f"Failed to generate barcode for {product_id}")
                    
            except Exception as e:
                results.append({
                    'product_id': product.get('id', 'unknown'),
                    'status': 'error',
                    'error': str(e)
                })
                logging.error(f"Error generating barcode: {e}")
        
        return results
    
    def verify_batch(self, image_paths: List[str]) -> List[Dict[str, Any]]:
        """Verify a batch of barcode images."""
        results = []
        
        for image_path in image_paths:
            try:
                # Determine if it's a standard or composite barcode
                is_composite = self.processor.is_grayscale_or_color(image_path)
                
                if is_composite is None:
                    results.append({
                        'image_path': image_path,
                        'status': 'error',
                        'error': 'Could not analyze image'
                    })
                    continue
                
                if is_composite:
                    # Decode composite barcode
                    result = self.decoder.read_composite_barcode(image_path)
                    
                    if not result:
                        results.append({
                            'image_path': image_path,
                            'status': 'error',
                            'error': 'Failed to decode composite barcode'
                        })
                        continue
                    
                    barcode, _ = result
                    
                    # Verify the barcode
                    is_authentic = self.verifier.verify_barcode(barcode, verbose=False)
                    
                    if is_authentic:
                        secret = self.verifier.extract_secret_message(barcode)
                        results.append({
                            'image_path': image_path,
                            'status': 'authentic',
                            'public_data': barcode.public_data,
                            'secret_message': secret
                        })
                    else:
                        results.append({
                            'image_path': image_path,
                            'status': 'counterfeit',
                            'public_data': barcode.public_data
                        })
                else:
                    # Process standard barcode
                    standard_results = self.processor.read_standard_barcodes(image_path)
                    
                    if standard_results:
                        for obj in standard_results:
                            results.append({
                                'image_path': image_path,
                                'status': 'standard',
                                'type': obj.type,
                                'data': obj.data.decode('utf-8')
                            })
                    else:
                        results.append({
                            'image_path': image_path,
                            'status': 'error',
                            'error': 'No standard barcode found'
                        })
                        
            except Exception as e:
                results.append({
                    'image_path': image_path,
                    'status': 'error',
                    'error': str(e)
                })
                logging.error(f"Error processing {image_path}: {e}")
        
        return results

def advanced_usage_example():
    """Advanced example demonstrating batch processing and custom configuration."""
    print("=== SecuriQR Advanced Usage Example ===\n")
    
    # Set up detailed logging
    setup_logging(verbose=True)
    
    # Create a temporary directory for output
    output_base_dir = Path(__file__).parent / "advanced_output"
    output_base_dir.mkdir(parents=True, exist_ok=True)
    key_path = output_base_dir / "batch_secret.key"
    
    # Initialize batch processor
    processor = SecuriQRBatchProcessor(str(output_base_dir / "output"), str(key_path))
        
    # Define products to process
    products = [
        {'id': 'SKU-1001', 'secret': 'Genuine product from factory A'},
        {'id': 'SKU-1002', 'secret': 'Batch 2023-05, verified'},
        {'id': 'SKU-1003'},  # No secret message
    ]
    
    print("1. Generating batch of barcodes...")
    generation_results = processor.generate_batch(products)
    
    print("\nGeneration Results:")
    for result in generation_results:
        print(f"  {result['product_id']}: {result['status']}")
        if result['status'] == 'success':
            print(f"    Signature: {result['signature'][:16]}...")
    
    # Get paths of generated barcodes
    generated_paths = [
        result['output_path'] for result in generation_results 
        if result['status'] == 'success'
    ]
    
    if not generated_paths:
        print("No barcodes were successfully generated")
        return False
    
    print(f"\n2. Verifying {len(generated_paths)} barcodes...")
    verification_results = processor.verify_batch(generated_paths)
    
    print("\nVerification Results:")
    authentic_count = 0
    for result in verification_results:
        print(f"  {Path(result['image_path']).name}: {result['status']}")
        if result['status'] == 'authentic':
            authentic_count += 1
            print(f"    Secret: {result.get('secret_message', 'None')}")
    
    print(f"\nSummary: {authentic_count}/{len(generated_paths)} barcodes authentic")
    
    return authentic_count == len(generated_paths)

if __name__ == "__main__":
    success = advanced_usage_example()
    sys.exit(0 if success else 1)