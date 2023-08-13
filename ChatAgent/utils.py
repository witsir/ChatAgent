import random
import os
import tempfile
import time

import requests

# import threading

# class SingletonMeta(type):
#     _instances = {}
#     _lock = threading.Lock()
#
#     def __call__(cls, *args, **kwargs):
#         with cls._lock:
#             if cls not in cls._instances:
#                 instance = super().__call__(*args, **kwargs)
#                 cls._instances[cls] = instance
#         return cls._instances[cls]
from .exceptions import Requests500Error, RequestsError, RetryFailed, Requests4XXError


class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
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


# define a retry decorator
def retry(
        func,
        initial_delay: float = 1,
        exponential_base: float = 2,
        jitter: bool = True,
        max_retries: int = 3
):
    """Retry a function with exponential backoff."""

    def wrapper(*args, **kwargs):
        # Initialize variables
        num_retries = 0
        delay = initial_delay

        # Loop until a successful response or max_retries is hit or an exception is raised
        while True:
            try:
                return func(*args, **kwargs)

            # Retry on specified errors
            except (Requests500Error, RequestsError) as e:
                print(e)
                num_retries += 1
                if num_retries > max_retries:
                    raise RetryFailed(
                        f"Maximum number of retries ({max_retries}) exceeded. Last Exception {type(e)}"
                    )
                delay *= exponential_base * (1 + jitter * random.random())

                time.sleep(delay)

    return wrapper
