from dataclasses import dataclass

@dataclass
class DualAuthBarcode:
    """A simple dataclass to hold the barcode data."""
    public_data: str  # includes UUID
    signature: bytes  # HMAC bytes