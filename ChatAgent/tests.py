import requests

from auth_handler import get_access_token, get_cookies
from config import *

from conversation import show_prose_conversation, ConversationAgent
from use_requests import ChatgptAgent

from playload import get_request_moderations_playload, get_request_conversation_playload
########## test dotenv
# print(EMAIL)

########## test auth_handler
# print(get_access_token())
# print(get_cookies("chatgpt"))

########## test conversation_handler
# print(show_prose_conversation("64ba5915-d034-40f7-95c7-f9f63b91982c"))

# print(get_request_moderations_playload('','',''))
# print(get_request_conversation_playload('','',''))

########### test conversation
# session = requests.session()
# con = ConversationAgent(session, "64ba5915-d034-40f7-95c7-f9f63b91982c")
# print(con)

########## test ChatgptAgent
from use_selenium import SeleniumRequests

with ChatgptAgent() as chat_agent:
    conversation = ConversationAgent(chat_agent.session, "2659f633-46bf-46a5-a693-33c40e94b7b0")
    # conversation = ConversationAgent(chat_agent.session)
    print(chat_agent.ask_chat("他们是国有企业吗", conversation))


# import datetime
# #
# timestamp = [1687797453, 1685207163, 1684768427]
# for i in timestamp:
#     dt = datetime.datetime.fromtimestamp(i)
#     formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
#
#     print(formatted_time)
# session = requests.session()
# for var in "ab":
#     session.get(f"https://httpbin.org/cookies/set/{var}/{var*10}")
#
# cookies = session.cookies
# for i in cookies:
#     print(vars(i))

