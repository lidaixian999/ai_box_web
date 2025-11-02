from fastapi import Depends
from app.services.ai_service import AIService
from app.services.schedule_service import ScheduleService
from app.services.document_service import DocumentService

def get_ai_service() -> AIService:
    return AIService()

def get_schedule_service(ai_service: AIService = Depends(get_ai_service)) -> ScheduleService:
    return ScheduleService(ai_service=ai_service)

def get_document_service() -> DocumentService:
    """获取文档服务实例（延迟初始化）"""
    try:
        return DocumentService()
    except Exception as e:
        # 如果初始化失败，记录错误但不阻止路由注册
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"文档服务初始化失败: {str(e)}")
        raise