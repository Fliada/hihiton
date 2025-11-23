from fastapi import APIRouter, HTTPException
from app.api.models import ChatResponse, ChatRequest


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(data: ChatRequest):
    #TODO: сделать точку входа в агента
    response = run_agent(message=data.message)
    return ChatResponse(response=response)
