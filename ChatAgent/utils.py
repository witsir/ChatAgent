import threading
import os
import tempfile
import requests


class SingletonMeta(type):
    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]


def download_file(self):
    p = os.path.expanduser("~/Library/Application Support/undetected_chromedriver")
    u = "%s/%s/%s" % (self.url_repo, self.version_full.vstring, self.zip_name)
    response = requests.get(u, stream=True)
    with tempfile.NamedTemporaryFile(delete=False, dir=p) as temp_file:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                temp_file.write(chunk)
    return temp_file.name
