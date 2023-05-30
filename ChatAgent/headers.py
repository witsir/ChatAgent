from auth_handler import get_access_token


def get_headers_for_conversation(conversation_id: str) -> dict:
    access_token = get_access_token("chatgpt")
    return {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}',
        'Accept': 'text/event-stream',
        'Referer': f'https://chat.openai.com/c/{conversation_id}',
        'Origin': 'https://chat.openai.com',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
        'Sec-Ch-Ua': '"Google Chrome";v="113", "Chromium";v="113", "Not-A.Brand";v="24"'
    }


def get_headers_for_new_conversation() -> dict:
    access_token = get_access_token("chatgpt")
    return {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}',
        'Accept': 'text/event-stream',
        'Referer': f'https://chat.openai.com/?model=text-davinci-002-render-sha',
        'Origin': 'https://chat.openai.com',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
        'Sec-Ch-Ua': '"Google Chrome";v="113", "Chromium";v="113", "Not-A.Brand";v="24"'
    }


def get_headers_for_moderations(conversation_id: str) -> dict:
    access_token = get_access_token("chatgpt")
    return {
        'Content-Type': 'application/json',
        'Accept': "*/*",
        'Authorization': f'Bearer {access_token}',
        'Referer': f'https://chat.openai.com/c/{conversation_id}',
        'Origin': 'https://chat.openai.com',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
        'Sec-Ch-Ua': '"Google Chrome";v="113", "Chromium";v="113", "Not-A.Brand";v="24"'
    }


def keep_session(conversation_id: str) -> dict:
    return {
        'Accept': "*/*",
        'Referer': f'https://chat.openai.com/c/{conversation_id}',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
        'Sec-Ch-Ua': '"Google Chrome";v="113", "Chromium";v="113", "Not-A.Brand";v="24"'
    }
