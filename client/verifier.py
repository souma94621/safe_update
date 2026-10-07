from pathlib import Path
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding, utils
from cryptography.exceptions import InvalidSignature
import hashlib
import base64

with open(Path(__file__).parent.parent / "keys" / "client_public.pem", 'rb') as f: 
    key_bytes = f.read()

public_key = serialization.load_pem_public_key(key_bytes)

def checksum(package_bytes, package_hash):
    if hashlib.sha256(package_bytes).hexdigest() == package_hash:
        return True
    return False

def check_signature(package_bytes, signature):
    try:
        package_hash = hashlib.sha256(package_bytes).digest()
        de_signature = base64.b64decode(signature)
        public_key.verify(de_signature, package_hash, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), utils.Prehashed(hashes.SHA256()))

        return True
    except InvalidSignature:
        return False

def check_version(package_version, client_version):
    package_parts = [int(i) for i in package_version.split('.')]
    client_parts = [int(i) for i in client_version.split('.')]
    return package_parts > client_parts

class Verifier:
    def __init__(self, view):
        self.view = view

    def verify(self, current_version):
        package_bytes, metadata = self.view.read()

        checks = {
            "checksum": checksum(package_bytes, metadata["package_hash"]["value"]),
            "signature": check_signature(package_bytes, metadata["signature"]["value"]),
            "version": check_version(metadata["package_version"], current_version),
        }

        if all(checks.values()):
            self.view.approve()
            return {"verdict": "pass"}
        else:
            self.view.reject()
            return {"verdict": "fail", "reason": checks}

