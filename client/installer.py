from datetime import datetime, timezone

class InstallError(Exception):
    pass

class Installer:
    def __init__(self, view, data_storage):
        self.view = view
        self.data_storage = data_storage

    def install(self):
        package_bytes, metadata = self.view.read()

        try:
            installed_at = datetime.now(timezone.utc).isoformat()
            metadata["installed_at"] = installed_at
            self.data_storage.write_and_activate(package_bytes, metadata)
            self.view.finish()
        except OSError as e:
            raise InstallError(f"сбой установки: {e}")

        
        return {"status": "installed", "version": metadata["package_version"]}

    def rollback(self):
        self.data_storage.rollback()
        return {"status": "rolled_back", "version": self.data_storage.get_active_version()}