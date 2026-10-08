class UpdateManager:
    def __init__(self, loader, verifier, installer, current_version):
        self.loader = loader
        self.verifier = verifier
        self.installer = installer
        self.current_version = current_version

    def run(self):
        update_info = self.loader.check_version(self.current_version)
        if update_info is None:
            return {"status": "no_update"}

        self.loader.download(update_info)

        verdict = self.verifier.verify(self.current_version)
        if verdict["verdict"] != "pass":
            return {"status": "verify_failed", "detail": verdict}

        try:
            result = self.installer.install()
            self.current_version = result["version"]
            return {"status": "installed", "detail": result}
        except Exception as e:
            return {"status": "install_failed", "error": str(e)}