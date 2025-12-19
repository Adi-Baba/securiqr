import unittest
import os
import shutil
import json
import numpy as np
import qrcode
from securiqr.core.common import load_or_generate_secret_key, get_qr_version
from securiqr.core.crypto import CryptoManager
from securiqr.core.engine import SecuriQREngine
from securiqr.processing.decoder import BarcodeDecoder

# --- Test Common Utilities ---
class TestCommon(unittest.TestCase):
    def test_qr_version(self):
        v1 = get_qr_version("Short data", qrcode.constants.ERROR_CORRECT_M)
        self.assertEqual(v1, 1)

# --- Test Crypto (Asymmetric) ---
class TestCrypto(unittest.TestCase):
    def setUp(self):
        self.test_keys_dir = "test_keys"
        self.crypto = CryptoManager()
        # Ensure we have keys
        if os.path.exists(self.test_keys_dir):
            shutil.rmtree(self.test_keys_dir)
        self.crypto.generate_key_pair(self.test_keys_dir)
        
    def tearDown(self):
        if os.path.exists(self.test_keys_dir):
            shutil.rmtree(self.test_keys_dir)

    def test_sign_verify(self):
        """Test ECDSA Signing and Verification."""
        data = b"Hello World"
        # Mock visual matrix (random boolean array)
        matrix = np.random.choice([True, False], size=(21, 21))
        
        # Sign
        signature = self.crypto.sign_data(data, matrix)
        self.assertTrue(len(signature) > 0)
        
        # Verify
        is_valid = self.crypto.verify_signature(signature, data, matrix)
        self.assertTrue(is_valid)
        
        # Tamper Data
        is_valid_tampered = self.crypto.verify_signature(signature, b"Hello World!", matrix)
        self.assertFalse(is_valid_tampered)
        
        # Tamper Matrix
        matrix[0,0] = not matrix[0,0]
        is_valid_tampered_matrix = self.crypto.verify_signature(signature, data, matrix)
        self.assertFalse(is_valid_tampered_matrix)

# --- Test Engine (Full Cycle) ---
class TestEngine(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_engine_keys"
        os.makedirs(self.test_dir, exist_ok=True)
        
        # We need to explicitly generate keys first because the Engine needs them
        # CryptoManager automatically looks for keys or fails if not found during sign
        # So we manually use a CryptoManager to setup keys
        cm = CryptoManager()
        cm.generate_key_pair(self.test_dir)
        
        # Initialize engine pointing to the Private Key (for generation)
        self.engine_gen = SecuriQREngine(key_path=os.path.join(self.test_dir, "private.pem"))
        # Initialize engine pointing to the Public Key (for verification verification)
        self.engine_ver = SecuriQREngine(key_path=os.path.join(self.test_dir, "public.pem"))

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_full_cycle(self):
        public_data = "Product-123"
        secret = "MySecret"
        
        # Generate (Uses Private Key)
        barcode, mat, v, ec, mask = self.engine_gen.create_barcode(public_data, secret)
        
        # Verify (Uses Public Key)
        is_valid = self.engine_ver.verify_barcode(barcode, verbose=False)
        self.assertTrue(is_valid)
        
        # Extract secret
        extracted = self.engine_ver.extract_secret_message(barcode)
        self.assertEqual(extracted, secret)

    def test_tamper_detection(self):
        barcode, _, _, _, _ = self.engine_gen.create_barcode("Original", "Secret")
        
        # Tamper Payload
        payload = json.loads(barcode.public_data)
        payload['d'] = "Tampered"
        barcode.public_data = json.dumps(payload, separators=(',', ':'))
        
        is_valid = self.engine_ver.verify_barcode(barcode, verbose=False)
        self.assertFalse(is_valid)

# --- Test Decoder (K-Means) ---
class TestDecoder(unittest.TestCase):
    def test_kmeans_logic(self):
        decoder = BarcodeDecoder()
        data = np.array([10, 12, 11, 200, 205, 202])
        # Simple clustering check
        centers = decoder._simple_1d_kmeans(data.reshape(-1, 1), k=2)
        centers.sort()
        # Should find centers near ~11 and ~202
        self.assertTrue(10 <= centers[0] <= 12)
        self.assertTrue(200 <= centers[1] <= 205)

if __name__ == '__main__':
    unittest.main()
