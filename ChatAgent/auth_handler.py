import os
from datetime import datetime, timezone
import json
from json import JSONDecodeError

from pathlib import Path
from typing import Literal

from .exceptions import NoSuchCookiesException, AccessTokenExpiredException
from .log_handler import logger

LLM_PROVIDER = Literal["chatgpt", "bard"]


def get_access_token(name: LLM_PROVIDER) -> str:
    if name == "chatgpt":
        path = Path(__file__).parent / "ChatgptAuth" / "accessToken.json"
        if path.exists():
            with open(path, 'r') as f:
                access_token = json.load(f)
                expires = datetime.strptime(access_token['expires'], '%Y-%m-%dT%H:%M:%S.%fZ').replace(
                    tzinfo=timezone.utc)
                if datetime.now(timezone.utc) < expires:
                    return access_token["accessToken"]
                else:
                    raise AccessTokenExpiredException("AccessToken Expired")
        else:
            raise AccessTokenExpiredException("AccessToken not Found")


def save_access_token(name: LLM_PROVIDER, token_str: str):
    if name == "chatgpt":
        try:
            path = Path(__file__).parent / "ChatgptAuth"
            if not path.exists():
                path.mkdir()
                path = path / "accessToken.json"
                with open(path, 'w') as f:
                    f.write(token_str)
                    logger.info(f"success in saving {name} accessToken.json")
        except Exception as e:
            logger.error(f"failed in saving {name} accessToken.json\n", e)
    if name == "bard":
        ...


def get_cookies(name: LLM_PROVIDER) -> list[dict] | None:
    if name == "chatgpt":
        path = Path(__file__).parent / "ChatgptAuth" / "cookies.json"
        if path.exists() and os.path.getsize(path) != 0:
            with open(path, 'r') as f:
                try:
                    return json.load(f)
                except JSONDecodeError as e:
                    logger.warning(f"decode Json cookies failed {e.msg}")
                    return None
        else:
            raise NoSuchCookiesException()


def save_cookies(name: LLM_PROVIDER, cookies: list[dict]):
    if name == "chatgpt":
        try:
            path = Path(__file__).parent / "ChatgptAuth"
            if not path.exists():
                path.mkdir()
            path = path / "cookies.json"
            with open(path, 'w') as f:
                json.dump(cookies, f)
                logger.info(f"success in saving {name} cookies.json")
        except Exception as e:
            logger.error(f"failed in saving {name} cookies.json\n", e)


def save_next_data(name: LLM_PROVIDER, next_data: str):
    if name == "chatgpt":
        try:
            path = Path(__file__).parent / "ChatgptAuth"
            if not path.exists():
                path.mkdir()
                path = path / "__NEXT_DATA__.json"
                with open(path, 'w') as f:
                    f.write(next_data)
                    logger.info(f"success in saving {name} __NEXT_DATA__.json")
        except Exception as e:
            logger.error(f"failed in saving {name} __NEXT_DATA__.json\n", e)


def get_next_data(name: LLM_PROVIDER) -> str | None:
    if name == "chatgpt":
        try:
            path = Path(__file__).parent / "ChatgptAuth" / "__NEXT_DATA__.json"
            with open(path, 'r') as f:
                return json.load(f)["buildId"]
        except Exception as e:
            logger.error(f"get  {name} __NEXT_DATA__.json failed error is {type(e)}")
