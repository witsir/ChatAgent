import json
import uuid


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
        "action": "next",
        "conversation_id": conversation_id,
        "history_and_training_disabled": False,
        "messages": [
            {
                "id": message_id,
                "author": {"role": "user"},
                "content": {"content_type": "text",
                            "parts": [str(prompt)]},
            }
        ],
        "parent_message_id": parent_message_id,
        "model": "text-davinci-002-render-sha",
        "timezone_offset_min": -480
    })


def get_new_conversation_playload(prompt: str,
                                  parent_message_id: str,
                                  message_id: str) -> str:
    return json.dumps({
        "action": "next",
        "history_and_training_disabled": False,
        "messages": [
            {
                "id": message_id,
                "author": {"role": "user"},
                "content": {"content_type": "text",
                            "parts": [str(prompt)]},
            }
        ],
        "parent_message_id": parent_message_id,
        "model": "text-davinci-002-render-sha",
        "timezone_offset_min": -480
    })
