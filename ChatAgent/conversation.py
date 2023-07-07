import json
import uuid
from collections import OrderedDict
from pathlib import Path

from .log_handler import logger


def save_conversation_data(conversation_id: str, conversation_date: str):
    path = Path(__file__).parent / "conversations"
    if not path.exists():
        path.mkdir()
    path = path / f"{conversation_id}.json"
    with open(path, "w") as f:
        f.write(conversation_date)
        print(f"SUCCESS: Save conversation {conversation_id}")


def load_conversation(conversation_id: str, load_str=False) -> OrderedDict | str | None:
    path = Path(__file__).parent / "conversations" / f"{conversation_id}.json"
    if path.exists():
        try:
            with open(path, "r") as f:
                if not load_str:
                    conversation = json.load(f, object_hook=OrderedDict)
                    logger.info(f"SUCCESS: Load conversation {conversation_id}")
                    return conversation
                return f.read()
        except Exception as e:
            logger.warning(f"FAILED: Load conversation {conversation_id}, ERROR: {type(e)}")
            return None
    else:
        logger.info(f"FAILED: No conversation file {conversation_id}")
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
            logger.warning(f"Failed: Parsing clean conversation {conversation_id} {type(e)}")
    return None


def show_prose_conversation(conversation_id: str) -> str | None:
    clean_conversation = show_clean_conversation(conversation_id)
    if clean_conversation:
        return "\n\n".join(clean_conversation)
    else:
        return None


class ConversationAgent:
    def __init__(self, conversation_id=None):
        self.is_echo = False
        if not conversation_id:
            self.is_new_conversation = True
            self.conversation_id = None
            self.current_node = str(uuid.uuid4())
        else:
            self.is_new_conversation = False
            self.conversation_id = conversation_id
            _data = load_conversation(conversation_id)
            self.conversation_name, self.current_node = _data["title"], _data["current_node"]

    @property
    def conversation_prose(self):
        return show_prose_conversation(self.conversation_id)

    def save_conversation_data(self, conversation_date: str):
        save_conversation_data(self.conversation_id, conversation_date)

    def __str__(self):
        return f"Conversation\n" \
               f"conversation_id: {self.conversation_id},\n" \
               f"current_node: {self.current_node},\n" \
               f"conversation_name: {self.conversation_name})"
