from temp_storage import State

PERMISSION = {
    ("loader", "write"): State.WRITABLE,
    ("verifier", "read"): State.SEALED,
    ("verifier", "approve"): State.SEALED,
    ("verifier", "reject"): State.SEALED,
    ("installer", "read"): State.VERIFIED,
    ("installer", "finish"): State.VERIFIED,
}

class Monitor():
    def __init__(self, storage):
        self.storage = storage
        self.log = []

    def check_access(self, role, action):
        required_state = PERMISSION.get((role, action))
        granted = required_state is not None and self.storage.get_state() == required_state
        self.log.append({
            "role": role,
            "action": action,
            "state": self.storage.get_state().value,
            "granted": granted,
        })
        return granted

    def get_loader_view(self):
        from views import LoaderView
        return LoaderView(self.storage, self)

    def get_verifier_view(self):
        from views import VerifierView
        return VerifierView(self.storage, self)

    def get_installer_view(self):
        from views import InstallerView
        return InstallerView(self.storage, self)