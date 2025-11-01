import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from app.services.schedule_service import ScheduleService
from app.dependencies import get_schedule_service
from typing import Optional

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/convert")
async def convert_schedule_to_ics(
    file: UploadFile = File(..., description="CSV课表文件"),
    semester_start: Optional[str] = Form(None, description="学期开始日期，格式：YYYY-MM-DD（可选）"),
    schedule_service: ScheduleService = Depends(get_schedule_service)
):
    """
    将CSV课表文件转换为ICS日历文件
    
    请求格式：
    - 使用 multipart/form-data
    - file: CSV文件
    - semester_start: 学期开始日期（可选，格式：YYYY-MM-DD）
    
    CSV文件格式建议：
    应包含以下列（列名支持多种变体）：
    - 课程名称（course_name/课程名称/课程名）
    - 星期（weekday/星期/星期几）
    - 时间（time/时间/上课时间/节次）
    - 地点（location/地点/教室）
    - 周次（weeks/周次/上课周次，格式如：1-16 或 1,3,5-10）
    
    示例CSV：
    ```
    课程名称,星期,时间,地点,周次
    高等数学,周一,08:00-09:40,教学楼A101,1-16
    英语,周二,10:00-11:40,教学楼B205,1-16双
    ```
    """
    try:
        # 检查文件类型
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="文件必须是CSV格式")
        
        # 读取文件内容
        content = await file.read()
        
        # 尝试解码
        csv_content = None
        for encoding in ['utf-8', 'utf-8-sig', 'gbk', 'gb2312']:
            try:
                csv_content = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if csv_content is None:
            raise HTTPException(status_code=400, detail="无法解码CSV文件，请确保文件编码为UTF-8或GBK")
        
        logger.info(f"收到CSV文件: {file.filename}, 大小: {len(content)} 字节")
        
        # 解析CSV
        courses = schedule_service.parse_csv(csv_content)
        
        if not courses:
            raise HTTPException(status_code=400, detail="CSV文件中没有找到课程数据")
        
        logger.info(f"解析到 {len(courses)} 门课程")
        
        # 生成ICS
        ics_content = schedule_service.generate_ics(courses, semester_start)
        
        # 返回ICS文件
        return Response(
            content=ics_content,
            media_type="text/calendar",
            headers={
                "Content-Disposition": f'attachment; filename="schedule.ics"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"转换课表时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"转换失败: {str(e)}")


@router.post("/parse")
async def parse_schedule(
    file: UploadFile = File(..., description="CSV课表文件"),
    schedule_service: ScheduleService = Depends(get_schedule_service)
):
    """
    解析CSV课表文件，返回解析后的课程数据（用于测试和调试）
    """
    try:
        # 检查文件类型
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="文件必须是CSV格式")
        
        # 读取文件内容
        content = await file.read()
        
        # 尝试解码
        csv_content = None
        for encoding in ['utf-8', 'utf-8-sig', 'gbk', 'gb2312']:
            try:
                csv_content = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if csv_content is None:
            raise HTTPException(status_code=400, detail="无法解码CSV文件")
        
        # 解析CSV
        courses = schedule_service.parse_csv(csv_content)
        
        # 标准化课程数据
        normalized_courses = []
        for course in courses:
            normalized = schedule_service.normalize_course_data(course)
            normalized_courses.append(normalized)
        
        return {
            "total": len(courses),
            "courses": normalized_courses
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"解析课表时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")

