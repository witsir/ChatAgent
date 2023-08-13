from .server import FakeChatgptApi

fake_chatgpt_api = FakeChatgptApi()
fake_chatgpt_api.run_server(True)
