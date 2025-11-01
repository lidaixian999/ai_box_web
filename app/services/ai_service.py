import ollama
import os
from dotenv import load_dotenv

load_dotenv()


class AIService:
    def __init__(self):
        self.host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "qwen3:8b")

        # 配置Ollama客户端
        self.client = ollama.Client(host=self.host)

    def ask_question(self, question: str) -> str:
        """向AI模型提问并获取响应"""
        try:
            response = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": question}]
            )
            return response['message']['content']
        except Exception as e:
            return f"请求AI服务时出错: {str(e)}"