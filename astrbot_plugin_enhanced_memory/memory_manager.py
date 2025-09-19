import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

try:
    from .faiss_manager import FAISSManager
    from .memory_classifier import MemoryClassifier
    from .memory_graph import MemoryGraph
    from .memory_extractor import MemoryExtractor
except ImportError as e:
    logging.error(f"导入组件失败: {e}")
    # 创建占位类
    class FAISSManager:
        def __init__(self, *args, **kwargs): pass
        def add_memory(self, *args, **kwargs): return True
        def remove_memory(self, *args, **kwargs): return True
        def search_similar(self, *args, **kwargs): return []
    
    class MemoryClassifier:
        def __init__(self, *args, **kwargs): pass
        def classify(self, text): return {"其他": 1.0}
    
    class MemoryGraph:
        def __init__(self, *args, **kwargs): pass
        def add_memory(self, *args, **kwargs): pass
        def add_association(self, *args, **kwargs): return True
        def get_associated_memories(self, *args, **kwargs): return []
    
    class MemoryExtractor:
        def __init__(self, *args, **kwargs): pass
        def extract_from_text(self, text, context=None): return []
logger = logging.getLogger("astrbot.plugin.enhanced_memory")

class EnhancedMemoryManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.storage_path = config.get("storage_path", "data/plugin_data/enhanced_memory")
        self.max_memories = config.get("max_memories", 5000)
        
        # 初始化组件
        self.faiss_manager = FAISSManager(
            os.path.join(self.storage_path, "faiss_index"),
            config.get("faiss", {}).get("dimension", 384)
        )
        
        self.classifier = MemoryClassifier(
            os.path.join(self.storage_path, "classification_model"),
            config.get("classification", {}).get("categories", ["事实", "观点", "用户偏好", "事件", "关系"])
        )
        
        self.memory_graph = MemoryGraph(
            os.path.join(self.storage_path, "memory_graph.json")
        )
        
        self.extractor = MemoryExtractor(
            min_importance=config.get("auto_extraction", {}).get("min_importance", 0.3),
            extract_keywords=config.get("auto_extraction", {}).get("extract_keywords", True),
            max_keywords=config.get("auto_extraction", {}).get("max_keywords", 5)
        )
        
        self.memories = {}
        self._ensure_storage_path()
        self.load_memories()
    
    def _ensure_storage_path(self):
        """确保存储路径存在"""
        os.makedirs(self.storage_path, exist_ok=True)
    
    def load_memories(self):
        """从文件加载记忆"""
        try:
            memories_path = os.path.join(self.storage_path, "memories.json")
            if os.path.exists(memories_path):
                with open(memories_path, 'r', encoding='utf-8') as f:
                    self.memories = json.load(f)
                logger.info(f"已加载 {len(self.memories)} 条记忆")
            else:
                self.memories = {}
                logger.info("未找到记忆文件，将创建新文件")
        except Exception as e:
            logger.error(f"加载记忆失败: {e}")
            self.memories = {}
    
    def save_memories(self):
        """保存记忆到文件"""
        try:
            memories_path = os.path.join(self.storage_path, "memories.json")
            
            # 确保不超过最大记忆数量
            if len(self.memories) > self.max_memories:
                self._prune_memories()
            
            with open(memories_path, 'w', encoding='utf-8') as f:
                json.dump(self.memories, f, ensure_ascii=False, indent=2)
            
            logger.info(f"已保存 {len(self.memories)} 条记忆")
            return True
        except Exception as e:
            logger.error(f"保存记忆失败: {e}")
            return False
    
    def _prune_memories(self):
        """修剪记忆，移除不重要的"""
        # 按重要性排序，保留最重要的
        sorted_memories = sorted(
            self.memories.items(), 
            key=lambda x: x[1].get("importance", 0) * (1 - x[1].get("decay", 0)), 
            reverse=True
        )
        
        # 保留前N个记忆
        self.memories = dict(sorted_memories[:self.max_memories])
        
        # 更新FAISS索引和记忆图
        self._sync_auxiliary_storage()
    
    def _sync_auxiliary_storage(self):
        """同步辅助存储（FAISS和记忆图）"""
        # 确保FAISS索引和记忆图与主记忆存储同步
        memory_ids = set(self.memories.keys())
        
        # 同步FAISS
        faiss_ids = set(self.faiss_manager.id_to_index.keys())
        for memory_id in memory_ids - faiss_ids:
            if memory_id in self.memories:
                self.faiss_manager.add_memory(memory_id, self.memories[memory_id]["content"])
        
        for memory_id in faiss_ids - memory_ids:
            self.faiss_manager.remove_memory(memory_id)
        
        # 同步记忆图
        graph_ids = set(self.memory_graph.graph.nodes())
        for memory_id in memory_ids - graph_ids:
            if memory_id in self.memories:
                self.memory_graph.add_memory(memory_id, self.memories[memory_id])
        
        for memory_id in graph_ids - memory_ids:
            self.memory_graph.remove_memory(memory_id)
    
    def add_memory(
        self, 
        content: str, 
        importance: float = 0.5, 
        memory_type: str = None,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
        auto_classify: bool = True
    ) -> str:
        """添加新记忆"""
        memory_id = str(uuid.uuid4())
        
        # 自动分类
        if auto_classify and memory_type is None:
            classification = self.classifier.classify(content)
            memory_type = max(classification.items(), key=lambda x: x[1])[0]
        
        memory = {
            "id": memory_id,
            "content": content,
            "importance": max(0.0, min(1.0, importance)),
            "type": memory_type or "其他",
            "tags": tags or [],
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "access_count": 0,
            "decay": 0.0,
            "metadata": metadata or {}
        }
        
        # 添加到主存储
        self.memories[memory_id] = memory
        
        # 添加到辅助存储
        self.faiss_manager.add_memory(memory_id, content)
        self.memory_graph.add_memory(memory_id, memory)
        
        self.save_memories()
        logger.info(f"已添加新记忆: {content[:50]}...")
        return memory_id
    
    def extract_and_add_memories(self, text: str, conversation_context: List[Dict[str, Any]] = None) -> List[str]:
        """从文本中提取并添加记忆"""
        extracted = self.extractor.extract_from_text(text, conversation_context)
        memory_ids = []
        
        for memory_data in extracted:
            memory_id = self.add_memory(
                content=memory_data["content"],
                importance=memory_data["importance"],
                memory_type=memory_data["type"],
                tags=memory_data.get("keywords", []),
                auto_classify=False
            )
            memory_ids.append(memory_id)
        
        return memory_ids
    
    def search_memories(
        self, 
        query: str, 
        limit: int = 5, 
        min_importance: float = 0.0,
        memory_type: str = None,
        use_semantic: bool = True
    ) -> List[Dict[str, Any]]:
        """搜索相关记忆"""
        results = []
        
        if use_semantic:
            # 语义搜索
            semantic_results = self.faiss_manager.search_similar(query, limit * 2)  # 获取更多结果用于过滤
            
            for result in semantic_results:
                memory_id = result["memory_id"]
                if memory_id in self.memories:
                    memory = self.memories[memory_id]
                    
                    # 应用过滤器
                    if self._passes_filters(memory, min_importance, memory_type):
                        results.append({
                            "memory": memory,
                            "score": result["similarity"],
                            "type": "semantic"
                        })
        else:
            # 关键词搜索
            for memory_id, memory in self.memories.items():
                if query.lower() in memory["content"].lower():
                    # 应用过滤器
                    if self._passes_filters(memory, min_importance, memory_type):
                        # 计算简单匹配分数
                        score = len(query) / len(memory["content"])
                        results.append({
                            "memory": memory,
                            "score": score,
                            "type": "keyword"
                        })
        
        # 按分数排序并返回前N个结果
        results.sort(key=lambda x: x["score"], reverse=True)
        return [result["memory"] for result in results[:limit]]
    
    def _passes_filters(self, memory: Dict[str, Any], min_importance: float, memory_type: str) -> bool:
        """检查记忆是否通过过滤器"""
        current_importance = self._calculate_current_importance(memory)
        
        if current_importance < min_importance:
            return False
        
        if memory_type and memory.get("type") != memory_type:
            return False
        
        return True
    
    def _calculate_current_importance(self, memory: Dict[str, Any]) -> float:
        """计算记忆的当前重要性（考虑衰减）"""
        importance = memory.get("importance", 0.5)
        decay = memory.get("decay", 0.0)
        
        # 如果有衰减配置，计算时间衰减
        if "created_at" in memory:
            created_at = datetime.fromisoformat(memory["created_at"])
            days_passed = (datetime.now() - created_at).days
            decay = min(0.9, days_passed * 0.1)  # 每天衰减10%，最大衰减90%
        
        return importance * (1 - decay)
    
    def get_associated_memories(self, memory_id: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """获取关联记忆"""
        associations = self.memory_graph.get_associated_memories(memory_id, max_results)
        results = []
        
        for assoc in associations:
            assoc_id = assoc["memory_id"]
            if assoc_id in self.memories:
                memory = self.memories[assoc_id]
                results.append({
                    "memory": memory,
                    "relation_type": assoc["relation_type"],
                    "strength": assoc["strength"]
                })
        
        return results
    
    def add_association(self, memory_id_1: str, memory_id_2: str, relation_type: str, strength: float = 1.0):
        """添加记忆关联"""
        if memory_id_1 in self.memories and memory_id_2 in self.memories:
            return self.memory_graph.add_association(memory_id_1, memory_id_2, relation_type, strength)
        return False
    
    def export_memories(self, file_path: str, format: str = "json") -> bool:
        """导出记忆到文件"""
        try:
            if format == "json":
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.memories, f, ensure_ascii=False, indent=2)
            elif format == "csv":
                import csv
                with open(file_path, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["ID", "Content", "Type", "Importance", "Tags", "Created At"])
                    for memory_id, memory in self.memories.items():
                        writer.writerow([
                            memory_id,
                            memory.get("content", ""),
                            memory.get("type", ""),
                            memory.get("importance", 0),
                            ",".join(memory.get("tags", [])),
                            memory.get("created_at", "")
                        ])
            else:
                logger.error(f"不支持的导出格式: {format}")
                return False
            
            logger.info(f"已导出 {len(self.memories)} 条记忆到 {file_path}")
            return True
        except Exception as e:
            logger.error(f"导出记忆失败: {e}")
            return False
    
    def import_memories(self, file_path: str, format: str = "json") -> bool:
        """从文件导入记忆"""
        try:
            if format == "json":
                with open(file_path, 'r', encoding='utf-8') as f:
                    imported_memories = json.load(f)
                
                # 合并记忆
                for memory_id, memory in imported_memories.items():
                    if memory_id not in self.memories:
                        self.memories[memory_id] = memory
                        
                        # 添加到辅助存储
                        self.faiss_manager.add_memory(memory_id, memory["content"])
                        self.memory_graph.add_memory(memory_id, memory)
            
            elif format == "csv":
                import csv
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        memory_id = row.get("ID", str(uuid.uuid4()))
                        if memory_id not in self.memories:
                            memory = {
                                "id": memory_id,
                                "content": row.get("Content", ""),
                                "type": row.get("Type", "其他"),
                                "importance": float(row.get("Importance", 0.5)),
                                "tags": row.get("Tags", "").split(",") if row.get("Tags") else [],
                                "created_at": row.get("Created At", datetime.now().isoformat()),
                                "last_accessed": datetime.now().isoformat(),
                                "access_count": 0,
                                "decay": 0.0,
                                "metadata": {}
                            }
                            
                            self.memories[memory_id] = memory
                            
                            # 添加到辅助存储
                            self.faiss_manager.add_memory(memory_id, memory["content"])
                            self.memory_graph.add_memory(memory_id, memory)
            else:
                logger.error(f"不支持的导入格式: {format}")
                return False
            
            self.save_memories()
            logger.info(f"已从 {file_path} 导入 {len(imported_memories)} 条记忆")
            return True
        except Exception as e:
            logger.error(f"导入记忆失败: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取记忆统计信息"""
        total_memories = len(self.memories)
        
        # 按类型统计
        type_counts = {}
        for memory in self.memories.values():
            mem_type = memory.get("type", "其他")
            type_counts[mem_type] = type_counts.get(mem_type, 0) + 1
        
        # 计算平均重要性
        avg_importance = sum(m.get("importance", 0) for m in self.memories.values()) / total_memories if total_memories > 0 else 0
        
        # 获取图统计
        graph_stats = {
            "nodes": self.memory_graph.graph.number_of_nodes(),
            "edges": self.memory_graph.graph.number_of_edges(),
            "clusters": len(list(self.memory_graph.get_clusters()))
        }
        
        return {
            "total_memories": total_memories,
            "type_counts": type_counts,
            "average_importance": avg_importance,
            "graph_stats": graph_stats
        }