import json
import re
import threading
import uuid
from pathlib import Path

import time
from json import JSONDecodeError

import requests
from requests.utils import cookiejar_from_dict

from .auth_handler import get_cookies, LLM_PROVIDER, save_cookies, get_access_token
from .conversation import ConversationAgent
from .exceptions import NoSuchCookiesException, AccessTokenExpiredException, Requests403Error, Requests500Error, \
    RequestsError
from .headers import get_headers_for_moderations, get_headers_for_conversation, get_headers_for_new_conversation, \
    keep_session, get_headers_for_fetch_conversations
from .log_handler import logger
from .playload import get_request_conversation_playload, get_request_moderations_playload, \
    get_new_conversation_playload, get_continue_conversation_playload
from .use_selenium import SeleniumRequests
from .utils import SingletonMeta, retry


def _callback_mod(r, *args, **kwargs):
    if r.status_code == 200 and 'json' in r.headers['Content-Type']:
        try:
            moderation = r.json()
            if moderation["flagged"] or moderation["blocked"]:
                logger.warning(f"moderation flagged is {moderation['flagged']} blocked is {moderation['blocked']}")
        except Exception as e:
            logger.warning(f"some error happen {type(e)}")


def _update_cookies_for_requests(session: requests.Session, name: LLM_PROVIDER) -> requests.Session:
    cookies_ = {cookie['name']: cookie['value'] for cookie in get_cookies(name)}
    cookiejar = cookiejar_from_dict(cookies_)
    session.cookies.update(cookiejar)
    return session


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


def _list_local_conversations_id() -> list[str]:
    path = Path(__file__).parent / "conversations"
    conversation_id_list = []
    for file in path.iterdir():
        if file.suffix == '.json':
            conversation_id_list.append(file.stem)
    return conversation_id_list


class ChatgptAgent(metaclass=SingletonMeta):
    def __init__(self, is_keep_session: bool = False, proxies: dict[str, str] = None):
        self.sl = None
        self.session = self.prepare_session(proxies)
        self.cookies = get_cookies("chatgpt")
        self.access_token = self.get_access_token("chatgpt")
        self.is_keep_session = is_keep_session
        self.register_conversations = set()
        self.current_conversation = None
        self.start_keep_session = False
        self.is_echo = False
        self.lock = threading.Lock()

    def _keep_session(self):
        self.start_keep_session = True
        threading.Thread(target=self._wrapper_session_get).start()

    def _wrapper_session_get(self):
        while self.is_keep_session:
            time.sleep(300)
            response = self.session.get("https://chat.openai.com/api/auth/session",
                                        headers=keep_session(self.current_conversation.conversation_id))
            logger.info(f"keep_session get method return")
            _update_cookies(self.session, response, self.cookies)
            # self.session.cookies.update(
            #     cookiejar_from_dict({cookie['name']: cookie['value'] for cookie in self.cookies}))

    @retry
    def rename_conversation_title(self, name: str, conversation: ConversationAgent | None) -> bool:
        if not conversation:
            conversation = self.current_conversation
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
            self._update_cookies_onceagain()
            self.rename_conversation_title(name, conversation)
        else:
            logger.warning(
                f"FAILED: Rename conversation, [Status Code] {response.status_code} | [Response Text]\n{response.text}")
            raise RequestsError(f"Requests {response.status_code}")

    def del_conversation_local(self, conversation_id: str):
        if not conversation_id:
            conversation_id = self.current_conversation.conversation_id
        path = Path(__file__).parent / "conversations" / f"{conversation_id}.json"
        if path.exists():
            path.unlink()
            logger.info(f"local {conversation_id}.json deleted")

    @retry
    def del_conversation_remote(self, conversation_id: str | None):
        payload = json.dumps({"is_visible": False})
        if not conversation_id:
            conversation_id = self.current_conversation.conversation_id
        try:
            response = self.session.patch(
                url=f"https://chat.openai.com/backend-api/conversation/{conversation_id}",
                headers=get_headers_for_moderations(self.access_token, conversation_id),
                data=payload)
        except Exception as e:
            raise RequestsError(f"{type(e)}")

        if response.status_code == 200:
            logger.info(f"SUCCESS: Delete conversation {response.json()}")
            self.current_conversation = ConversationAgent(session=self.session)
            return response.json()["success"]
        elif response.status_code == 403:
            self._update_cookies_onceagain()
            self.del_conversation_remote(conversation_id)
        else:
            raise RequestsError(f"Requests {response.status_code}")

    def del_all_conversations(self):
        for conversation_id in _list_local_conversations_id():
            self.del_conversation_remote(conversation_id)
            self.del_conversation_local(conversation_id)

    def __str__(self):
        return f"ChatgptAgent: Current conversation {self.current_conversation.conversation_name}"

    def __enter__(self):
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        self.is_keep_session = False
        if self.is_echo:
            for conversation in self.register_conversations:
                self.fetch_conversation_history(conversation)
            save_cookies("chatgpt", self.cookies)
        if self.sl:
            self.sl.get_driver.quit()

    @retry
    def fetch_conversation_history(self, conversation: ConversationAgent | None):
        if not conversation:
            conversation = self.current_conversation
        if self.is_echo:
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
                self._update_cookies_onceagain()
                self.fetch_conversation_history(conversation)
            else:
                raise RequestsError(f"Requests {response.status_code}")

    def quit(self):
        self.__exit__()

    def get_access_token(self, name: LLM_PROVIDER) -> str | None:
        try:
            return get_access_token(name)
        except AccessTokenExpiredException:
            logger.warning(f"AccessToken Expired. Will use Selenium next.")
            self.sl = SeleniumRequests()
            self.sl.chatgpt_login()
            return get_access_token("chatgpt")
        except Exception as e:
            logger.error(f"{type(e)}")
            return None

    def prepare_session(self, proxies: dict[str, str] | None) -> requests.Session:
        session = requests.Session()
        if not proxies:
            proxies = {'http': "http://localhost:7890", 'https': "http://localhost:7890"}
        session.proxies.update(proxies)
        try:
            return _update_cookies_for_requests(session, "chatgpt")
        except NoSuchCookiesException as e:
            logger.warning(f"Not fetch cookies yet, start use selenium {e.message}")
            self.sl = SeleniumRequests()
            self.sl.chatgpt_login()
            return _update_cookies_for_requests(session, "chatgpt")

    def _pass_moderations(self, conversation_id: str, prompt: str, message_id: str):
        try:
            self.session.post(
                "https://chat.openai.com/backend-api/moderations",
                headers=get_headers_for_moderations(self.access_token, conversation_id),
                hooks={'response': _callback_mod},
                data=get_request_moderations_playload(prompt, conversation_id, message_id))
        except AccessTokenExpiredException:
            return

    def _update_cookies_onceagain(self, update_access_token: bool = False):
        if self.sl:
            cookies_ = self.sl.from_session_cookies()
            self.cookies = cookies_
            self.session.cookies.update(
                cookiejar_from_dict({cookie['name']: cookie['value'] for cookie in cookies_}))
        else:
            self.sl = SeleniumRequests()
            self.sl.chatgpt_log_with_cookies()
            if update_access_token:
                self.access_token = self.sl.fetch_access_token()
            _update_cookies_for_requests(self.session, "chatgpt")

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
                finish_details_start = last_data.find("finish_details") - 1
                logger.info("SUCCESS: Get data\n"
                            f"{last_data[finish_details_start:finish_details_start + 100]}"
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
            logger.warning(f"[Status Code] {response.status_code} | [Response Text] {response.text}")
            raise AccessTokenExpiredException(message=f"[Status Code] {response.status_code}")
        elif response.status_code == 403:
            logger.warning(f"[Status Code] {response.status_code}")
            if is_continue:
                self._update_cookies_onceagain()
                return self._complete_conversation(conversation, headers, content_parts=content_parts, is_continue=True)
            else:
                raise Requests403Error(message=f"[Status Code] {response.status_code}")
        elif response.status_code >= 500:
            logger.warning(f"[Status Code] {response.status_code} | [Response Text] {response.text}")
            raise Requests500Error(message=f"Request {response.status_code}")
        else:
            logger.error(f"[Status Code] {response.status_code} | [Response Text] {response.text}")
            raise RequestsError(message=f"Request {response.status_code}")

    def ask_chat(self,
                 prompt: str,
                 conversation: ConversationAgent,
                 pass_moderation: bool = False,
                 ) -> str | None:
        with self.lock:
            self.current_conversation = conversation
            message_id = str(uuid.uuid4())
            if not conversation.is_new_conversation:
                conversation_playload = get_request_conversation_playload(prompt,
                                                                          conversation.conversation_id,
                                                                          conversation.current_node,
                                                                          message_id)
                headers = get_headers_for_conversation(self.access_token, conversation.conversation_id)
            else:
                conversation_playload = get_new_conversation_playload(prompt,
                                                                      conversation.current_node,
                                                                      message_id)
                headers = get_headers_for_new_conversation(self.access_token)
            if not conversation.is_echo:
                self.register_conversations.add(conversation)
            if pass_moderation:
                threading.Thread(target=self._pass_moderations,
                                 args=(conversation.conversation_id, prompt, message_id)).start()
            if self.is_keep_session and not self.start_keep_session:
                self._keep_session()
            try:
                return self._complete_conversation(conversation, headers, conversation_playload)
            except AccessTokenExpiredException as e:
                logger.warning(f"{e.message}，update cookies, call _complete_conversation() again")
                self._update_cookies_onceagain(True)
                if not conversation.is_new_conversation:
                    headers = get_headers_for_conversation(self.access_token, conversation.conversation_id)
                else:
                    headers = get_headers_for_new_conversation(self.access_token)
                return self._complete_conversation(conversation, headers, conversation_playload)
            except Requests403Error as e:
                logger.warning(f"{e.message}，update cookies, call _complete_conversation() again")
                self._update_cookies_onceagain()
                return self._complete_conversation(conversation, headers, conversation_playload)
