from dotenv import load_dotenv
from src.app.agents.web_search_agent.agent import web_search_agent

from langfuse.langchain import CallbackHandler
langfuse_handler = CallbackHandler()
load_dotenv()
config = {
    "callbacks": [langfuse_handler],
    "configurable": {"thread_id": "e90165add92568e538fad7255ea203e3f2a677c6"},
}

def run_web_search_agent(messages):
    result = web_search_agent.invoke(
            input=messages,
            config={
                "callbacks": [langfuse_handler],
            },
        )
    response = result["messages"][-1].content if result["messages"] else "Нет ответа"
    return response
