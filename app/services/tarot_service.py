# services/tarot_service.py
import json
from typing import List, Dict
from logging import getLogger

from app.services.ai_service import AIService


class TarotService:
    """塔罗牌服务类"""

    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
        # 使用 getLogger 获取 logger 实例
        self.logger = getLogger(__name__)

    def divine_cards(self, question: str) -> Dict:
        """
        根据用户问题直接抽取三张塔罗牌并进行解读

        Args:
            question: 用户提出的问题

        Returns:
            包含塔罗牌和整体解读的字典
        """
        prompt = f"""你是一个专业的塔罗牌占卜师。请根据以下问题，直接抽取三张塔罗牌并进行详细讲解。

问题: {question}

要求:
1. 抽取三张塔罗牌（正位或逆位）
2. 对每张牌进行详细的解读，包括牌面含义、与当前问题的关联
3. 综合三张牌给出整体解读
4. 使用专业但易懂的语言
5. 解读要具体、有指导意义

返回格式:
{{
    "cards": [
        {{
            "name": "牌名",
            "position": "正位/逆位",
            "interpretation": "解读内容"
        }}
    ],
    "overall_interpretation": "整体解读"
}}"""

        try:
            response = self.ai_service.ask_question(prompt)
            # 使用更安全的JSON解析方式
            result = json.loads(response)

            # 验证返回的数据结构
            if not isinstance(result, dict):
                raise ValueError("返回数据不是字典类型")

            cards = result.get("cards", [])
            if not isinstance(cards, list):
                raise ValueError("cards字段不是列表类型")

            # 验证每张牌的结构
            for card in cards:
                if not all(key in card for key in ["name", "position", "interpretation"]):
                    raise ValueError("卡片数据结构不完整")

            overall_interpretation = result.get("overall_interpretation", "")
            if not isinstance(overall_interpretation, str):
                raise ValueError("overall_interpretation字段不是字符串类型")

            return {
                "cards": cards,
                "overall_interpretation": overall_interpretation
            }
        except Exception as e:
            self.logger.error(f"塔罗牌占卜时出错: {str(e)}")
            # 返回默认值
            return {
                "cards": [
                    {
                        "name": "愚人",
                        "position": "正位",
                        "interpretation": "新的开始，冒险精神，无拘无束的自由。"
                    },
                    {
                        "name": "魔术师",
                        "position": "正位",
                        "interpretation": "创造力，自信，运用才能达成目标。"
                    },
                    {
                        "name": "女祭司",
                        "position": "正位",
                        "interpretation": "直觉，内在智慧，潜意识的信息。"
                    }
                ],
                "overall_interpretation": "这是一个充满机遇的新开始，需要发挥创造力和直觉来把握机会。"
            }
