import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from app.services.ai_service import AIService
from app.dependencies import get_ai_service
from pydantic import BaseModel, Field

router = APIRouter()
logger = logging.getLogger(__name__)

class QuestionRequest(BaseModel):
    question: str = Field(..., description="用户的问题", min_length=1)

class AnswerResponse(BaseModel):
    answer: str

@router.post("/ask", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest, ai_service: AIService = Depends(get_ai_service)):
    """处理用户提问"""
    # 记录解析后的请求
    logger.info(f"收到问题: {request.question}")
    
    answer = ai_service.ask_question(request.question)
    return {"answer": answer}