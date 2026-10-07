from temp_storage import State, AccessDeniedError


class LoaderView:
    def __init__(self, storage, monitor):
        self._storage = storage
        self._monitor = monitor

    def write(self, package_bytes, metadata):
        if not self._monitor.check_access("loader", "write"):
            raise AccessDeniedError("загрузчику запрещена запись в текущем состоянии")
        self._storage.write_package(package_bytes, metadata)


class VerifierView:
    def __init__(self, storage, monitor):
        self._storage = storage
        self._monitor = monitor

    def read(self):
        if not self._monitor.check_access("verifier", "read"):
            raise AccessDeniedError("верификатору запрещено чтение в текущем состоянии")
        return self._storage.read_package(State.SEALED)

    def approve(self):
        if not self._monitor.check_access("verifier", "approve"):
            raise AccessDeniedError("верификатору запрещено подтверждение в текущем состоянии")
        self._storage.mark_verified()

    def reject(self):
        if not self._monitor.check_access("verifier", "reject"):
            raise AccessDeniedError("верификатору запрещён сброс в текущем состоянии")
        self._storage.reset(State.SEALED)


class InstallerView:
    def __init__(self, storage, monitor):
        self._storage = storage
        self._monitor = monitor

    def read(self):
        if not self._monitor.check_access("installer", "read"):
            raise AccessDeniedError("установщику запрещено чтение в текущем состоянии")
        return self._storage.read_package(State.VERIFIED)

    def finish(self):
        if not self._monitor.check_access("installer", "finish"):
            raise AccessDeniedError("установщику запрещено завершение в текущем состоянии")
        self._storage.reset(State.VERIFIED)