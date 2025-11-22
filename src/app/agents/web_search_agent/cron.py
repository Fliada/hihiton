from src.app.agents.web_search_agent.tools import get_bank_and_products
from src.app.agents.web_search_agent.run import run_web_search_agent


def get_raw_data():
    
    raw_data = []
    
    for query in get_bank_and_products():
        
        message = list(query.keys())[0]
        ids = list(query.values())[0]
        
        print(message, ids)
        
        messages = [{"role": "user", "content": message}]
        
        result = run_web_search_agent({"messages": messages})
        print('-'*15)
        print(result)


get_raw_data()