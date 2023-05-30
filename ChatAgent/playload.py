import json


def get_request_moderations_playload(prompt: str, conversation_id: str, message_id: str) -> str:
    return json.dumps({
        "conversation_id": conversation_id,
        "input": prompt,
        "message_id": message_id,
        "model": "text-moderation-playground"
    })


def get_request_conversation_playload(prompt: str,
                                      conversation_id: str,
                                      parent_message_id: str,
                                      message_id: str) -> str:
    return json.dumps({
        'action': 'next',
        'messages': [{'id': message_id,
                      'author': {'role': 'user'},
                      'content': {'content_type': 'text', 'parts': [prompt]},
                      'metadata': {}}],
        'conversation_id': conversation_id,
        'parent_message_id': parent_message_id,
        'model': 'text-davinci-002-render-sha',
        'timezone_offset_min': -480,
        'history_and_training_disabled': False,
        'arkose_token': None,
        'supports_modapi': False
    })


def get_new_conversation_playload(prompt: str,
                                  parent_message_id: str,
                                  message_id: str) -> str:
    return json.dumps({
        'action': 'next',
        'messages': [{'id': message_id,
                      'author': {'role': 'user'},
                      'content': {'content_type': 'text', 'parts': [prompt]},
                      'metadata': {}}],
        'parent_message_id': parent_message_id,
        'model': 'text-davinci-002-render-sha',
        'timezone_offset_min': -480,
        'history_and_training_disabled': False,
        'arkose_token': None,
        'supports_modapi': False
    })
