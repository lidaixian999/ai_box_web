from fastapi import Depends
from app.services.ai_service import AIService
from app.services.schedule_service import ScheduleService

def get_ai_service() -> AIService:
    return AIService()

def get_schedule_service(ai_service: AIService = Depends(get_ai_service)) -> ScheduleService:
    return ScheduleService(ai_service=ai_service)