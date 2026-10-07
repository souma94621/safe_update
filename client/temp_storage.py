from pathlib import Path
from enum import Enum
import json

TEMP_DIR = Path(__file__).parent.parent / "storage" / "temp"
TEMP_DIR_STATE = TEMP_DIR / "state.json"
TEMP_DIR_METADATA = TEMP_DIR / "metadata.json"

class State(Enum):
    WRITABLE = "writable"
    SEALED = "sealed"
    VERIFIED = "verified"

class AccessDeniedError(Exception):
    pass

class UnacceptableTransitionError(Exception):
    pass

class TempStorage:
    def __init__(self):
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        if not TEMP_DIR_STATE.exists():
            self._write_state(State.WRITABLE)

    def get_state(self):
        with open(TEMP_DIR_STATE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return State(data["state"])

    def _write_state(self, state):
        with open(TEMP_DIR_STATE, 'w', encoding='utf-8') as f:
            json.dump({"state": state.value}, f)

    def write_package(self, package_bytes, metadata):
        if self.get_state() != State.WRITABLE:
            raise AccessDeniedError("запись  возможна только в состоянии writable")

        package_path = TEMP_DIR / metadata["filename"]
        with open(package_path, 'wb') as f:
            f.write(package_bytes)

        with open(TEMP_DIR_METADATA, 'w', encoding='utf-8') as f:
            json.dump(metadata, f)

        self._write_state(State.SEALED)

    def read_package(self, allowed_state):
        if self.get_state() != allowed_state:
            raise AccessDeniedError("чтение в этом состоянии запрещено")

        with open(TEMP_DIR_METADATA, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        package_path = TEMP_DIR / metadata["filename"]
        with open(package_path, 'rb') as f:
            package_bytes = f.read()

        return package_bytes, metadata

    def mark_verified(self):
        if self.get_state() != State.SEALED:
            raise UnacceptableTransitionError("Переход из этого состояния запрещен")

        self._write_state(State.VERIFIED)

    def reset(self, allowed_state):
        if self.get_state() != allowed_state:
            raise AccessDeniedError("сброс из этого состояния запрещён")

        try:
            with open(TEMP_DIR_METADATA, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            package_path = TEMP_DIR / metadata["filename"]
            package_path.unlink(missing_ok=True)
        except (FileNotFoundError, KeyError, json.JSONDecodeError):
            pass

        TEMP_DIR_METADATA.unlink(missing_ok=True)
        self._write_state(State.WRITABLE)
