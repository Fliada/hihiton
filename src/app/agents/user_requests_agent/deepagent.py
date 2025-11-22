from deepagents import create_deep_agent
from dotenv import load_dotenv
from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.memory import MemorySaver

from app.tools.user_requests_parse import get_user_request_data_from_db
from app.infra.llm.client import llm


tools = [get_user_request_data_from_db]

system_prompt = """# Ты - агент помощник по работе с аналитикой по банковским продуктам в компании "Сбербанк".
# Твоя задача отвечать на вопросы пользователей.

# Твои основные функции:
1) вызывать функцию для получения данных из базы. В результате ты получишь списки id. Выведи их в ответ пользователю.

Правила получения данных:
1) вызови функцию СТРОГО один раз!
"""

langfuse_handler = CallbackHandler()
load_dotenv()
config = {
    "callbacks": [langfuse_handler],
    "configurable": {"thread_id": "e90165add92568e538fad7255ea203e3f2a677c6"},
}

checkpointer = MemorySaver()
deep_agent = create_deep_agent(
    model=llm,
    tools=tools,
    system_prompt=system_prompt,
    checkpointer=checkpointer,
)
