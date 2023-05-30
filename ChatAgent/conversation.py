import json
import threading
import time
import uuid
from collections import OrderedDict
from pathlib import Path

import requests

from headers import get_headers_for_moderations, keep_session
from log_handler import logger


def save_conversation_data(conversation_id: str, conversation_date: str):
    path = Path(__file__).parent / "conversations"
    if not path.exists():
        path.mkdir()
    path = path / f"{conversation_id}.json"
    with open(path, "w") as f:
        f.write(conversation_date)
        logger.info(f"success in saving conversation {conversation_id}")


def load_conversation(conversation_id: str, load_str=False) -> OrderedDict | str | None:
    path = Path(__file__).parent / "conversations" / f"{conversation_id}.json"
    if path.exists():
        try:
            with open(path, "r") as f:
                if not load_str:
                    conversation = json.load(f, object_hook=OrderedDict)
                    logger.info(f"success in loading conversation {conversation_id}")
                    return conversation
                return f.read()
        except Exception as e:
            logger.warning(f"Failed in loading conversation {conversation_id}\n", e)
            return None
    else:
        logger.info(f"No conversation {conversation_id} data file")
        return None


def show_clean_conversation(conversation_id: str) -> list[str] | None:
    conversation = load_conversation(conversation_id)
    if conversation:
        try:
            clean_conversation = [
                f'{message["message"]["author"]["role"]}:\n {"".join(message["message"]["content"]["parts"])}'
                for message in conversation["mapping"].values()
                if "message" in message and message["message"]["author"]["role"] in ("user", "assistant")
            ]
            return clean_conversation
        except Exception as e:
            logger.warning(f"Failed parsing clean conversation {conversation_id}\n", e)
    return None


def show_prose_conversation(conversation_id: str) -> str | None:
    clean_conversation = show_clean_conversation(conversation_id)
    if clean_conversation:
        return "\n\n".join(clean_conversation)
    else:
        return None


class ConversationAgent:
    def __init__(self, session: requests.Session, conversation_id=None, is_keep=False):
        self.session = session
        self.is_keep = is_keep
        self.is_echo = False
        if not conversation_id:
            self.is_new_conversation = True
            self.conversation_id = None
            self.current_node = str(uuid.uuid4())
        else:
            self.is_new_conversation = False
            self.conversation_id = conversation_id
            _ = load_conversation(conversation_id)
            self.conversation_name, self.current_node = _["title"], _["current_node"]
        if self.is_keep:
            self.keep_session()

    def fetch_conversation_history(self):
        if self.is_echo:
            response = self.session.get(
                    url=f"https://chat.openai.com/backend-api/conversation/{self.conversation_id}",
                    headers=get_headers_for_moderations(self.conversation_id))

            if response.status_code == 200:
                save_conversation_data(self.conversation_id, response.text)

            else:
                logger.warning(f"get conversation history failed [Status Code] {response.status_code}")

    def rename_conversation_title(self, name: str) -> bool:
        payload = json.dumps({"title": name})
        response = self.session.post(
            url=f"https://chat.openai.com/backend-api/conversation/{self.conversation_id}",
            headers=get_headers_for_moderations(self.conversation_id),
            data=payload)
        if response.status_code == 200:
            try:
                logger.info("success in renaming conversation")
                return response.json()["success"]
            except Exception as e:
                logger.error(f"Failed in renaming conversation", e)
                return False


    @property
    def conversation_prose(self):
        return show_prose_conversation(self.conversation_id)

    def save_conversation_data(self, conversation_date: str):
        save_conversation_data(self.conversation_id, conversation_date)

    def keep_session(self):
        threading.Thread(target=self.wrapper_session_get, args=(self,)).start()

    def wrapper_session_get(self):
        while self.is_keep:
            time.sleep(10)
            self.session.get("https://chat.openai.com/api/auth/session",
                             headers=keep_session(self.conversation_id))

    def __str__(self):
        return f"Conversation\n" \
               f"conversation_id: {self.conversation_id},\n" \
               f"current_node: {self.current_node},\n" \
               f"conversation_name: {self.conversation_name})"
