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

def check_signature(signature_bytes, message_hash):
    """Проверяет подпись сообщения (версия + хеш пакета)."""
    try:
        public_key.verify(
            signature_bytes, 
            message_hash, 
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), 
            utils.Prehashed(hashes.SHA256())
        )
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

    def verify(self, client_version):
        package_bytes, metadata = self.view.read()
    
        if not package_bytes or not metadata:
            return {"verdict": "fail", "reason": "пакет или метаданные не найдены"}
    
        try:
            package_version = metadata["package_version"]
            package_hash_str = metadata["package_hash"]["value"]
            signature_b64 = metadata["signature"]["value"]
        
            package_hash = hashlib.sha256(package_bytes).digest()
            if package_hash.hex() != package_hash_str:
                self.view.reject()
                return {"verdict": "fail", "reason": "неверная контрольная сумма пакета"}
        
            message = hashlib.sha256(package_version.encode() + b"\n" + package_hash).digest()
            signature = base64.b64decode(signature_b64)
        
            if not check_signature(signature, message):
                self.view.reject()
                return {"verdict": "fail", "reason": "неверная подпись"}
            
            # Если все проверки прошли, переводим состояние в VERIFIED
            self.view.approve()
            return {"verdict": "pass"}
        except Exception as e:
            self.view.reject()
            return {"verdict": "fail", "reason": str(e)}