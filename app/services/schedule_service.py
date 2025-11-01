import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from ics import Calendar, Event
from ics.alarm import DisplayAlarm
import pytz
import logging

logger = logging.getLogger(__name__)


class ScheduleService:
    """课表服务类，负责CSV解析和ICS生成"""
    
    # 星期几到数字的映射（周一=0）
    WEEKDAY_MAP = {
        '周一': 0, '星期一': 0, 'Monday': 0, 'Mon': 0, '1': 0,
        '周二': 1, '星期二': 1, 'Tuesday': 1, 'Tue': 1, '2': 1,
        '周三': 2, '星期三': 2, 'Wednesday': 2, 'Wed': 2, '3': 2,
        '周四': 3, '星期四': 3, 'Thursday': 3, 'Thu': 3, '4': 3,
        '周五': 4, '星期五': 4, 'Friday': 4, 'Fri': 4, '5': 4,
        '周六': 5, '星期六': 5, 'Saturday': 5, 'Sat': 5, '6': 5,
        '周日': 6, '星期日': 6, 'Sunday': 6, 'Sun': 6, '0': 6,
    }
    
    def __init__(self, ai_service=None, start_date: Optional[str] = None):
        """
        初始化课表服务
        :param ai_service: AI服务实例，用于解析CSV
        :param start_date: 学期开始日期，格式为 'YYYY-MM-DD'，默认为当前周一的日期
        """
        self.ai_service = ai_service
        
        if start_date:
            self.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            # 确保是周一
            days_to_monday = self.start_date.weekday()
            self.start_date -= timedelta(days=days_to_monday)
        else:
            # 默认为当前周的周一
            today = datetime.now().date()
            days_to_monday = today.weekday()
            self.start_date = today - timedelta(days=days_to_monday)
    
    def parse_csv(self, csv_content: str) -> List[Dict]:
        """
        使用AI解析CSV文件内容
        :param csv_content: CSV文件的字符串内容
        :return: 解析后的课程列表
        """
        if not self.ai_service:
            raise ValueError("AI服务未配置，无法解析CSV文件")
        
        try:
            # 尝试不同的编码
            csv_text = None
            for encoding in ['utf-8', 'utf-8-sig', 'gbk', 'gb2312']:
                try:
                    if isinstance(csv_content, bytes):
                        csv_text = csv_content.decode(encoding)
                    else:
                        csv_text = csv_content
                    break
                except UnicodeDecodeError:
                    continue
            
            if csv_text is None:
                raise ValueError("无法解码CSV文件，请确保文件编码为UTF-8或GBK")
            
            # 构造提示词，让AI解析课表
            prompt = self._build_parse_prompt(csv_text)
            
            logger.info("使用AI解析课表...")
            ai_response = self.ai_service.ask_question(prompt)
            
            # 解析AI返回的JSON
            courses = self._parse_ai_response(ai_response)
            
            logger.info(f"AI成功解析 {len(courses)} 门课程")
            return courses
            
        except Exception as e:
            logger.error(f"使用AI解析CSV时出错: {str(e)}")
            raise ValueError(f"CSV解析失败: {str(e)}")
    
    def _build_parse_prompt(self, csv_text: str) -> str:
        """
        构造用于解析课表的AI提示词
        :param csv_text: CSV文件文本内容
        :return: 提示词字符串
        """
        prompt = """你是一个专业的课表解析助手。请根据以下CSV课表文件，准确解析课程信息并返回JSON格式的结果，用于生成ICS日历文件。

重要要求：
1. **严格遵循CSV文件内容**：只提取CSV中实际存在的课程信息，不要添加或推断任何不存在的课程
2. **不要添加课程**：如果CSV中某个时间段没有课程，不要添加任何课程记录
3. **准确理解列结构**：注意区分每一列代表一天，按照课表的列结构进行解析

课表列结构说明：
- **第一列**：时间段信息（包含节次和具体时间，如："第1 2节\\n(01,02)\\n08:30-09:55"）
- **第二列**：星期一（Monday）的课程
- **第三列**：星期二（Tuesday）的课程
- **第四列**：星期三（Wednesday）的课程
- **第五列**：星期四（Thursday）的课程
- **第六列**：星期五（Friday）的课程
- **第七列**：星期六（Saturday）的课程
- **第八列**：星期日（Sunday）的课程

需要提取的字段：
   - course_name: 课程名称（必填，从CSV单元格中提取的实际课程名）
   - weekday: 星期几（必填，根据列位置确定：第二列=星期一，第三列=星期二，以此类推）
   - time: 上课时间（必填，从第一列的时间段信息中提取，格式如：08:30-09:55）
   - location: 上课地点（可选，如：B-1-506）
   - weeks: 上课周次（可选，格式如：1-16 或 1-16单 或 1-16双）
   - teacher: 授课教师（可选，教师姓名）
   - note: 课程备注信息（可选，如："不开放选课，理论课线上"等附加说明）

解析步骤：
1. 识别表头行（通常包含"星期一"、"星期二"等星期标识）
2. 从表头行之后开始读取数据
3. 对于每一行：
   - 第一列是时间段，提取时间信息（如：08:30-09:55）
   - 第二列开始，依次对应星期一至星期日的课程
   - 如果某列有课程信息，结合第一列的时间段，组合成完整的课程记录
4. 从课程单元格中提取：课程名称、教师、周次、地点等信息
5. 如果同一门课程在不同周次或地点上课，拆分成多条记录
6. 保留课程名称中的括号信息作为备注（note字段）

请严格按照以下JSON格式返回结果（只包含CSV中实际存在的课程）：
[
  {
    "course_name": "课程名称",
    "weekday": "星期一",
    "time": "08:30-09:55",
    "location": "B-1-506",
    "weeks": "1-16",
    "teacher": "教师姓名",
    "note": "备注信息（如果有）"
  },
  ...
]

CSV课表数据：
```csv
""" + csv_text[:8000] + """
```

请直接返回JSON数组，不要包含markdown代码块、注释或其他格式。只返回CSV中实际存在的课程数据，确保weekday字段准确对应列的位置（第二列=星期一，第三列=星期二，以此类推）。"""
        
        return prompt
    
    def _parse_ai_response(self, ai_response: str) -> List[Dict]:
        """
        解析AI返回的响应，提取JSON格式的课程列表
        :param ai_response: AI返回的响应文本
        :return: 课程列表
        """
        courses = []
        
        try:
            # 尝试提取JSON部分（可能包含在代码块中）
            json_text = ai_response.strip()
            
            # 如果包含markdown代码块，提取JSON部分
            if '```json' in json_text:
                json_text = json_text.split('```json')[1].split('```')[0].strip()
            elif '```' in json_text:
                # 可能是其他代码块格式
                parts = json_text.split('```')
                if len(parts) >= 2:
                    json_text = parts[1].strip()
                    if json_text.startswith('json'):
                        json_text = json_text[4:].strip()
            
            # 尝试找到JSON数组的开始和结束
            start_idx = json_text.find('[')
            end_idx = json_text.rfind(']')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_text = json_text[start_idx:end_idx + 1]
            
            # 解析JSON
            courses = json.loads(json_text)
            
            # 验证和标准化数据
            standardized_courses = []
            for course in courses:
                if isinstance(course, dict) and 'course_name' in course:
                    standardized = {
                        'course_name': course.get('course_name', '').strip(),
                        'weekday': course.get('weekday', '').strip(),
                        'time': course.get('time', '').strip(),
                        'location': course.get('location', '').strip(),
                        'weeks': course.get('weeks', '').strip(),
                        'teacher': course.get('teacher', '').strip(),
                        'note': course.get('note', '').strip()
                    }
                    # 只添加有效的课程（至少要有课程名和星期）
                    if standardized['course_name'] and standardized['weekday']:
                        standardized_courses.append(standardized)
            
            return standardized_courses
            
        except json.JSONDecodeError as e:
            logger.error(f"解析AI返回的JSON失败: {str(e)}")
            logger.error(f"AI响应内容: {ai_response[:500]}")
            raise ValueError(f"AI返回的数据格式错误，无法解析JSON: {str(e)}")
        except Exception as e:
            logger.error(f"处理AI响应时出错: {str(e)}")
            raise ValueError(f"无法解析AI返回的数据: {str(e)}")
    
    
    def normalize_course_data(self, course: Dict) -> Dict:
        """
        标准化课程数据
        AI返回的数据已经是标准格式，直接返回并确保字段完整
        :param course: 原始课程字典
        :return: 标准化后的课程字典
        """
        # AI返回的数据应该已经是标准格式（包含course_name和weekday）
        if 'course_name' in course and 'weekday' in course:
            normalized = {
                'course_name': course.get('course_name', '').strip(),
                'weekday': course.get('weekday', '').strip(),
                'time': course.get('time', '').strip(),
                'location': course.get('location', '').strip(),
                'weeks': course.get('weeks', '').strip(),
                'teacher': course.get('teacher', '').strip(),
                'note': course.get('note', '').strip()
            }
            return normalized
        
        # 如果格式不正确，返回空字典
        logger.warning(f"课程数据格式不正确: {course}")
        return {
            'course_name': '',
            'weekday': '',
            'time': '',
            'location': '',
            'weeks': '',
            'teacher': '',
            'note': ''
        }
    
    def parse_time(self, time_str: str) -> tuple:
        """
        解析时间字符串，返回开始时间和结束时间
        支持的格式：
        - "08:00-09:40"
        - "第1-2节" (需要时间映射)
        - "08:00"
        """
        time_str = time_str.strip()
        
        # 如果包含 "-"，尝试分割
        if '-' in time_str or '—' in time_str:
            separator = '-' if '-' in time_str else '—'
            parts = time_str.split(separator)
            if len(parts) == 2:
                start_str = parts[0].strip()
                end_str = parts[1].strip()
                
                # 尝试解析时间
                try:
                    start_time = datetime.strptime(start_str, '%H:%M').time()
                    end_time = datetime.strptime(end_str, '%H:%M').time()
                    return start_time, end_time
                except ValueError:
                    pass
        
        # 如果是指定节次，使用默认时间表
        if '节' in time_str or '节次' in time_str:
            # 常见节次时间表（每节课45分钟，课间休息10分钟）
            period_map = {
                '1': (8, 0), '2': (8, 55), '3': (10, 5), '4': (11, 0),
                '5': (14, 0), '6': (14, 55), '7': (16, 5), '8': (17, 0),
                '9': (19, 0), '10': (19, 55), '11': (20, 50), '12': (21, 45),
            }
            
            # 提取节次数字
            import re
            periods = re.findall(r'\d+', time_str)
            if periods:
                start_period = int(periods[0])
                end_period = int(periods[-1]) if len(periods) > 1 else start_period
                
                if str(start_period) in period_map:
                    start_hour, start_min = period_map[str(start_period)]
                    # 结束时间为下一节课的开始时间
                    if str(end_period + 1) in period_map:
                        end_hour, end_min = period_map[str(end_period + 1)]
                    else:
                        # 默认每节课45分钟
                        end_time_obj = datetime.combine(datetime.today(), 
                                                       datetime(start_hour, start_min).time()) + timedelta(minutes=45)
                        end_hour, end_min = end_time_obj.hour, end_time_obj.minute
                    
                    return datetime(start_hour, start_min).time(), datetime(end_hour, end_min).time()
        
        # 默认时间（如果无法解析）
        logger.warning(f"无法解析时间格式: {time_str}，使用默认时间 08:00-09:40")
        return datetime(8, 0).time(), datetime(9, 40).time()
    
    def parse_weeks(self, weeks_str: str) -> List[int]:
        """
        解析周次字符串，返回周次列表
        支持的格式：
        - "1-16" -> [1,2,3,...,16]
        - "1,3,5-10" -> [1,3,5,6,7,8,9,10]
        - "1-16单" -> [1,3,5,...,15]
        - "1-16双" -> [2,4,6,...,16]
        """
        if not weeks_str or weeks_str.strip() == '':
            # 默认整学期（1-20周）
            return list(range(1, 21))
        
        weeks_str = weeks_str.strip()
        weeks = []
        
        # 判断是单周还是双周
        is_odd = '单' in weeks_str or 'odd' in weeks_str.lower()
        is_even = '双' in weeks_str or 'even' in weeks_str.lower()
        
        # 移除单双周标记
        weeks_str = weeks_str.replace('单', '').replace('双', '').replace('odd', '').replace('even', '')
        
        # 分割逗号
        parts = weeks_str.split(',')
        
        for part in parts:
            part = part.strip()
            if '-' in part or '—' in part:
                separator = '-' if '-' in part else '—'
                range_parts = part.split(separator)
                if len(range_parts) == 2:
                    try:
                        start = int(range_parts[0].strip())
                        end = int(range_parts[1].strip())
                        if is_odd:
                            weeks.extend([w for w in range(start, end + 1) if w % 2 == 1])
                        elif is_even:
                            weeks.extend([w for w in range(start, end + 1) if w % 2 == 0])
                        else:
                            weeks.extend(range(start, end + 1))
                    except ValueError:
                        pass
            else:
                try:
                    week = int(part)
                    if is_odd and week % 2 == 0:
                        continue
                    if is_even and week % 2 == 1:
                        continue
                    weeks.append(week)
                except ValueError:
                    pass
        
        return sorted(set(weeks)) if weeks else list(range(1, 21))
    
    def weekday_to_number(self, weekday_str: str) -> int:
        """
        将星期几字符串转换为数字（周一=0）
        """
        weekday_str = weekday_str.strip()
        
        # 直接查找映射
        for key, value in self.WEEKDAY_MAP.items():
            if key in weekday_str:
                return value
        
        # 尝试提取数字
        import re
        numbers = re.findall(r'\d+', weekday_str)
        if numbers:
            num = int(numbers[0])
            if 0 <= num <= 6:
                return num % 7
        
        # 默认返回0（周一）
        logger.warning(f"无法识别星期: {weekday_str}，默认为周一")
        return 0
    
    def refine_courses(self, courses: List[Dict]) -> List[Dict]:
        """
        使用AI对解析后的课程数据进行二次处理和优化
        :param courses: 初始解析的课程列表
        :return: 优化后的课程列表
        """
        if not self.ai_service:
            logger.warning("AI服务未配置，跳过二次处理，使用原始数据")
            return courses
        
        if not courses:
            return courses
        
        try:
            # 将课程数据转换为JSON字符串
            courses_json = json.dumps(courses, ensure_ascii=False, indent=2)
            
            # 构造二次处理的提示词
            prompt = self._build_refine_prompt(courses_json)
            
            logger.info("使用AI对课程数据进行二次处理和优化...")
            ai_response = self.ai_service.ask_question(prompt)
            
            # 解析AI返回的优化后的课程数据
            refined_courses = self._parse_ai_response(ai_response)
            
            logger.info(f"AI优化完成，原始 {len(courses)} 门课程，优化后 {len(refined_courses)} 门课程")
            return refined_courses
            
        except Exception as e:
            logger.error(f"AI二次处理时出错: {str(e)}，使用原始数据")
            return courses
    
    def _build_refine_prompt(self, courses_json: str) -> str:
        """
        构造用于二次处理和优化课程的AI提示词
        :param courses_json: 初始解析的课程JSON数据
        :return: 提示词字符串
        """
        prompt = """你是一个专业的课表数据优化助手。请对以下解析后的课程数据进行二次处理和优化，确保数据准确、完整，并修正可能存在的错误。

优化任务：
1. **数据验证和修正**：检查并修正以下问题
   - 时间格式是否正确（应为 HH:MM-HH:MM 格式）
   - 星期几是否准确（星期一、星期二...星期日）
   - 周次格式是否正确（如：1-16、1-16单、1-16双）
   - 地点信息是否完整

2. **数据补充**：如果某些字段缺失但可以从其他信息推断，可以合理补充
   - 如果时间缺失，尝试从课程信息中推断
   - 确保每个课程都有完整的必要字段

3. **数据优化**：
   - 统一字段格式（时间、星期、周次等）
   - 清理无效或重复的数据
   - 确保课程名称清晰明确
   - 合并相同课程不同周次的记录（如果合适）

4. **错误修正**：
   - 修正明显的数据错误
   - 统一命名规范
   - 处理特殊情况（如单周、双周）

要求：
- 保持原始课程的核心信息不变
- 不要删除真实存在的课程
- 只优化和修正，不要添加新课程
- 确保返回的数据格式与输入格式一致

输入数据（JSON格式）：
""" + courses_json[:6000] + """

请返回优化后的课程JSON数组，格式与输入相同：
[
  {
    "course_name": "课程名称",
    "weekday": "星期一",
    "time": "08:30-09:55",
    "location": "B-1-506",
    "weeks": "1-16",
    "teacher": "教师姓名",
    "note": "备注信息（如果有）"
  },
  ...
]

请直接返回JSON数组，不要包含markdown代码块、注释或其他格式。"""
        
        return prompt
    
    def generate_ics(self, courses: List[Dict], semester_start: Optional[str] = None) -> str:
        """
        生成ICS日历文件
        流程：1. AI解析CSV → 2. AI二次优化 → 3. 生成ICS文件
        :param courses: 课程列表（AI解析后的数据）
        :param semester_start: 学期开始日期，格式 'YYYY-MM-DD'
        :return: ICS文件内容（字符串）
        """
        # 第一步：对课程数据进行二次AI处理和优化
        refined_courses = self.refine_courses(courses)
        
        # 第二步：设置学期开始日期
        if semester_start:
            self.start_date = datetime.strptime(semester_start, '%Y-%m-%d').date()
            days_to_monday = self.start_date.weekday()
            self.start_date -= timedelta(days=days_to_monday)
        
        # 第三步：创建日历并生成ICS文件
        # 设置中国时区（Asia/Shanghai, UTC+8）
        china_tz = pytz.timezone('Asia/Shanghai')
        calendar = Calendar()
        
        for course in refined_courses:
            try:
                # 标准化课程数据
                normalized = self.normalize_course_data(course)
                
                course_name = normalized.get('course_name', '未命名课程')
                weekday_str = normalized.get('weekday', '')
                time_str = normalized.get('time', '')
                location = normalized.get('location', '')
                weeks_str = normalized.get('weeks', '')
                
                if not course_name or course_name == '':
                    continue
                
                # 解析星期几
                weekday = self.weekday_to_number(weekday_str)
                
                # 解析时间
                start_time, end_time = self.parse_time(time_str)
                
                # 解析周次
                weeks = self.parse_weeks(weeks_str)
                
                # 为每周创建事件
                for week in weeks:
                    # 计算该周的日期（第N周的周一 + weekday天）
                    course_date = self.start_date + timedelta(days=(week - 1) * 7 + weekday)
                    
                    # 创建带时区的datetime对象（中国时区）
                    begin_dt = datetime.combine(course_date, start_time)
                    end_dt = datetime.combine(course_date, end_time)
                    # 本地化到中国时区
                    begin_dt = china_tz.localize(begin_dt)
                    end_dt = china_tz.localize(end_dt)
                    
                    # 创建事件
                    event = Event()
                    event.name = course_name
                    event.begin = begin_dt
                    event.end = end_dt
                    event.location = location if location else None
                    
                    # 构建描述信息
                    description_parts = [f"周次: 第{week}周", f"时间: {time_str}", f"星期: {weekday_str}"]
                    note = normalized.get('note', '').strip()
                    if note:
                        description_parts.append(f"备注: {note}")
                    teacher = normalized.get('teacher', '').strip()
                    if teacher:
                        description_parts.append(f"教师: {teacher}")
                    event.description = "\n".join(description_parts)
                    
                    # 添加提醒（提前15分钟）
                    alarm = DisplayAlarm(trigger=timedelta(minutes=-15))
                    event.alarms.append(alarm)
                    
                    calendar.events.add(event)
                
                logger.info(f"已添加课程: {course_name} ({len(weeks)}周)")
                
            except Exception as e:
                logger.error(f"处理课程时出错: {str(e)}, 课程数据: {course}")
                continue
        
        return str(calendar)

