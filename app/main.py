import os
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.routers import ai
from app.dependencies import get_ai_service

app = FastAPI(
    title="AI工具箱后端",
    description="基于Ollama的AI对话服务",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制为特定的源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import logging

logger = logging.getLogger(__name__)

# 添加验证错误处理器以查看详细错误
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body = None
    if exc.body:
        if isinstance(exc.body, bytes):
            body = exc.body.decode('utf-8', errors='ignore')
        else:
            body = str(exc.body)
    
    # 记录详细的验证错误到日志
    logger.error(f"验证错误: {exc.errors()}")
    logger.error(f"请求体: {body}")
    logger.error(f"请求URL: {request.url}")
    logger.error(f"请求方法: {request.method}")
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "body": body,
            "message": "请求验证失败，请检查请求体格式。需要发送JSON格式: {\"question\": \"你的问题\"}"
        }
    )

# 包含路由
app.include_router(ai.router, prefix="/api/ai", tags=["AI服务"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", 8000)),
        reload=True
    )