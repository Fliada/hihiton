from src.app.agents.user_requests_agent.deepagent import deep_agent
import traceback
from langfuse.langchain import CallbackHandler

from loguru import logger

langfuse_handler = CallbackHandler()


def run_agent(user_query: str, thread_id: str = 1) -> dict:
    """Запускает супервизора с пользовательским запросом"""
    config = {"configurable": {"thread_id": thread_id}, "callbacks": [langfuse_handler]}
    try:
        result = deep_agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": user_query,
                    }
                ]
            },
            config=config,
        )
        logger.debug(result)
        return result
    except Exception as e:
        print(f"Ошибка в агенте: {e}")
        traceback.print_exc()
        return "Ошибка выполнения"
