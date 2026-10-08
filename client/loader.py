import requests
from views import LoaderView
from pathlib import Path

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SERVER_URL = "https://localhost:8000"
DIR = Path(__file__).parent.parent / 'keys' / 'server.crt'

class NetworkError(Exception):
    pass

class ServerAuthError(Exception):
    pass

class DownloadError(Exception):
    pass

class Loader():
    def __init__(self, view):
        self.view = view

    def check_version(self, current_version):
        try:
            response = requests.post(SERVER_URL + "/version_check", json={"client_version": current_version}, verify=str(DIR))
        except requests.exceptions.SSLError:
            raise ServerAuthError("сертификат сервера не прошёл проверку")
        except requests.exceptions.ConnectionError:
            raise NetworkError("сервер недоступен")
        
        data = response.json()

        if not data["available"]:
            return None
        return data

    def download(self, update_info):
        try:
            response = requests.get(SERVER_URL + f"/package/{update_info['package_version']}", verify=str(DIR))
        except requests.exceptions.SSLError:
            raise ServerAuthError("сертификат сервера не прошёл проверку")
        except requests.exceptions.ConnectionError:
            raise DownloadError("ошибка загрузки")
        
        if response.status_code != 200:
            raise DownloadError("ошибка загрузки")

        content_disposition = response.headers.get("content-disposition", "")
        filename = content_disposition.split('filename="')[-1].rstrip('"') if 'filename=' in content_disposition else update_info["package_version"]
        update_info["filename"] = filename

        self.view.write(response.content, update_info)