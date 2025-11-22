from os import getenv
from dotenv import load_dotenv
from langfuse import Langfuse
from langchain_openai import ChatOpenAI

load_dotenv()

langfuse = Langfuse(
    secret_key=getenv("LANGFUSE_SECRET_KEY"),
    public_key=getenv("LANGFUSE_PUBLIC_KEY"),
    host=getenv("LANGFUSE_HOST"),
)

llm = ChatOpenAI(
    base_url=getenv("MODEL_API_BASE"),
    model=getenv("MODEL"),
    api_key="EMPTY",
)
