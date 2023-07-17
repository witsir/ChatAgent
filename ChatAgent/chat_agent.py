import json
import re
import threading
import uuid
from pathlib import Path

import time
from json import JSONDecodeError

import requests
from requests.utils import cookiejar_from_dict

from .config import config
from .auth_handler import get_cookies, save_cookies, get_access_token
from .conversation import ConversationAgent
from .exceptions import NoSuchCookiesException, AccessTokenExpiredException, Requests403Error, Requests500Error, \
    RequestsError, AuthenticationTokenExpired
from .headers import get_headers_for_moderations, get_headers_for_conversation, get_headers_for_new_conversation, \
    keep_session, get_headers_for_fetch_conversations
from .log_handler import logger
from .playload import get_request_conversation_playload, \
    get_new_conversation_playload, get_continue_conversation_playload
from .uc_back import SeleniumRequests
from .utils import retry, SingletonMeta


# def _callback_mod(r, *args, **kwargs):
#     if r.status_code == 200 and 'json' in r.headers['Content-Type']:
#         try:
#             moderation = r.json()
#             if moderation["flagged"] or moderation["blocked"]:
#                 logger.warning(f"moderation flagged is {moderation['flagged']} blocked is {moderation['blocked']}")
#         except Exception as e:
#             logger.warning(f"some error happen {type(e)}")


def _update_cookies(session: requests.Session, resp: requests.Response, chat_cookies: list[dict]):
    session.cookies.update(resp.cookies)
    for cookie_jar in resp.cookies:
        found = False
        for cookie in chat_cookies:
            if cookie["name"] == cookie_jar.name:
                cookie["value"] = cookie_jar.value
                cookie["expires"] = cookie_jar.expires
            found = True
            break
        if not found:
            chat_cookies.append({"name": cookie_jar.name,
                                 "value": cookie_jar.value,
                                 "expires": cookie_jar.expires,
                                 "path": cookie_jar.path,
                                 "domain": cookie_jar.domain,
                                 "secure": cookie_jar.secure,
                                 })


def _list_local_conversations_id(user: dict) -> list[str]:
    path = Path(__file__).parent / "conversations" / f"{user['EMAIL']}"
    conversation_id_list = []
    for file in path.iterdir():
        if file.suffix == '.json':
            conversation_id_list.append(file.stem)
    return conversation_id_list


class ChatgptAgent:
    def __init__(self, user: dict, conversation: ConversationAgent | str | None,
                 is_keep_session: bool = False,
                 proxies: dict[str, str] = None):
        self.user = user
        self.sl = None
        self.session = self._prepare_session(proxies)
        self.cookies = self.get_cookies()
        self.access_token = self.get_access_token()
        self.is_keep_session = is_keep_session
        self.register_conversations = set()
        if type(conversation) == str:
            self.current_conversation = ConversationAgent(user, conversation)
        elif type(conversation) == ConversationAgent:
            self.current_conversation = conversation
        else:
            self.current_conversation = ConversationAgent(user)
        self.start_keep_session = False
        self.lock = threading.Lock()

    @property
    def current_conversation(self):
        return self._current_conversation

    @current_conversation.setter
    def current_conversation(self, conversation: ConversationAgent | str):
        if type(conversation) == str:
            self._current_conversation = ConversationAgent(self.user, conversation)
        else:
            self._current_conversation = conversation

    def set_conversation(self, conversation: ConversationAgent):
        self._current_conversation = conversation

    def _keep_session(self):
        self.start_keep_session = True
        threading.Thread(target=self._wrapper_session_get).start()

    def _wrapper_session_get(self):
        while self.is_keep_session:
            time.sleep(300)
            response = self.session.get("https://chat.openai.com/api/auth/session",
                                        headers=keep_session(self._current_conversation.conversation_id))
            logger.info(f"keep_session get method return")
            _update_cookies(self.session, response, self.cookies)

    @retry
    def rename_conversation_title(self, name: str, conversation: ConversationAgent | None) -> bool:
        if not conversation:
            conversation = self._current_conversation
        payload = json.dumps({"title": name})
        try:
            response = self.session.patch(
                url=f"https://chat.openai.com/backend-api/conversation/{conversation.conversation_id}",
                headers=get_headers_for_moderations(self.access_token, conversation.conversation_id),
                data=payload)
        except Exception as e:
            raise RequestsError(f"{type(e)}")

        if response.status_code == 200:
            logger.info(f"SUCCESS: Rename conversation, Response {response.json()}")
            conversation.conversation_name = name
            return response.json()["success"]
        if response.status_code == 403:
            self._update_cookies_again()
            self.rename_conversation_title(name, conversation)
        else:
            logger.warning(
                f"FAILED: Rename conversation, [Status Code] {response.status_code} | [Response Text]\n{response.text}")
            raise RequestsError(f"Requests {response.status_code}")

    def del_conversation_local(self, conversation_id: str):
        if not conversation_id:
            conversation_id = self._current_conversation.conversation_id
        path = Path(__file__).parent / "conversations" / f"{self.user['EMAIL']}" / f"{conversation_id}.json"
        if path.exists():
            path.unlink()
            logger.info(f"local {self.user['EMAIL']}/{conversation_id}.json deleted")

    @retry
    def del_conversation_remote(self, conversation_id: str | None):
        payload = json.dumps({"is_visible": False})
        if not conversation_id:
            conversation_id = self._current_conversation.conversation_id
        try:
            response = self.session.patch(
                url=f"https://chat.openai.com/backend-api/conversation/{conversation_id}",
                headers=get_headers_for_moderations(self.access_token, conversation_id),
                data=payload)
        except Exception as e:
            raise RequestsError(f"{type(e)}")

        if response.status_code == 200:
            logger.info(f"SUCCESS: Delete conversation {self.user['EMAIL']} {response.json()}")
            self._current_conversation = ConversationAgent(self.user)
            return response.json()["success"]
        elif response.status_code == 403:
            self._update_cookies_again()
            self.del_conversation_remote(conversation_id)
        else:
            raise RequestsError(f"Requests {response.status_code}")

    def del_all_conversations(self):
        for conversation_id in _list_local_conversations_id(self.user):
            self.del_conversation_remote(conversation_id)
            self.del_conversation_local(conversation_id)

    def __str__(self):
        return f"ChatgptAgent: \
        Current user: {self.user['EMAIL']}, \
        Current conversation {getattr(self._current_conversation, 'conversation_name', '')}"

    def __enter__(self):
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        self.is_keep_session = False
        with self.lock:
            for conversation in self.register_conversations:
                if conversation.is_echo:
                    self.fetch_conversation_history(conversation)
            save_cookies("chatgpt", self.user, self.cookies)
            if self.sl:
                self.sl.get_driver.quit()

    @retry
    def fetch_conversation_history(self, conversation: ConversationAgent | None):
        if not conversation:
            conversation = self._current_conversation
        try:
            response = self.session.get(
                url=f"https://chat.openai.com/backend-api/conversation/{conversation.conversation_id}",
                headers=get_headers_for_fetch_conversations(self.access_token, conversation.conversation_id))
        except Exception as e:
            raise RequestsError(f"{type(e)}")
        if response.status_code == 200:
            conversation.save_conversation_data(response.text)
        elif response.status_code == 403:
            logger.warning(f"FAILED: Fetch conversation history [Status Code] | {response.status_code}")
            self._update_cookies_again()
            self.fetch_conversation_history(conversation)
        else:
            raise RequestsError(f"Requests {response.status_code}")

    def quit(self):
        self.__exit__()

    def get_cookies(self):
        try:
            return get_cookies("chatgpt", self.user)
        except NoSuchCookiesException as e:
            logger.warning(f"{e.message}. Will use Selenium next.")
            self.sl = SeleniumRequests(self.user)
            self.sl.chatgpt_login()
            return get_cookies("chatgpt", self.user)

    def get_access_token(self) -> str | None:
        try:
            return get_access_token("chatgpt", self.user)
        except AccessTokenExpiredException as e:
            logger.warning(f"{e.message}. Will use Selenium next.")
            self.sl = SeleniumRequests(self.user)
            self.sl.chatgpt_login()
            return get_access_token("chatgpt", self.user)
        except Exception as e:
            logger.error(f"{type(e)}")
            return None

    def _update_cookies_for_requests(self, session: requests.Session) -> requests.Session:
        cookies_ = {cookie['name']: cookie['value'] for cookie in get_cookies("chatgpt", self.user)}
        cookiejar = cookiejar_from_dict(cookies_)
        session.cookies.update(cookiejar)
        return session

    def _prepare_session(self, proxies: dict[str, str] | None) -> requests.Session:
        session = requests.Session()
        if not proxies:
            proxies = {'http': "http://localhost:7890", 'https': "http://localhost:7890"}
        session.proxies.update(proxies)
        try:
            return self._update_cookies_for_requests(session)
        except NoSuchCookiesException as e:
            logger.warning(f"{e.message}")
            self.sl = SeleniumRequests(self.user)
            self.sl.chatgpt_login()
            return self._update_cookies_for_requests(session)

    # def _pass_moderations(self, conversation_id: str, prompt: str, message_id: str):
    #     try:
    #         self.session.post(
    #             "https://chat.openai.com/backend-api/moderations",
    #             headers=get_headers_for_moderations(self.access_token, conversation_id),
    #             data=get_request_moderations_playload(prompt, conversation_id, message_id))
    #     except AccessTokenExpiredException:
    #         return

    def _update_cookies_again(self, auth_again: bool = False):
        if not self.sl:
            self.sl = SeleniumRequests(self.user)
            self.sl.chatgpt_log_with_cookies()
        if auth_again:
            self.cookies, self.access_token = self.sl.fetch_access_token_cookies(auth_again)
            self.session.cookies.update(
                cookiejar_from_dict({cookie['name']: cookie['value'] for cookie in self.cookies}))
        else:
            self.cookies = self.sl.fetch_access_token_cookies(False)
            self.session.cookies.update(
                cookiejar_from_dict({cookie['name']: cookie['value'] for cookie in self.cookies}))

    @retry
    def _complete_conversation(self,
                               conversation: ConversationAgent,
                               headers: dict,
                               playload: str = None,
                               content_parts: str = "",
                               is_continue: bool = False) -> str:
        if is_continue:
            playload = get_continue_conversation_playload(conversation.conversation_id, conversation.current_node)
        try:
            response = self.session.post(
                "https://chat.openai.com/backend-api/conversation",
                headers=headers,
                data=playload,
                stream=True
            )
        except Exception as e:
            raise RequestsError(f"{type(e)}")

        if response.status_code == 200:
            if len(response.cookies) != 0:
                _update_cookies(self.session, response, self.cookies)
            iter_line = None
            for line in response.iter_lines():
                if line[7:11] != b"DONE" and line[7:11] == b'"mes':
                    iter_line = line
            try:
                last_data = re.search(r'data: (.*)', iter_line.decode("utf-8")).group(1)
                complete_data = json.loads(last_data)
                parts_start = last_data.find("parts") - 1
                end_turn_start = last_data.find("end_turn") - 1
                logger.info(f"SUCCESS: Get data from {conversation.user['EMAIL']}\n"
                            f"{last_data[parts_start:parts_start + 100]}"
                            "...\n"
                            f"{last_data[end_turn_start:end_turn_start + 100]}"
                            "...")
            except JSONDecodeError:
                logger.error(F"Encounter a JSONDecodeError, Check local conversation memorized")
                return iter_line
            if not conversation.conversation_id:
                conversation.conversation_id = complete_data["conversation_id"]
            if not is_continue:
                conversation.is_new_conversation = False
                conversation.is_echo = True
            conversation.current_node = complete_data["message"]["id"]
            content_parts += complete_data["message"]["content"]["parts"][0]
            if complete_data["message"]["end_turn"]:
                return content_parts
            else:
                return self._complete_conversation(conversation, headers, content_parts=content_parts, is_continue=True)
        elif response.status_code == 401:
            logger.warning(
                f"{self.user['EMAIL']} | [Status Code] {response.status_code} | [Response Text]\n{response.text}")
            raise AuthenticationTokenExpired(message=f"{self.user['EMAIL']} | [Status Code] {response.status_code}")
        elif response.status_code == 403:
            logger.warning(f"{self.user['EMAIL']} | [Status Code] {response.status_code}")
            if is_continue:
                self._update_cookies_again(False)
                return self._complete_conversation(conversation, headers, content_parts=content_parts, is_continue=True)
            else:
                raise Requests403Error(message=f"{self.user['EMAIL']} | [Status Code] {response.status_code}")
        elif response.status_code >= 500:
            logger.warning(
                f"{self.user['EMAIL']} | [Status Code] {response.status_code} | [Response Text] {response.text}")
            raise Requests500Error(message=f"Request {response.status_code}")
        else:
            logger.error(
                f"{self.user['EMAIL']} | [Status Code] {response.status_code} | [Response Text] {response.text}")
            raise RequestsError(message=f"{self.user['EMAIL']} | [Status Code] {response.status_code}")

    def ask_chat(self, prompt: str) -> str | None:
        with self.lock:
            message_id = str(uuid.uuid4())
            if not self._current_conversation.is_new_conversation:
                conversation_playload = get_request_conversation_playload(prompt,
                                                                          self._current_conversation.conversation_id,
                                                                          self._current_conversation.current_node,
                                                                          message_id)
                headers = get_headers_for_conversation(self.access_token, self._current_conversation.conversation_id)
            else:
                conversation_playload = get_new_conversation_playload(prompt,
                                                                      self._current_conversation.current_node,
                                                                      message_id)
                headers = get_headers_for_new_conversation(self.access_token)
            if not self._current_conversation.is_echo:
                self.register_conversations.add(self._current_conversation)
            if self.is_keep_session and not self.start_keep_session:
                self._keep_session()
            try:
                return self._complete_conversation(self._current_conversation, headers, conversation_playload)
            except Requests403Error as e:
                logger.warning(
                    f"{e.message}，{self._current_conversation.user['EMAIL']}| will call _complete_conversation again")
                self._update_cookies_again(False)
                return self._complete_conversation(self._current_conversation, headers, conversation_playload)
            except AuthenticationTokenExpired as e:
                logger.warning(
                    f"{e.message}，{self._current_conversation.user['EMAIL']}| will call _complete_conversation again")
                self.sl.chatgpt_login()
                self.cookies, self.access_token = self.sl.fetch_access_token_cookies(True)
                self.session.cookies.update(
                    cookiejar_from_dict({cookie['name']: cookie['value'] for cookie in self.cookies}))
                if not self._current_conversation.is_new_conversation:
                    headers = get_headers_for_conversation(self.access_token,
                                                           self._current_conversation.conversation_id)
                else:
                    headers = get_headers_for_new_conversation(self.access_token)
                return self._complete_conversation(self._current_conversation, headers, conversation_playload)


class ChatAgentPool(metaclass=SingletonMeta):
    def __init__(self, conversation_list: list[str, None] | None = None):
        if not conversation_list:
            conversation_list = [None, None, None]
        self.instances = [ChatgptAgent(u, conversation_list[i]) for i, u in enumerate(config["ACCOUNTS"])]
        self.count = -1

    def __enter__(self):
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        threads = []
        for ins in self.instances:
            t = threading.Thread(target=ins.quit)
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

    def quit(self):
        self.__exit__()

    def ask_chat(self, prompt: str):
        self.count += 1
        return self.instances[self.count % 3].ask_chat(prompt)
