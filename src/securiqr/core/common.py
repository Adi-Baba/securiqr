import os
from dataclasses import dataclass
import qrcode
import logging

# --- Types ---

@dataclass
class DualAuthBarcode:
    """A simple dataclass to hold the barcode data."""
    public_data: str  # includes UUID
    signature: bytes  # HMAC bytes

# --- QR Utils ---

def get_qr_version(data: str, error_correction) -> int:
    """Helper to determine the version of a QR code for given data."""
    qr = qrcode.QRCode(error_correction=error_correction)
    qr.add_data(data)
    qr.make(fit=True)
    return qr.version

# --- Key Manager ---

HMAC_KEY_SIZE_BYTES = 32
logger = logging.getLogger(__name__)

def load_or_generate_secret_key(path: str) -> bytes:
    """Loads a secret key from a file or generates a new one if not found."""
    if os.path.exists(path):
        logger.info(f"Loading existing secret key from '{path}'...")
        with open(path, 'rb') as f:
            return f.read()
    else:
        logger.info(f"Generating new secret key and saving to '{path}'...")
        key = os.urandom(HMAC_KEY_SIZE_BYTES)
        try:
            os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
            with open(path, 'wb') as f:
                f.write(key)
        except Exception as e:
            logger.error(f"Failed to save secret key: {e}")
            # If we can't save, we should honestly crash or return the key transiently
            # For now, let's return the key but log the error
        return key
