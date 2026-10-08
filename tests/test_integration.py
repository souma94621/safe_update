import sys
import shutil
from pathlib import Path

import pytest
import requests

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "client"))

from temp_storage import TempStorage, State, AccessDeniedError, UnacceptableTransitionError
from data_storage import DataStorage, RollbackUnavailableError
from monitor import Monitor
from loader import Loader, NetworkError, ServerAuthError, DownloadError
from verifier import Verifier
from installer import Installer, InstallError
from manager import UpdateManager


# ─────────────────────────────────────────────────────────────────────────────
# Хелперы
# ─────────────────────────────────────────────────────────────────────────────

SERVER_URL = "https://localhost:8000"


def _latest_version():
    """
    Спрашивает у сервера максимальную версию, которую он готов отдать клиенту
    с версией 0.0.0. Тесты не привязаны к конкретному номеру — если в реестр
    добавят новую версию, тесты продолжат работать.
    """
    resp = requests.post(
        f"{SERVER_URL}/version_check",
        json={"client_version": "0.0.0"},
        verify=False,
    )
    return resp.json()["package_version"]


# ─────────────────────────────────────────────────────────────────────────────
# Фикстуры
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def clean_storages():
    """Сносит storage/ перед каждым тестом и после него."""
    storage_dir = BASE / "storage"
    if storage_dir.exists():
        shutil.rmtree(storage_dir)
    yield
    if storage_dir.exists():
        shutil.rmtree(storage_dir)


@pytest.fixture
def system(clean_storages):
    """Собирает полную систему как в client/main.build_system()."""
    t_storage = TempStorage()
    d_storage = DataStorage()
    monitor = Monitor(t_storage)
    loader = Loader(monitor.get_loader_view())
    verifier = Verifier(monitor.get_verifier_view())
    installer = Installer(monitor.get_installer_view(), d_storage)
    version = d_storage.get_active_version() or "0.0.0"
    manager = UpdateManager(loader, verifier, installer, version)

    return {
        "temp": t_storage,
        "data": d_storage,
        "monitor": monitor,
        "loader": loader,
        "verifier": verifier,
        "installer": installer,
        "manager": manager,
    }


def _seed_previous_version(system, version="1.0.0"):
    """
    Кладёт рабочую версию в data_storage (становится активной).
    После этого система выглядит «работающей на версии version»,
    а неактивный слот содержит None.
    """
    system["data"].write_and_activate(
        b"previous version contents",
        {
            "filename": f"prev_{version}.bin",
            "package_version": version,
            "installed_at": "2026-10-01T00:00:00+00:00",
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Позитивные сценарии
# ─────────────────────────────────────────────────────────────────────────────

class TestHappyPath:
    def test_full_update_cycle_from_scratch(self, system):
        """С нулевой версии — полный цикл до installed, temp вернулся в WRITABLE."""
        t = system["temp"]
        assert t.get_state() == State.WRITABLE

        latest = _latest_version()
        result = system["manager"].run()

        assert result["status"] == "installed"
        assert result["detail"]["version"] == latest
        assert t.get_state() == State.WRITABLE
        assert system["data"].get_active_version() == latest

    def test_monitor_logged_each_access(self, system):
        """Монитор фиксирует доступы loader/verifier/installer."""
        system["manager"].run()
        roles = {e["role"] for e in system["monitor"].log}
        assert "loader" in roles
        assert "verifier" in roles
        assert "installer" in roles
        assert all(e["granted"] for e in system["monitor"].log)

    def test_state_transitions_writable_sealed_verified(self, system):
        """Состояния проходят через все три стадии по шагам."""
        t = system["temp"]
        seen = [t.get_state()]

        info = system["loader"].check_version("1.2.0")
        assert info is not None
        system["loader"].download(info)
        seen.append(t.get_state())

        verdict = system["verifier"].verify("1.2.0")
        assert verdict["verdict"] == "pass"
        seen.append(t.get_state())

        system["installer"].install()
        seen.append(t.get_state())

        assert seen == [State.WRITABLE, State.SEALED, State.VERIFIED, State.WRITABLE]


# ─────────────────────────────────────────────────────────────────────────────
# Верификация — негативные сценарии
# ─────────────────────────────────────────────────────────────────────────────

class TestVerificationFailures:
    def test_broken_signature_rejected(self, system, monkeypatch):
        import verifier as verifier_mod
        monkeypatch.setattr(verifier_mod, "check_signature", lambda *a, **k: False)

        info = system["loader"].check_version("1.2.0")
        system["loader"].download(info)
        verdict = system["verifier"].verify("1.2.0")

        assert verdict["verdict"] == "fail"
        assert verdict["reason"]["signature"] is False
        assert system["temp"].get_state() == State.WRITABLE

    def test_broken_checksum_rejected(self, system, monkeypatch):
        import verifier as verifier_mod
        monkeypatch.setattr(verifier_mod, "checksum", lambda *a, **k: False)

        info = system["loader"].check_version("1.2.0")
        system["loader"].download(info)
        verdict = system["verifier"].verify("1.2.0")

        assert verdict["verdict"] == "fail"
        assert verdict["reason"]["checksum"] is False

    def test_manager_stops_on_failed_verification(self, system, monkeypatch):
        """При неудачной верификации installer.install() не вызывается."""
        import verifier as verifier_mod
        monkeypatch.setattr(verifier_mod, "check_signature", lambda *a, **k: False)

        called = {"install": False}
        original_install = system["installer"].install

        def spy_install():
            called["install"] = True
            return original_install()

        system["installer"].install = spy_install
        result = system["manager"].run()

        assert result["status"] == "verify_failed"
        assert called["install"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Доступ — негативные сценарии
# ─────────────────────────────────────────────────────────────────────────────

class TestMonitorAccessControl:
    def test_loader_cannot_write_when_sealed(self, system):
        """Повторная запись в SEALED запрещена (через LoaderView)."""
        info = system["loader"].check_version("1.2.0")
        system["loader"].download(info)

        with pytest.raises(AccessDeniedError):
            system["loader"].view.write(b"", {"filename": "x.bin"})

    def test_verifier_cannot_read_in_writable(self, system):
        """В WRITABLE верификатор читать не должен."""
        with pytest.raises(AccessDeniedError):
            system["verifier"].view.read()

    def test_installer_cannot_read_before_verified(self, system):
        """В SEALED (сразу после загрузки) установщик читать не должен."""
        info = system["loader"].check_version("1.2.0")
        system["loader"].download(info)

        with pytest.raises(AccessDeniedError):
            system["installer"].view.read()

    def test_monitor_denies_and_logs(self, system):
        """При отказе монитор фиксирует granted=False."""
        with pytest.raises(AccessDeniedError):
            system["verifier"].view.read()

        denied = [e for e in system["monitor"].log if not e["granted"]]
        assert len(denied) >= 1
        assert denied[0]["role"] == "verifier"


# ─────────────────────────────────────────────────────────────────────────────
# Сеть — негативные сценарии
# ─────────────────────────────────────────────────────────────────────────────

class TestNetworkFailures:

    def test_download_error_on_bad_version(self, system):
        """Сервер вернёт 404 → DownloadError."""
        with pytest.raises(DownloadError):
            system["loader"].download({"package_version": "99.99.99"})


# ─────────────────────────────────────────────────────────────────────────────
# Откат (A/B-схема)
# ─────────────────────────────────────────────────────────────────────────────

class TestRollback:
    def test_rollback_after_successful_install(self, system):
        """После двух установок откат доступен."""
        system["data"].write_and_activate(
            b"v1", {"filename": "v1.bin", "package_version": "1.0.0", "installed_at": "x"},
        )
        system["data"].write_and_activate(
            b"v2", {"filename": "v2.bin", "package_version": "1.1.0", "installed_at": "y"},
        )
        assert system["data"].get_active_version() == "1.1.0"

        rb = system["installer"].rollback()
        assert rb["status"] == "rolled_back"
        assert system["data"].get_active_version() == "1.0.0"

    def test_rollback_unavailable_at_first_boot(self, system):
        """На чистой системе откатывать некуда."""
        with pytest.raises(RollbackUnavailableError):
            system["data"].rollback()

    def test_ab_scheme_keeps_previous_version(self, system):
        """После установки новой версии поверх 1.0.0 откат возвращает 1.0.0."""
        _seed_previous_version(system, version="1.0.0")
        assert system["data"].get_active_version() == "1.0.0"

        latest = _latest_version()
        system["manager"].current_version = "1.0.0"
        result = system["manager"].run()
        assert result["status"] == "installed"
        assert system["data"].get_active_version() == latest

        system["installer"].rollback()
        assert system["data"].get_active_version() == "1.0.0"


# ─────────────────────────────────────────────────────────────────────────────
# Конечный автомат temp_storage
# ─────────────────────────────────────────────────────────────────────────────

class TestTempStorageStateMachine:
    def test_cannot_mark_verified_from_writable(self, system):
        with pytest.raises(UnacceptableTransitionError):
            system["temp"].mark_verified()

    def test_cannot_reset_from_writable(self, system):
        with pytest.raises(AccessDeniedError):
            system["temp"].reset(State.SEALED)

    def test_double_write_forbidden(self, system):
        info = system["loader"].check_version("1.2.0")
        system["loader"].download(info)
        with pytest.raises(AccessDeniedError):
            system["loader"].view.write(b"x", {"filename": "y.bin"})


# ─────────────────────────────────────────────────────────────────────────────
# Граничные случаи
# ─────────────────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_no_update_when_client_is_latest(self, system):
        """Клиент на самой свежей версии — no_update, ничего не грузится."""
        latest = _latest_version()
        system["manager"].current_version = latest
        result = system["manager"].run()
        assert result["status"] == "no_update"
        assert system["temp"].get_state() == State.WRITABLE

    def test_version_comparison_handles_double_digits(self):
        """1.10.0 > 1.9.0 — сравнение не лексикографическое."""
        from verifier import check_version
        assert check_version("1.10.0", "1.9.0") is True
        assert check_version("1.9.0", "1.10.0") is False
        assert check_version("1.2.0", "1.2.0") is False