import asyncio


import concurrent
from agents.web_search_agent.agent import web_search_agent


def run_web_search_agent(messages):
    async def run_request():
        return await web_search_agent.ainvoke(
            input=messages,
            # config={
            #     "configurable": {"thread_id": state["thread_id"]},
            #     "callbacks": [langfuse_handler],
            # },
        )

    def run_in_thread():
        try:
            result = asyncio.run(run_request())
            return result
        except Exception as e:
            print("Ошибка:", e)
            raise

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_in_thread)
        result = future.result()

    response = result["messages"][-1].content if result["messages"] else "Нет ответа"
    return response
