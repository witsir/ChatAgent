## 介绍
首先你需要梯子，梯子已经将 openai.com,huggingface.co 等 PREFIX 设置为走proxy。
然后你使用的浏览器是 chrome，版本越新越好。

## 原理
本包是通过 selenium获取web端 chat.openai.com accessToken 和 Cookies 后,然后使用 requests 库将其转换为 聊天API。

> TODO 后面会增加其他网页对话模型

## 安装
```bash
git clone git@github.com:witsir/ChatAgent.git
#切换至 pyproject.toml 所在目录 
cd ChatAgent
pip install -e .
```

## 使用
```bash
# 进入子目录,创建 .env 文件保存 你的EMAIL和PASSWORD
cd ChatAgent
# 这是一个列表，你可以添加多个账号
echo ACCOUNTS=\''[{"EMAIL":"your email","PASSWORD":"your password"}]'\' > .env
# 如果你需要使用 selenium 的 driver 是 headless，请设置
echo DEBUG=false >> .env
```
```python
# 简单的一个对话
from ChatAgent import ChatAgentPool
chat_agent_pool =ChatAgentPool()
print(chat_agent_pool.ask_chat("""tell me joke"""))


# 在 http://localhost:5050 上运行模仿chatgpt api 服务 
from ChatAgent import FakeChatgptApi
fake_chatgpt_api = FakeChatgptApi()
fake_chatgpt_api.run_server()
```
