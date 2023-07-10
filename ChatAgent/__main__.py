from .server import FakeChatgptApi

# these ids only work for author, replace them with your ids in different accounts
lista = ["005f3d9f-941f-459c-b801-e1f599fe2478",
         "6b73616c-88c9-4d80-a197-0d6179b48096",
         "b709b958-8291-4e76-9023-3142d0ae7b43"]
fake_chatgpt_api = FakeChatgptApi(lista)
fake_chatgpt_api.run_server()
