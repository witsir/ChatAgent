########## test Config
# if __name__ == '__main__':
#     from ChatAgent.config import config
#     for i in config["ACCOUNTS"]:
#         print(i["EMAIL"])
#         print(i["PASSWORD"])
#     print(config["USER_AGENT_UA"]["version_main"])


########## test auth_handler
# if __name__ == '__main__':
# from ChatAgent.config import config
# from ChatAgent.auth_handler import get_access_token, get_cookies
#
# print(get_access_token("chatgpt", config["ACCOUNTS"][0]))
# print(get_cookies("chatgpt", config["ACCOUNTS"][0]))

########## test conversation
# if __name__ == '__main__':
#     from ChatAgent.conversation import ConversationAgent
#     from ChatAgent.config import config
#
#     c = ConversationAgent(config['ACCOUNTS'][0], "9740caca-5ef6-4014-8c98-ea5f02dbac69")
# print(c.conversation_prose)
# print(c)
# print(c.is_new_conversation)
# print(c.is_echo)

########### test conversation
# session = requests.session()
# con = ConversationAgent(session, "64ba5915-d034-40f7-95c7-f9f63b91982c")
# print(con)

########## test FakeChatgptApi
# if __name__ == '__main__':
# from ChatAgent import FakeChatgptApi

# these ids only work for author, replace them with your ids in different accounts
# lista = ["005f3d9f-941f-459c-b801-e1f599fe2478",
#          "6b73616c-88c9-4d80-a197-0d6179b48096",
#          "b709b958-8291-4e76-9023-3142d0ae7b43"]
# fake_chatgpt_api = FakeChatgptApi(lista)
# fake_chatgpt_api.run_server()

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
