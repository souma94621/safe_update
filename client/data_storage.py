from pathlib import Path
import json

DATA_DIR = Path(__file__).parent.parent / "storage" / "data"
ACTIVE_FILE = DATA_DIR / "active_slot.json"
SLOT_A = DATA_DIR / "slot_a"
SLOT_B = DATA_DIR / "slot_b"

class RollbackUnavailableError(Exception):
    pass

class DataStorage:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        SLOT_A.mkdir(exist_ok=True)
        SLOT_B.mkdir(exist_ok=True)
        if not ACTIVE_FILE.exists():
            self._write_meta({
                "active_slot": "a",
                "slots": {
                    "a": {"version": None, "installed_at": None},
                    "b": {"version": None, "installed_at": None},
                },
            })

    def _read_meta(self):
        with open(ACTIVE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _write_meta(self, meta):
        with open(ACTIVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(meta, f)

    def _inactive_slot(self, meta):
        
        if meta["active_slot"] == "a":
            return "b" 
        else:
            return "a"

    def _slot_path(self, slot):
        if slot == "a":
            return SLOT_A
        else:
            return SLOT_B
    
    def get_active_version(self):
        meta = self._read_meta()
        return meta["slots"][meta["active_slot"]]["version"]

    def write_and_activate(self, package_bytes, metadata):
        meta = self._read_meta()
        inactive = self._inactive_slot(meta)
        slot_dir = self._slot_path(inactive)

        for old_file in slot_dir.iterdir():
            if old_file.is_file():
                old_file.unlink()
    
        meta["slots"][inactive] = {
            "version": None,
            "installed_at": None,
        }
        self._write_meta(meta)
    
        filename = metadata.get("filename", "package.bin")
        with open(self._slot_path(inactive) / filename, 'wb') as f:
            f.write(package_bytes)
        meta["slots"][inactive] = {
            "version": metadata["package_version"],
            "installed_at": metadata.get("installed_at"),
        }
        meta["active_slot"] = inactive
        self._write_meta(meta)

    def rollback(self):
        meta = self._read_meta()
        other = self._inactive_slot(meta)
        if meta["slots"][other]["version"] is None:
            raise RollbackUnavailableError("в неактивном слоте нет рабочей версии")
        meta["active_slot"] = other
        self._write_meta(meta)