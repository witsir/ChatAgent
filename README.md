## 介绍
首先你需要梯子，梯子已经将 openai.com 等网站设置为走proxy
套web端的 chat.openai.com,
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
echo "EMAIL=your email" > .env
echo "PASSWORD=your password" >> .env
```
```python
from ChatAgent import ChatgptAgent, ConversationAgent
chat_agent =ChatgptAgent()
conversation = ConversationAgent(chat_agent.session)
print(chat_agent.ask_chat("""写一个女权小作文""",conversation))
```
