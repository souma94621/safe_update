from pathlib import Path

DIR = Path(__file__).parent.parent / "packages"

version_dict = {'1.3.0' : DIR / "update_1.3.0.txt", '1.2.0' : DIR / "update_1.2.0.txt", '1.4.0' : DIR / "update_1.4.0.txt", '1.5.0' : DIR / "update_1.5.0.txt", '1.5.1' : DIR / "update_1.5.1.txt", '2.0.0' : DIR / "update_2.0.0.txt"}

def last_version():
    last = None
    last_parts = None
    for v in version_dict:
        parts = [int(i) for i in v.split('.')]
        if last_parts is None or parts > last_parts:
            last = v
            last_parts = parts
    return last

def version_path(version):
    if version in version_dict:
        return version_dict[version]
    else:
        return None

def has_update(client_version):
    latest = last_version()
    latest_int = [int(i) for i in latest.split('.')]
    cli_version_int = [int(i) for i in client_version.split('.')]
    if latest_int > cli_version_int:
        return True, latest
    return False, None