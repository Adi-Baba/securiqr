import qrcode

def get_qr_version(data: str, error_correction) -> int:
    """Helper to determine the version of a QR code for given data."""
    qr = qrcode.QRCode(error_correction=error_correction)
    qr.add_data(data)
    qr.make(fit=True)
    return qr.version