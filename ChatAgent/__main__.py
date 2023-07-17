from .config import config
from .server import FakeChatgptApi

fake_chatgpt_api = FakeChatgptApi(config["COV"])
fake_chatgpt_api.run_server()
