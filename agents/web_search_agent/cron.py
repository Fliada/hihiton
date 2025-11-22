from agents.web_search_agent.tools import get_bank_and_products
from agents.web_search_agent.run import run_web_search_agent

for message in get_bank_and_products():
    messages = [{"role": "user", "content": message}]
    print(messages)
    print(run_web_search_agent({"messages": messages}))
