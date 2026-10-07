from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import registry
import crypto
import base64

app = FastAPI()

class VersionCheckRequest(BaseModel):
    client_version : str

@app.post("/version_check")
def version_check(req: VersionCheckRequest):
    update_available, latest = registry.has_update(req.client_version)
    if not update_available:
        return {"available": False}

    path = registry.version_path(latest)
    with open(path, 'rb') as f:
        package_bytes = f.read()

    package_hash_hex, signature = crypto.sign_package(package_bytes)

    return {
        "available": True,
        "package_version": latest,
        "package_hash": {"algorithm" : "sha256", "value" : package_hash_hex},
        "signature" : {"algorithm" : "rsa-pss-sha256", "value" : base64.b64encode(signature).decode()},
        "package_size_bytes" : len(package_bytes)
    }

@app.get("/package/{version}")
def package(version : str):
    path = registry.version_path(version)

    if path is None:
        raise HTTPException(status_code=404, detail="сообщение об ошибке")

    return FileResponse(path, filename=version)