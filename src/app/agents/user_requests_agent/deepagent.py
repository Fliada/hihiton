from deepagents import create_deep_agent, CompiledSubAgent
from dotenv import load_dotenv
from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.memory import MemorySaver

from src.app.tools.user_requests_parse import get_user_request_data_from_db
# from app.tools.get_report import get_report
from src.app.infra.llm.client import llm
from src.app.agents.web_search_agent.agent import web_search_agent  

# tools = [get_user_request_data_from_db, get_report]

tools = [get_user_request_data_from_db]

system_prompt = """# Ты - агент помощник по работе с аналитикой по банковским продуктам в компании "Сбербанк".
# Твоя задача отвечать на вопросы пользователей.

# Твои основные функции:
1) Вызывать инструмент для получения заданных данных из базы данных
2) Написать вывод по предоставленной информации. 
3) Предоставь источники данных (ссылки).

Правила составления ответа пользователю:
1) обязательно выводи ответ в формате json с полями text - ответ агента, csv - True (если бы свормирован отчет), png - True (если был построен график) 

У тебя есть субагент для сбора информации в интернете, обращайся к нему, когда не можешь найти информацию в базе данных. 
Он должен найти информацию, а затем добавить ее в базу. После этого получи данные из базы данных еще раз.
"""

subagent = CompiledSubAgent(
    name='web-search',
    description="Агент для поиска информации в интернете",
    runnable=web_search_agent
)

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
    subagents=[subagent]
)
