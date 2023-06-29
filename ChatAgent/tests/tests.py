# import requests

# from auth_handler import get_access_token, get_cookies


# from conversation import show_prose_conversation, ConversationAgent
# from use_requests import ChatgptAgent

from playload import get_request_moderations_playload, get_request_conversation_playload
########## test Config
# if __name__ == '__main__':
#     from ChatAgent.config import config
#     print(config["USER_AGENT_UA"]["version_main"])


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
if __name__ == '__main__':
    from ChatAgent.conversation import ConversationAgent
    from ChatAgent.use_requests import ChatgptAgent
    with ChatgptAgent() as chat_agent:
        conversation = ConversationAgent(chat_agent.session)
        # conversation = ConversationAgent(chat_agent.session)
        # chat_agent.del_all_conversations()
        print(chat_agent.ask_chat("说一个关于牛奶的笑话", conversation))
        print(chat_agent.ask_chat("说一个关于小羊的笑话", conversation))


########## test SeleniumRequests
# if __name__ == '__main__':
#     from use_selenium import SeleniumRequests
#
#     s = SeleniumRequests()

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
