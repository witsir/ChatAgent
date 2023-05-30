import json
import re
import threading
import uuid

import requests
from requests import cookies

from auth_handler import get_cookies, LLM_PROVIDER, save_cookies
from config import EMAIL, PASSWORD
from conversation import ConversationAgent
from exceptions import NoSuchCookiesException, AccessTokenExpiredException
from headers import get_headers_for_moderations, get_headers_for_conversation, get_headers_for_new_conversation
from log_handler import logger
from playload import get_request_conversation_playload, get_request_moderations_playload, get_new_conversation_playload
from use_selenium import SeleniumRequests
from utils import SingletonMeta


def _callback_mod(r, *args, **kwargs):
    if r.status_code == 200 and 'json' in r.headers['Content-Type']:
        try:
            moderation = r.json()
            if moderation["flagged"] or moderation["blocked"]:
                logger.warning(f"moderation flagged is {moderation['flagged']} blocked is {moderation['blocked']}")
        except Exception as e:
            logger.warning(f"some error happen", e)


def _get_cookies_for_requests(session: requests.Session, name: LLM_PROVIDER):
    for item in get_cookies(name):
        jar = cookies.cookiejar_from_dict({item["name"]: item["value"]})
        session.cookies.update(jar)
    return session


def _update_cookies(resp: requests.Response, llm_cookies):
    for cookie_jar in resp.cookies:
        for cookie in llm_cookies:
            if cookie["name"] == cookie_jar.name:
                cookie["value"] = cookie_jar.value
                cookie["expires"] = cookie_jar.expires
            break


class ChatgptAgent(metaclass=SingletonMeta):
    def __init__(self, proxies: dict[str, str] = None):
        self.g = None
        self.sl = None
        self.session = self.prepare_session(proxies)
        self.cookies = get_cookies("chatgpt")
        self.is_echo = False
        self.register_conversations = set()

    def init_selenium(self):
        self.sl = SeleniumRequests()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.is_echo:
            save_cookies("chatgpt", self.cookies)
            for conversation in self.register_conversations:
                conversation.fetch_conversation_history()

    def prepare_session(self, proxies: dict[str, str] | None) -> requests.Session:
        session = requests.Session()
        if not proxies:
            proxies = {'http': "http://localhost:7890", 'https': "http://localhost:7890"}
        session.proxies.update(proxies)
        try:
            return _get_cookies_for_requests(session, "chatgpt")
        except NoSuchCookiesException as e:
            logger.warning("Not fetch cookies yet, start use selenium", e)
            self.sl.chatgpt_login(EMAIL, PASSWORD)
            return _get_cookies_for_requests(session, "chatgpt")

    def _pass_moderations(self, conversation_id: str, prompt: str, message_id: str):
        try:
            self.session.post(
                "https://chat.openai.com/backend-api/moderations",
                headers=get_headers_for_moderations(conversation_id),
                hooks={'response': _callback_mod},
                data=get_request_moderations_playload(prompt, conversation_id, message_id))
        except AccessTokenExpiredException:
            return

    def ask_chat(self,
                 prompt: str,
                 conversation: ConversationAgent | None,
                 pass_moderation=False
                 ) -> str | None:
        message_id = str(uuid.uuid4())
        if not conversation.is_new_conversation:
            conversation_playload = get_request_conversation_playload(prompt, conversation.conversation_id,
                                                                      conversation.current_node,
                                                                      message_id)
        else:
            conversation_playload = get_new_conversation_playload(prompt,
                                                                  conversation.current_node,
                                                                  message_id)
        self.register_conversations.add(conversation)
        if pass_moderation:
            threading.Thread(target=self._pass_moderations,
                             args=(conversation.conversation_id, prompt, message_id)).start()
        try:
            headers_ = None
            try:
                if not conversation.is_new_conversation:
                    headers_ = get_headers_for_conversation(conversation.conversation_id)
                else:
                    headers_ = get_headers_for_new_conversation()
            except AccessTokenExpiredException:
                logger.warning(f"Accesss token expired try use selenium")

                self.init_selenium()
                self.sl.chatgpt_log_with_cookies()

            response = self.session.post(
                "https://chat.openai.com/backend-api/conversation",
                headers=headers_,
                data=conversation_playload
            )
            # test
            if response.status_code == 200:
                _update_cookies(response, self.cookies)
                response_text = response.text.replace("data: [DONE]", "")
                last_data = re.findall(r'data: (.*)', response_text)[-1]
                complete_data = json.loads(last_data)
                if conversation.is_new_conversation:
                    conversation.conversation_id = complete_data["conversation_id"]
                    conversation.is_new_conversation = False
                conversation.current_node = complete_data["message"]["id"]
                conversation.is_echo = True
                self.is_echo = True
                return complete_data["message"]["content"]["parts"][0]
            elif response.status_code == 403:
                logger.error(f"[Status Code] {response.status_code}")
                self.init_selenium()
                try:
                    self.sl.chatgpt_log_with_cookies()
                except Exception as e:
                    logger.error(f"some bad things happened", e)
                resp = self.ask_chat(prompt, conversation)
                return resp if resp else None
            elif response.status_code >= 500:
                logger.warning(f" Looks like the server is either overloaded or down. Try again later.\n"
                               f"[Status Code] {response.status_code} | [Response Text] {response.text}")
                return None
            else:
                logger.error(f"[Status Code] {response.status_code} | [Response Text] {response.text}")
                return None
        except Exception as e:
            logger.warning(f"Error when calling ask_chat: ", e)
            return None
