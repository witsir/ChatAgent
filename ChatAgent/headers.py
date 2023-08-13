from .config import config


def get_headers_for_conversation(access_token: str, conversation_id: str) -> dict:
    return {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}',
        'Accept': 'text/event-stream',
        # 'Referer': f'https://chat.openai.com/c/{conversation_id}',
        # 'Origin': 'https://chat.openai.com',
        'User-Agent': config["USER_AGENT_UA"]["User-Agent"],
        'Sec-Ch-Ua': config["USER_AGENT_UA"]["Sec-Ch-Ua"]
    }


def get_headers_for_new_conversation(access_token: str) -> dict:
    return {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}',
        'Accept': 'text/event-stream',
        # 'Referer': f'https://chat.openai.com/?model=text-davinci-002-render-sha',
        # 'Origin': 'https://chat.openai.com',
        'User-Agent': config["USER_AGENT_UA"]["User-Agent"],
        'Sec-Ch-Ua': config["USER_AGENT_UA"]["Sec-Ch-Ua"]
    }


def get_headers_for_moderations(access_token: str, conversation_id: str) -> dict:
    return {
        'Content-Type': 'application/json',
        'Accept': "*/*",
        'Authorization': f'Bearer {access_token}',
        # 'Referer': f'https://chat.openai.com/c/{conversation_id}',
        # 'Origin': 'https://chat.openai.com',
        'User-Agent': config["USER_AGENT_UA"]["User-Agent"],
        'Sec-Ch-Ua': config["USER_AGENT_UA"]["Sec-Ch-Ua"]
    }


def get_headers_for_fetch_conversation(access_token: str, conversation_id: str) -> dict:
    return {
        'Content-Type': 'application/json',
        'Accept': "*/*",
        'Authorization': f'Bearer {access_token}',
        # 'Referer': f'https://chat.openai.com/c/{conversation_id}',
        'User-Agent': config["USER_AGENT_UA"]["User-Agent"],
        'Sec-Ch-Ua': config["USER_AGENT_UA"]["Sec-Ch-Ua"]
    }


def get_headers_for_fetch_conversation_list(access_token: str) -> dict:
    return {
        'Content-Type': 'application/json',
        'Accept': "*/*",
        'Authorization': f'Bearer {access_token}',
        # 'Referer': 'https://chat.openai.com/?model=text-davinci-002-render-sha',
        'User-Agent': config["USER_AGENT_UA"]["User-Agent"],
        'Sec-Ch-Ua': config["USER_AGENT_UA"]["Sec-Ch-Ua"]
    }


def keep_session(conversation_id: str) -> dict:
    return {
        'Accept': "*/*",
        # 'Referer': f'https://chat.openai.com/c/{conversation_id}',
        'User-Agent': config["USER_AGENT_UA"]["User-Agent"],
        'Sec-Ch-Ua': config["USER_AGENT_UA"]["Sec-Ch-Ua"]
    }
