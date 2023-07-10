import json
import uuid
from collections import OrderedDict
from pathlib import Path

from .log_handler import logger


def save_conversation_data(user: dict, conversation_id: str, conversation_date: str):
    path = Path(__file__).parent / "conversations" / f"{user['EMAIL']}"
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    path = path / f"{conversation_id}.json"
    with open(path, "w") as f:
        f.write(conversation_date)
        print(f"SUCCESS: Save conversation {user['EMAIL']}/{conversation_id}")


def load_conversation(user: dict, conversation_id: str, load_str=False) -> OrderedDict | str | None:
    path = Path(__file__).parent / "conversations" / f"{user['EMAIL']}" / f"{conversation_id}.json"
    if path.exists():
        try:
            with open(path, "r") as f:
                if not load_str:
                    conversation = json.load(f, object_hook=OrderedDict)
                    logger.info(f"SUCCESS: Load conversation {user['EMAIL']}/{conversation_id}")
                    return conversation
                return f.read()
        except Exception as e:
            logger.warning(f"FAILED: Load conversation {conversation_id}, ERROR: {type(e)}")
            return None
    else:
        logger.info(f"FAILED: No conversation file {conversation_id}")
        return None


def show_clean_conversation(user: dict, conversation_id: str) -> list[str] | None:
    conversation = load_conversation(user, conversation_id)
    if conversation:
        try:
            clean_conversation = [
                f'{message["message"]["author"]["role"]}:\n {"".join(message["message"]["content"]["parts"])}'
                for message in conversation["mapping"].values()
                if "message" in message and message["message"]["author"]["role"] in ("user", "assistant")
            ]
            return clean_conversation
        except Exception as e:
            logger.warning(f"Failed: Parsing clean conversation {conversation_id} {type(e)}")
    return None


def show_prose_conversation(user, conversation_id: str) -> str | None:
    clean_conversation = show_clean_conversation(user, conversation_id)
    if clean_conversation:
        return "\n\n".join(clean_conversation)
    else:
        return None


class ConversationAgent:
    def __init__(self, user: dict, conversation_id: str | None = None):
        self.is_echo = False
        self.user = user
        if not conversation_id:
            self.is_new_conversation = True
            self.conversation_id = None
            self.current_node = str(uuid.uuid4())
        else:
            self.is_new_conversation = False
            self.conversation_id = conversation_id
            _data = load_conversation(self.user, conversation_id)
            self.conversation_name, self.current_node = _data["title"], _data["current_node"]

    @property
    def conversation_prose(self):
        return show_prose_conversation(self.user, self.conversation_id)

    def save_conversation_data(self, conversation_date: str):
        save_conversation_data(self.user, self.conversation_id, conversation_date)

    def __str__(self):
        return f"Conversation\n" \
               f"conversation_user: {self.user['EMAIL']},\n" \
               f"conversation_id: {self.conversation_id},\n" \
               f"current_node: {self.current_node},\n" \
               f"conversation_name: {self.conversation_name}"
