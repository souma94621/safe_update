import sys
import shutil
from pathlib import Path

import pytest

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "client"))

from temp_storage import TempStorage, State, AccessDeniedError
from monitor import Monitor

@pytest.fixture
def clean_temp_storage():
    """Сносит storage/temp перед каждым тестом и после него."""
    temp_dir = BASE / "storage" / "temp"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    yield
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def storage(clean_temp_storage):
    """Свежее временное хранилище в состоянии WRITABLE."""
    return TempStorage()


@pytest.fixture
def monitor(storage):
    """Монитор поверх чистого хранилища."""
    return Monitor(storage)


@pytest.fixture
def loader_view(monitor):
    return monitor.get_loader_view()


@pytest.fixture
def verifier_view(monitor):
    return monitor.get_verifier_view()


@pytest.fixture
def installer_view(monitor):
    return monitor.get_installer_view()


class TestWriteToSealedStorage:
    def test_write_to_sealed_storage_raises_access_denied(self, storage, loader_view):
        """
        После перевода хранилища в SEALED повторная запись через LoaderView
        должна падать с AccessDeniedError.
        """
        # первая запись — переводит хранилище в SEALED
        loader_view.write(b"first package", {"filename": "first.bin"})
        assert storage.get_state() == State.SEALED

        # вторая запись — должна упасть
        with pytest.raises(AccessDeniedError):
            loader_view.write(b"second package", {"filename": "second.bin"})

    def test_write_to_verified_storage_raises_access_denied(self, storage, loader_view, verifier_view):
        """
        В состоянии VERIFIED запись тоже запрещена — LoaderView требует WRITABLE.
        """
        # доводим хранилище до VERIFIED
        loader_view.write(b"pkg", {"filename": "pkg.bin"})
        verifier_view.read()
        verifier_view.approve()
        assert storage.get_state() == State.VERIFIED

        with pytest.raises(AccessDeniedError):
            loader_view.write(b"another", {"filename": "another.bin"})


class TestReadBeforeSealed:
    def test_verifier_read_in_writable_raises_access_denied(self, storage, verifier_view):
        """
        В состоянии WRITABLE верификатор не имеет права читать временное хранилище.
        """
        assert storage.get_state() == State.WRITABLE

        with pytest.raises(AccessDeniedError):
            verifier_view.read()

    def test_verifier_read_in_verified_raises_access_denied(self, storage, loader_view, verifier_view):
        """
        В состоянии VERIFIED верификатор тоже не должен читать — данные уже
        передаются установщику.
        """
        loader_view.write(b"pkg", {"filename": "pkg.bin"})
        verifier_view.read()
        verifier_view.approve()
        assert storage.get_state() == State.VERIFIED

        with pytest.raises(AccessDeniedError):
            verifier_view.read()


class TestInstallerReadRestrictions:
    def test_installer_read_in_writable_raises(self, storage, installer_view):
        """Установщик в WRITABLE читать не должен."""
        assert storage.get_state() == State.WRITABLE
        with pytest.raises(AccessDeniedError):
            installer_view.read()

    def test_installer_read_in_sealed_raises(self, storage, loader_view, installer_view):
        """Установщик в SEALED читать не должен — данные ещё не верифицированы."""
        loader_view.write(b"pkg", {"filename": "pkg.bin"})
        assert storage.get_state() == State.SEALED
        with pytest.raises(AccessDeniedError):
            installer_view.read()


class TestMonitorLogsDenial:
    def test_denied_access_logged_with_granted_false(self, storage, monitor, verifier_view):
        """При отказе доступа монитор фиксирует granted=False."""
        with pytest.raises(AccessDeniedError):
            verifier_view.read()

        assert len(monitor.log) == 1
        entry = monitor.log[0]
        assert entry["role"] == "verifier"
        assert entry["action"] == "read"
        assert entry["granted"] is False
        assert entry["state"] == State.WRITABLE.value

    def test_granted_access_logged_with_granted_true(self, storage, monitor, loader_view):
        """При успешной записи монитор фиксирует granted=True."""
        loader_view.write(b"pkg", {"filename": "pkg.bin"})

        assert len(monitor.log) == 1
        entry = monitor.log[0]
        assert entry["role"] == "loader"
        assert entry["action"] == "write"
        assert entry["granted"] is True