import faiss
import numpy as np
import json
import os
from typing import List, Dict, Any
import logging

# 使用根记录器而不是特定名称的记录器
logger = logging.getLogger()

class FAISSManager:
    def __init__(self, index_path: str, dimension: int = 384):
        self.index_path = index_path
        self.dimension = dimension
        self.index = None
        self.id_to_index = {}  # 记忆ID到FAISS索引的映射
        self.index_to_id = {}  # FAISS索引到记忆ID的映射
        self.embedding_model = None
        
        self._ensure_storage_path()
        self.load_index()
        self._initialize_embedding_model()
    
    def _ensure_storage_path(self):
        """确保存储路径存在"""
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
    
    def _initialize_embedding_model(self):
        """初始化嵌入模型"""
        try:
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        except ImportError as e:
            logger.error(f"初始化嵌入模型失败: {e}")
            self.embedding_model = None

    def load_index(self):
        """加载FAISS索引"""
        try:
            if os.path.exists(self.index_path):
                self.index = faiss.read_index(self.index_path)
                
                # 加载ID映射
                mapping_path = f"{self.index_path}.mapping"
                if os.path.exists(mapping_path):
                    with open(mapping_path, 'r', encoding='utf-8') as f:
                        mapping_data = json.load(f)
                        self.id_to_index = mapping_data.get("id_to_index", {})
                        self.index_to_id = mapping_data.get("index_to_id", {})
                
                logger.info(f"已加载FAISS索引，包含 {self.index.ntotal} 个向量")
            else:
                # 创建新的索引
                self.index = faiss.IndexFlatL2(self.dimension)
                logger.info("创建了新的FAISS索引")
        except Exception as e:
            logger.error(f"加载FAISS索引失败: {e}")
            self.index = faiss.IndexFlatL2(self.dimension)
    
    def save_index(self):
        """保存FAISS索引"""
        try:
            faiss.write_index(self.index, self.index_path)
            
            # 保存ID映射
            mapping_path = f"{self.index_path}.mapping"
            with open(mapping_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "id_to_index": self.id_to_index,
                    "index_to_id": self.index_to_id
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"已保存FAISS索引，包含 {self.index.ntotal} 个向量")
            return True
        except Exception as e:
            logger.error(f"保存FAISS索引失败: {e}")
            return False
    
    def add_memory(self, memory_id: str, text: str):
        """添加记忆到向量索引"""
        try:
            if self.embedding_model is None:
                return False

            # 生成嵌入向量
            embedding = self.embedding_model.encode([text])
            embedding = np.array(embedding, dtype='float32')
            
            # 添加到索引
            idx = self.index.ntotal
            self.index.add(embedding)
            
            # 更新映射
            self.id_to_index[memory_id] = idx
            self.index_to_id[idx] = memory_id
            
            self.save_index()
            return True
        except Exception as e:
            logger.error(f"添加记忆到向量索引失败: {e}")
            return False
    
    def remove_memory(self, memory_id: str):
        """从向量索引中移除记忆"""
        try:
            if memory_id not in self.id_to_index:
                return False
            
            idx = self.id_to_index[memory_id]
            
            # FAISS不支持直接删除，需要重建索引
            # 这里标记为删除，在下次重建时实际删除
            self.index_to_id.pop(idx, None)
            self.id_to_index.pop(memory_id, None)
            
            # 设置定期重建索引的逻辑
            self.save_index()
            return True
        except Exception as e:
            logger.error(f"从向量索引中移除记忆失败: {e}")
            return False
    
    def search_similar(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """语义搜索相似记忆"""
        try:
            if self.embedding_model is None:
                logger.warning("嵌入模型未初始化，无法进行语义搜索")
                return []
                
            # 生成查询向量
            query_embedding = self.embedding_model.encode([query])
            query_embedding = np.array(query_embedding, dtype='float32')
            
            # 搜索相似向量
            distances, indices = self.index.search(query_embedding, k)
            
            # 添加调试信息
            logger.debug(f"搜索查询: {query}")
            logger.debug(f"索引总数: {self.index.ntotal}")
            logger.debug(f"找到的索引: {indices}")
            logger.debug(f"距离: {distances}")
            
            # 转换为记忆ID
            results = []
            for i, idx in enumerate(indices[0]):
                if idx in self.index_to_id and idx != -1:
                    results.append({
                        "memory_id": self.index_to_id[idx],
                        "similarity": 1.0 / (1.0 + distances[0][i]),  # 转换为相似度分数
                        "distance": distances[0][i]
                    })
            
            logger.debug(f"结果数量: {len(results)}")
            
            return results
        except Exception as e:
            logger.error(f"语义搜索失败: {e}")
            return []
        
    def rebuild_index(self):
        """重建索引，移除已删除的项目"""
        # 实现索引重建逻辑
        # 由于FAISS不支持直接删除，需要定期重建
        pass