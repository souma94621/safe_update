# main.py
from temp_storage import TempStorage
from data_storage import DataStorage
from monitor import Monitor
from loader import Loader
from verifier import Verifier
from installer import Installer
from manager import UpdateManager

def build_system():
    t_storage = TempStorage()
    d_storage = DataStorage()
    monitor = Monitor(t_storage)
    loader = Loader(monitor.get_loader_view())
    verifier = Verifier(monitor.get_verifier_view())
    installer = Installer(monitor.get_installer_view(), d_storage)
    version = d_storage.get_active_version() or '0.0.0'
    manager = UpdateManager(loader, verifier, installer, version)
    return manager, monitor

if __name__ == "__main__":
    manager, _ = build_system()
    manager.run()