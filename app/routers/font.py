# app/routers/font.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict
from app.services.font_service import FontService
from pydantic import BaseModel

router = APIRouter()

class FontGenerateRequest(BaseModel):
    text: str
    font_type: str  # HZK 或 ASC
    font_size: int
    arrangement: str = "horizontal"  # horizontal 或 vertical
    mode: str = "vertical_upper"     # vertical_upper, vertical_lower, horizontal_upper, horizontal_lower
    invert: bool = False
    array_name: str = ""

class CharacterPreviewRequest(BaseModel):
    character: str
    font_type: str  # HZK 或 ASC
    font_size: int

class FontResponse(BaseModel):
    code: str

class PreviewResponse(BaseModel):
    character: str
    font_info: str
    preview: List[str]

class SupportedFontsResponse(BaseModel):
    fonts: Dict

def get_font_service() -> FontService:
    return FontService()

@router.get("/supported", response_model=SupportedFontsResponse)
async def get_supported_fonts(font_service: FontService = Depends(get_font_service)):
    """获取支持的字体列表"""
    try:
        fonts = font_service.get_supported_fonts()
        return {"fonts": fonts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate", response_model=FontResponse)
async def generate_font_data(request: FontGenerateRequest,
                           font_service: FontService = Depends(get_font_service)):
    """生成字体数据C代码"""
    try:
        if request.font_size != 12:
            raise HTTPException(status_code=400, detail="仅支持12号字体")
        array_name = request.array_name if request.array_name else f"font_{request.font_type}{request.font_size}"
        font_service.load_font(request.font_type, request.font_size)
        c_code = font_service.generate_c51_code(
            request.text,
            request.arrangement,
            request.mode,
            request.invert,
            array_name
        )
        return {"code": c_code}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/preview", response_model=PreviewResponse)
async def preview_character(request: CharacterPreviewRequest,
                          font_service: FontService = Depends(get_font_service)):
    """预览字符点阵"""
    try:
        font_service.load_font(request.font_type, request.font_size)
        preview_lines = font_service.preview_char(request.character)
        font_info = f"{request.font_type}{request.font_size}"
        return {
            "character": request.character,
            "font_info": font_info,
            "preview": preview_lines
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
