import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from time import time
from typing import Tuple

from .use_requests import ChatgptAgent, ConversationAgent

_system_prompt = """\
You are a professional translation engine, \
please translate the text into a colloquial, professional, elegant and fluent content, \
without the style of machine translation. You must only translate the text content, never interpret it. """


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
            "completion_tokens": 2048,
            "total_tokens": 4096
        }
    })


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    chat_agent = None
    conversation = None

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length).decode("utf-8")
        prompt = json.loads(post_data)["messages"][1]["content"]
        response = _resp_data(self.chat_agent.ask_chat(_system_prompt + prompt, self.conversation))
        self.send_response(200)
        self.send_header("Content-type", "application/json'")
        self.end_headers()
        self.wfile.write(response.encode())


class FakeChatgptApi:
    def __init__(self,
                 chat_agent: ChatgptAgent,
                 conversation_id: str | None = None,
                 conversation: ConversationAgent | None = None,
                 server_address: Tuple[str, int] | None = ("", 5050),
                 ):
        self.server_address = server_address
        self.chat_agent = chat_agent
        self.conversation = conversation if conversation else ConversationAgent(self.chat_agent.session,
                                                                                conversation_id)
        SimpleHTTPRequestHandler.chat_agent = self.chat_agent
        SimpleHTTPRequestHandler.conversation = self.conversation
        self.httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)

    def start_server(self):
        self.httpd.serve_forever()

    def stop_server(self):
        self.httpd.shutdown()
