import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from time import time
from typing import Tuple

from .chat_agent import ChatAgentPool
from .exceptions import Requests4XXError
from .log_handler import logger

# _system_prompt = """\
# You are a professional translation engine, \
# please translate the text into a colloquial, professional, elegant and fluent content, \
# without the style of machine translation. You must only translate the text content, never interpret it. \
# Keep and let -|1|- as a marker. """

_system_prompt = """You are a translation engine, you can only translate text and cannot interpret it, and do not \
explain any sentences or generate content which is not beneficial for translation."""


# _system_prompt = """\ You are a professional translation assistant, you understand the significance of accurately \
# conveying the intended meaning of the original text. Your goal is to provide professional-level, idiomatic, \
# standard and accurate translation."""


def _resp_data(content: str) -> str:
    return json.dumps({
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": int(time()),
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": content,
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 2048,
            "completion_tokens": 8192,
            "total_tokens": 10240
        }
    })


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    chat_agent_pool = None

    def do_POST(self):
        try:
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length).decode("utf-8")
            # logger.info(f'post_data:\n{post_data}')
            system_prompt = json.loads(post_data)["messages"][0]["content"]
            prompt = json.loads(post_data)["messages"][1]["content"]
            response = _resp_data(SimpleHTTPRequestHandler.chat_agent_pool.ask_chat(system_prompt + " " + prompt))
            self.send_response(200)
            self.send_header("Content-type", "application/json'")
            self.end_headers()
            self.wfile.write(response.encode())
        except BrokenPipeError:
            print("[Errno 32] Broken pipe")
        except Requests4XXError as e:
            logger.warning(f"{e}")
        except Exception as e:
            logger.exception(e)


class ThreadedHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address):
        super().__init__(server_address, SimpleHTTPRequestHandler)


class FakeChatgptApi:
    def __init__(self,
                 conversation_list: list[str, None] | None = None,
                 server_address: Tuple[str, int] | None = ("", 5050),
                 ):
        self.server_address = server_address
        if not conversation_list:
            conversation_list = [None, None, None, None]
        self.chat_agent_pool = ChatAgentPool(conversation_list)
        SimpleHTTPRequestHandler.chat_agent_pool = self.chat_agent_pool
        self.httpd = ThreadedHTTPServer(self.server_address)

    def run_server(self, del_cov: bool = True):
        print(f"Server running on {self.server_address}")
        try:
            self.httpd.serve_forever()
        except KeyboardInterrupt:
            try:
                print(f"\nServer will shut down...")
                self.httpd.shutdown()
                self.httpd.server_close()
                self.chat_agent_pool.close(del_cov)
            except Exception as e:
                logger.warning(f"{type(e)}")
