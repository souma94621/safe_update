import hashlib
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import utils
from pathlib import Path

with open(Path(__file__).parent.parent / "keys" / "server_private.pem", 'rb') as f: 
    key_bytes = f.read()

private_key = serialization.load_pem_private_key(key_bytes, password=None)

def sign_package(package_bytes, version):
    package_hash = hashlib.sha256(package_bytes).digest()
    message = hashlib.sha256(version.encode() + b"\n" + package_hash).digest()
    signature = private_key.sign(message, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), utils.Prehashed(hashes.SHA256()))
    return package_hash.hex(), signature 
