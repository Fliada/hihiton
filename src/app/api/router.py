from fastapi import APIRouter, HTTPException
from app.api.models import ChatResponse, ChatRequest


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(data: ChatRequest):
    result = run_agent(data.message)

    return ChatResponse(
        text=result["text"],
        send_csv=result.get("csv", False),
        send_png=result.get("png", False)
    )
