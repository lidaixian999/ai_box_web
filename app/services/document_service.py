import os
import logging
import re
from pathlib import Path
from typing import List, Optional, Iterator, Dict, Any
import ollama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
try:
    from langchain_core.documents import Document
except ImportError:
    from langchain.schema import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class DocumentService:
    """文档分析服务，支持从 demos 和 drivers 目录加载文档并进行向量检索"""
    
    def __init__(self):
        """初始化文档服务"""
        self.host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.embed_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        self.gen_model = os.getenv("OLLAMA_MODEL", "qwen3:8b")
        
        # 文档目录路径
        self.docs_root = Path(os.getenv(
            "DOCS_ROOT", 
            r"C:\Users\97049\Documents\xwechat_files\wxid_3ci68pxrxyxn22_9bf9\msg\file\2025-11\ws63"
        ))
        self.knowledge_dirs = [
            self.docs_root / "demos",
            self.docs_root / "drivers"
        ]
        
        # 索引配置
        self.index_dir = self.docs_root / "faiss_index"
        self.chunk_size = 4096
        self.chunk_overlap = 256
        self.glob_patterns = ["**/*.c", "**/*.h", "**/*.md", "**/*.txt"]
        
        # C/H 文件分隔符
        self.c_separators = [
            "\n\n\n", "\n\n", "\n", " ", "",
            ";", "{", "}", "(", ")", "#", "//", "/*", "*/"
        ]
        
        # 向量存储和 LLM
        self.vector_store: Optional[FAISS] = None
        self.embeddings = OllamaEmbeddings(
            model=self.embed_model,
            base_url=self.host
        )
        self.client = ollama.Client(host=self.host)
        
        # 加载索引
        try:
            self._load_or_build_index()
        except Exception as e:
            logger.error(f"初始化文档服务失败: {e}", exc_info=True)
            raise
    
    def _load_documents(self) -> List[Document]:
        """加载所有文档并分块"""
        docs: List[Document] = []
        
        for kd in self.knowledge_dirs:
            if not kd.exists():
                logger.warning(f"知识库目录不存在，跳过: {kd}")
                continue
                
            for pat in self.glob_patterns:
                for file in kd.glob(pat):
                    try:
                        text = file.read_text(encoding="utf-8", errors="ignore")
                        if not text.strip():
                            continue
                            
                        splitter = RecursiveCharacterTextSplitter(
                            chunk_size=self.chunk_size,
                            chunk_overlap=self.chunk_overlap,
                            separators=self.c_separators,
                        )
                        chunks = splitter.split_text(text)
                        for chk in chunks:
                            if chk.strip():  # 跳过空块
                                docs.append(
                                    Document(
                                        page_content=chk,
                                        metadata={"source": str(file.relative_to(self.docs_root))},
                                    )
                                )
                    except Exception as e:
                        logger.error(f"读取文件失败 {file}: {e}", exc_info=True)
                        continue
        
        logger.info(f"加载了 {len(docs)} 个文档块")
        return docs
    
    def _build_index(self, docs: List[Document]) -> FAISS:
        """构建 FAISS 向量索引"""
        if not docs:
            raise ValueError("没有文档可索引")
            
        texts = [d.page_content for d in docs]
        metadatas = [d.metadata for d in docs]
        
        logger.info(f"开始构建索引，文档块数量: {len(docs)}")
        
        # 使用 langchain 的 FAISS.from_documents，自动处理嵌入
        vector_store = FAISS.from_documents(
            documents=docs,
            embedding=self.embeddings
        )
        
        logger.info("索引构建完成")
        return vector_store
    
    def _build_and_save_index(self):
        """内部方法：构建并保存索引"""
        docs = self._load_documents()
        if not docs:
            raise ValueError("未找到任何文档，请检查文档目录配置")
        
        os.makedirs(self.index_dir, exist_ok=True)
        self.vector_store = self._build_index(docs)
        self.vector_store.save_local(str(self.index_dir))
        logger.info(f"FAISS 索引已保存到: {self.index_dir}")
    
    def _load_or_build_index(self):
        """加载已存在的索引，如果不存在则构建新的"""
        try:
            if self.index_dir.exists() and any(self.index_dir.iterdir()):
                logger.info(f"加载索引: {self.index_dir}")
                self.vector_store = FAISS.load_local(
                    str(self.index_dir),
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                logger.info("索引加载成功")
            else:
                logger.info("索引不存在，开始构建...")
                self._build_and_save_index()
        except Exception as e:
            logger.warning(f"加载索引失败: {e}，重新构建...")
            self._build_and_save_index()
    
    def rebuild_index(self) -> int:
        """
        公开方法：重新构建索引，返回文档块数量
        
        Returns:
            int: 文档块数量
        """
        logger.info("开始重建索引...")
        docs = self._load_documents()
        chunks_count = len(docs)
        self._build_and_save_index()
        logger.info(f"索引重建完成，文档块数量: {chunks_count}")
        return chunks_count
    
    def is_code_request(self, text: str) -> bool:
        """
        检测是否为代码生成请求
        
        Args:
            text: 查询文本
            
        Returns:
            bool: 是否为代码生成请求
        """
        code_keywords = r"(生成|写|code|写一个|示例|demo|sample|创建|实现|编写)"
        return bool(re.search(code_keywords, text, re.I))
    
    def _get_retriever(self, mode: str, k: int):
        """
        根据模式获取检索器
        
        Args:
            mode: 查询模式 ("qa" 或 "code")
            k: 检索的文档数量
            
        Returns:
            retriever: 检索器对象
        """
        if self.vector_store is None:
            raise ValueError("向量索引未加载，请先构建索引")
        
        # 创建基础检索器
        retriever = self.vector_store.as_retriever(
            search_kwargs={"k": k * 2 if mode == "code" else k}  # 代码模式多检索一些，后续会过滤
        )
        return retriever
    
    def _retrieve_documents(self, query: str, mode: str, k: int) -> List[Document]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            mode: 查询模式
            k: 检索的文档数量
            
        Returns:
            List[Document]: 检索到的文档列表
        """
        retriever = self._get_retriever(mode, k)
        docs = retriever.invoke(query)
        
        # 代码模式：过滤出 .c 文件
        if mode == "code":
            docs = [d for d in docs if d.metadata.get("source", "").endswith(".c")]
            docs = docs[:min(k, 4)]  # 限制最多4个
        
        return docs[:k]
    
    def _build_prompt(self, query: str, docs: List[Document], mode: str) -> str:
        """
        构建提示词
        
        Args:
            query: 查询文本
            docs: 检索到的文档
            mode: 查询模式
            
        Returns:
            str: 构建好的提示词
        """
        if mode == "code":
            prompt = (
                "根据以下检索到的源码，生成一份**可直接编译运行的完整 C 文件**，"
                "包含必要头文件、初始化、主循环。功能描述："
                f"{query}\n\n参考源码：\n"
            )
            for d in docs:
                prompt += d.page_content[:600] + "\n--------\n"
        else:
            prompt = "基于以下文档内容回答问题（给出步骤、接口、返回值）：\n\n"
            for d in docs:
                prompt += d.page_content + "\n--------\n"
            prompt += f"\n问题：{query}"
        
        return prompt
    
    def query_documents(self, query: str, mode: str = "qa", k: int = 3) -> str:
        """
        查询文档
        
        Args:
            query: 查询问题
            mode: 模式 ("qa" 或 "code")
            k: 检索的文档数量
            
        Returns:
            str: 答案文本
        """
        try:
            if self.vector_store is None:
                return "错误：向量索引未加载，请先构建索引"
            
            # 检索相关文档
            docs = self._retrieve_documents(query, mode, k)
            
            if not docs:
                return "未找到相关文档，请检查查询内容或重建索引"
            
            # 构建提示词
            prompt = self._build_prompt(query, docs, mode)
            
            # 调用 LLM 生成回答
            response = self.client.chat(
                model=self.gen_model,
                messages=[{"role": "user", "content": prompt}]
            )
            return response['message']['content']
        except ValueError as e:
            logger.error(f"查询文档失败: {e}")
            return f"错误：{str(e)}"
        except Exception as e:
            logger.error(f"查询文档失败: {e}", exc_info=True)
            return f"请求AI服务时出错: {str(e)}"
    
    def stream_query_documents(self, query: str, mode: str = "qa", k: int = 3) -> Iterator[str]:
        """
        流式查询文档（生成器）
        
        Args:
            query: 查询问题
            mode: 模式 ("qa" 或 "code")
            k: 检索的文档数量
            
        Yields:
            str: 答案文本块
        """
        try:
            if self.vector_store is None:
                yield "错误：向量索引未加载，请先构建索引"
                return
            
            # 检索相关文档
            docs = self._retrieve_documents(query, mode, k)
            
            if not docs:
                yield "未找到相关文档，请检查查询内容或重建索引"
                return
            
            # 构建提示词
            prompt = self._build_prompt(query, docs, mode)
            
            # 流式调用 LLM
            stream = self.client.chat(
                model=self.gen_model,
                messages=[{"role": "user", "content": prompt}],
                stream=True
            )
            
            for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    yield chunk['message']['content']
        except ValueError as e:
            logger.error(f"流式查询文档失败: {e}")
            yield f"错误：{str(e)}"
        except Exception as e:
            logger.error(f"流式查询文档失败: {e}", exc_info=True)
            yield f"请求AI服务时出错: {str(e)}"