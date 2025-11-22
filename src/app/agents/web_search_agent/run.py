import asyncio


import concurrent
from src.app.agents.web_search_agent.agent import web_search_agent


def run_web_search_agent(messages):
    result = web_search_agent.invoke(
            input=messages,
            # config={
            #     "configurable": {"thread_id": state["thread_id"]},
            #     "callbacks": [langfuse_handler],
            # },
        )
    response = result["messages"][-1].content if result["messages"] else "Нет ответа"
    return response
