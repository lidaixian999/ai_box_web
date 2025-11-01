# routers/tarot.py
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from app.services.ai_service import AIService
from app.services.tarot_service import TarotService
from app.dependencies import get_ai_service
from pydantic import BaseModel, Field

router = APIRouter()
logger = logging.getLogger(__name__)


class QuestionRequest(BaseModel):
    question: str = Field(..., description="用户的问题", min_length=1)


class TarotCard(BaseModel):
    name: str
    position: str
    interpretation: str


class TarotResponse(BaseModel):
    cards: List[TarotCard]
    overall_interpretation: str


def get_tarot_service(ai_service: AIService = Depends(get_ai_service)) -> TarotService:
    """获取塔罗牌服务实例"""
    return TarotService(ai_service)


@router.post("/divine", response_model=TarotResponse)
async def divine_tarot_cards(
    request: QuestionRequest,
    tarot_service: TarotService = Depends(get_tarot_service)
):
    """
    直接进行塔罗牌占卜，根据用户问题抽取三张塔罗牌并进行解读

    Args:
        request: 包含用户问题的请求体

    Returns:
        塔罗牌解读结果
    """
    try:
        # 直接抽取塔罗牌并解读
        result = tarot_service.divine_cards(request.question)

        return {
            "cards": result["cards"],
            "overall_interpretation": result["overall_interpretation"]
        }

    except Exception as e:
        logger.error(f"塔罗牌占卜时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"占卜失败: {str(e)}")
