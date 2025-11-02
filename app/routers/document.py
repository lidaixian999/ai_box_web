import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.services.document_service import DocumentService
from app.dependencies import get_document_service
from pydantic import BaseModel, Field

router = APIRouter()
logger = logging.getLogger(__name__)


class DocumentQueryRequest(BaseModel):
    """文档查询请求模型"""
    query: str = Field(..., description="查询问题或功能描述", min_length=1, example="如何使用GPIO驱动LED？")
    mode: str = Field("auto", description="查询模式: auto(自动检测), qa(问答), code(代码生成)", example="auto")
    k: int = Field(3, description="检索的文档数量，范围：1-10", ge=1, le=10, example=3)


class DocumentQueryResponse(BaseModel):
    """文档查询响应模型"""
    answer: str = Field(..., description="AI生成的答案")
    mode: str = Field(..., description="实际使用的查询模式")
    retrieved_docs_count: int = Field(0, description="实际检索到的文档数量")


class RebuildIndexResponse(BaseModel):
    """重建索引响应模型"""
    message: str = Field(..., description="操作结果消息")
    chunks_count: int = Field(0, description="文档块数量")


class IndexStatusResponse(BaseModel):
    """索引状态响应模型"""
    index_loaded: bool = Field(..., description="索引是否已加载")
    index_dir: str = Field(..., description="索引目录路径")
    docs_root: str = Field(..., description="文档根目录路径")
    knowledge_dirs: list[str] = Field(..., description="知识库目录列表")
    embed_model: str = Field(..., description="嵌入模型名称")
    gen_model: str = Field(..., description="生成模型名称")


@router.post("/query", response_model=DocumentQueryResponse)
async def query_documents(
    request: DocumentQueryRequest,
    document_service: DocumentService = Depends(get_document_service)
):
    """
    查询文档（问答或代码生成）
    
    根据查询内容分析文档（demos 和 drivers 目录），支持三种模式：
    - **qa 模式**：问答模式，返回文档中的相关知识解答
    - **code 模式**：代码生成模式，根据文档内容生成代码示例
    - **auto 模式**：自动检测，根据查询内容自动判断是问答还是代码生成
    
    Args:
        request: 查询请求，包含：
            - query: 查询问题或功能描述
            - mode: 查询模式（auto/qa/code），默认为 auto
            - k: 检索的文档数量（1-10），默认为 3
    
    Returns:
        DocumentQueryResponse: 包含答案、使用的模式和检索的文档数量
        
    Raises:
        HTTPException: 当查询失败时返回 500 错误
    """
    try:
        logger.info(f"收到文档查询: query={request.query}, mode={request.mode}, k={request.k}")
        
        # 验证模式参数
        if request.mode not in ["auto", "qa", "code"]:
            raise HTTPException(
                status_code=400,
                detail=f"无效的查询模式: {request.mode}，支持的模式: auto, qa, code"
            )
        
        # 自动检测模式
        if request.mode == "auto":
            mode = "code" if document_service.is_code_request(request.query) else "qa"
            logger.info(f"自动检测模式为: {mode}")
        else:
            mode = request.mode
        
        # 查询文档
        answer = document_service.query_documents(
            query=request.query,
            mode=mode,
            k=request.k
        )
        
        # 检查是否返回了错误信息
        if answer.startswith("错误：") or answer.startswith("请求AI服务时出错"):
            logger.warning(f"查询返回错误: {answer}")
        
        return DocumentQueryResponse(
            answer=answer,
            mode=mode,
            retrieved_docs_count=request.k
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询文档失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/query/stream")
async def query_documents_stream(
    request: DocumentQueryRequest,
    document_service: DocumentService = Depends(get_document_service)
):
    """
    流式查询文档（支持实时输出）
    
    与 /query 接口功能相同，但返回流式响应，适合生成较长内容。
    响应类型为 text/plain，内容会逐步返回。
    
    Args:
        request: 查询请求，与 /query 接口相同
    
    Returns:
        StreamingResponse: 流式文本响应
        
    Raises:
        HTTPException: 当查询失败时返回 500 错误
    """
    try:
        logger.info(f"收到流式文档查询: query={request.query}, mode={request.mode}, k={request.k}")
        
        # 验证模式参数
        if request.mode not in ["auto", "qa", "code"]:
            raise HTTPException(
                status_code=400,
                detail=f"无效的查询模式: {request.mode}，支持的模式: auto, qa, code"
            )
        
        # 自动检测模式
        if request.mode == "auto":
            mode = "code" if document_service.is_code_request(request.query) else "qa"
            logger.info(f"自动检测模式为: {mode}")
        else:
            mode = request.mode
        
        # 流式查询
        def generate():
            try:
                for chunk in document_service.stream_query_documents(
                    query=request.query,
                    mode=mode,
                    k=request.k
                ):
                    yield chunk
            except Exception as e:
                logger.error(f"流式查询生成器错误: {e}", exc_info=True)
                yield f"\n\n[错误] {str(e)}"
        
        return StreamingResponse(
            generate(),
            media_type="text/plain; charset=utf-8"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"流式查询文档失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/rebuild-index", response_model=RebuildIndexResponse)
async def rebuild_index(
    document_service: DocumentService = Depends(get_document_service)
):
    """
    重新构建文档索引
    
    从 demos 和 drivers 目录重新加载所有文档并构建向量索引。
    首次使用时会自动构建，如果文档有更新可以手动重建索引。
    
    Returns:
        RebuildIndexResponse: 包含重建结果消息和文档块数量
        
    Raises:
        HTTPException: 当重建失败时返回 500 错误
    """
    try:
        logger.info("开始重建索引...")
        
        # 重建索引，返回文档块数量
        chunks_count = document_service.rebuild_index()
        
        logger.info(f"索引重建成功，文档块数量: {chunks_count}")
        return RebuildIndexResponse(
            message="索引重建成功",
            chunks_count=chunks_count
        )
    except ValueError as e:
        logger.error(f"重建索引失败（配置错误）: {str(e)}")
        raise HTTPException(status_code=400, detail=f"重建索引失败: {str(e)}")
    except Exception as e:
        logger.error(f"重建索引失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"重建索引失败: {str(e)}")


@router.get("/status", response_model=IndexStatusResponse)
async def get_index_status(
    document_service: DocumentService = Depends(get_document_service)
):
    """
    获取索引状态
    
    返回文档索引的当前状态信息，包括：
    - 索引是否已加载
    - 索引目录路径
    - 文档根目录路径
    - 知识库目录列表
    - 使用的嵌入模型和生成模型
    
    Returns:
        IndexStatusResponse: 包含索引状态的所有信息
        
    Raises:
        HTTPException: 当获取状态失败时返回 500 错误
    """
    try:
        status = IndexStatusResponse(
            index_loaded=document_service.vector_store is not None,
            index_dir=str(document_service.index_dir),
            docs_root=str(document_service.docs_root),
            knowledge_dirs=[str(d) for d in document_service.knowledge_dirs],
            embed_model=document_service.embed_model,
            gen_model=document_service.gen_model
        )
        return status
    except Exception as e:
        logger.error(f"获取索引状态失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")