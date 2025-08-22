import os

HMAC_KEY_SIZE_BYTES = 32

def load_or_generate_secret_key(path: str) -> bytes:
    """Loads a secret key from a file or generates a new one if not found."""
    if os.path.exists(path):
        print(f"Loading existing secret key from '{path}'...")
        with open(path, 'rb') as f:
            return f.read()
    else:
        print(f"Generating new secret key and saving to '{path}'...")
        key = os.urandom(HMAC_KEY_SIZE_BYTES)
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path, 'wb') as f:
            f.write(key)
        return key