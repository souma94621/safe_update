import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "client"))

from main import build_system, reset_temp_storage

app = FastAPI()

_manager, _monitor, _temp_storage = build_system()

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    return (Path(__file__).parent / "templates" / "index.html").read_text(encoding="utf-8")


@app.post("/api/check")
def check():
    reset_temp_storage(_temp_storage)
    log_before = len(_monitor.log)
    result = _manager.run()
    new_entries = _monitor.log[log_before:]
    return {"result": result, "new_log": new_entries, "total_log": _monitor.log}

@app.post("/api/rollback")
def rollback():
    reset_temp_storage(_temp_storage)
    log_before = len(_monitor.log)
    try:
        result = _manager.installer.rollback()
        _manager.current_version = result["version"]
    except Exception as e:
        result = {"status": "rollback_failed", "error": str(e)}
    new_entries = _monitor.log[log_before:]
    return {"result": result, "new_log": new_entries, "total_log": _monitor.log}

@app.get("/api/monitor_log")
def monitor_log():
    return {"log": _monitor.log}

@app.get("/api/version")
def current_version():
    return {"version": _manager.installer.data_storage.get_active_version()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)