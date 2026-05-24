# security.py
from cryptography.fernet import Fernet
import os
import config

KEY_FILE = "secret.key"

def generate_and_save_key():
    """Generates a new key and saves it to a file and the .env file."""
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as key_file:
        key_file.write(key)
    print(f"🔑 New encryption key generated and saved to {KEY_FILE}.")
    print("Please add this key to your .env file as ENCRYPTION_KEY for future use.")
    return key

def load_key():
    """Loads the encryption key from .env or generates a new one."""
    if config.ENCRYPTION_KEY:
        return config.ENCRYPTION_KEY.encode()
    
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as key_file:
            return key_file.read()
    else:
        return generate_and_save_key()

# Load the key on startup
_key = load_key()
_cipher_suite = Fernet(_key)

def encrypt_data(data: str) -> bytes:
    """Encrypts a string."""
    if not isinstance(data, str):
        raise TypeError("Data to encrypt must be a string.")
    return _cipher_suite.encrypt(data.encode('utf-8'))

def decrypt_data(encrypted_data: bytes) -> str:
    """Decrypts data and returns a string."""
    if not isinstance(encrypted_data, bytes):
        raise TypeError("Encrypted data must be bytes.")
    return _cipher_suite.decrypt(encrypted_data).decode('utf-8')