import os
import sys
import json
import uuid
import logging
import asyncio
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Set

# 添加当前目录到路径，确保模块导入正常
sys.path.append(os.path.dirname(__file__))

from astrbot.api.star import Context, Star, register
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api import logger as astrbot_logger

class MemoryAssociationManager:
    """记忆关联管理器"""
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self.associations = {}  # {memory_id: {related_id: strength}}
        self.load_associations()
    
    def load_associations(self):
        """加载关联数据"""
        try:
            assoc_path = os.path.join(self.storage_path, "associations.json")
            if os.path.exists(assoc_path):
                with open(assoc_path, 'r', encoding='utf-8') as f:
                    self.associations = json.load(f)
                astrbot_logger.info(f"Loaded {sum(len(v) for v in self.associations.values())} associations")
        except Exception as e:
            astrbot_logger.error(f"Failed to load associations: {e}")
            self.associations = {}
    
    def save_associations(self):
        """保存关联数据"""
        try:
            assoc_path = os.path.join(self.storage_path, "associations.json")
            with open(assoc_path, 'w', encoding='utf-8') as f:
                json.dump(self.associations, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            astrbot_logger.error(f"Failed to save associations: {e}")
            return False
    
    def add_association(self, memory_id: str, related_id: str, strength: float = 1.0):
        """添加记忆关联"""
        if memory_id not in self.associations:
            self.associations[memory_id] = {}
        if related_id not in self.associations:
            self.associations[related_id] = {}
        
        self.associations[memory_id][related_id] = strength
        self.associations[related_id][memory_id] = strength
        
        self.save_associations()
        return True
    
    def remove_association(self, memory_id: str, related_id: str):
        """移除记忆关联"""
        if memory_id in self.associations and related_id in self.associations[memory_id]:
            del self.associations[memory_id][related_id]
        if related_id in self.associations and memory_id in self.associations[related_id]:
            del self.associations[related_id][memory_id]
        
        self.save_associations()
        return True
    
    def get_associated_memories(self, memory_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """获取关联记忆"""
        if memory_id not in self.associations:
            return []
        
        associations = []
        for related_id, strength in self.associations[memory_id].items():
            associations.append({
                "memory_id": related_id,
                "strength": strength
            })
        
        # 按关联强度排序
        associations.sort(key=lambda x: x["strength"], reverse=True)
        return associations[:limit]
    
    def auto_create_associations(self, memory_id: str, content: str, all_memories: Dict[str, Any], threshold: float = 0.3):
        """自动创建关联"""
        try:
            # 简单的基于关键词的关联
            keywords = self._extract_keywords(content)
            created_count = 0
            
            for other_id, other_memory in all_memories.items():
                if other_id == memory_id:
                    continue
                
                other_content = other_memory.get("content", "")
                other_keywords = self._extract_keywords(other_content)
                
                # 计算关键词重叠度
                overlap = len(set(keywords) & set(other_keywords))
                total_unique = len(set(keywords) | set(other_keywords))
                
                if total_unique > 0:
                    similarity = overlap / total_unique
                    if similarity >= threshold:
                        self.add_association(memory_id, other_id, similarity)
                        created_count += 1
            
            return created_count
        except Exception as e:
            astrbot_logger.error(f"Auto create associations failed: {e}")
            return 0
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        try:
            import jieba.analyse
            return jieba.analyse.extract_tags(text, topK=10)
        except:
            # 简单的分词后备方案
            return [word for word in text.split() if len(word) > 1]

class AutoMemoryExtractor:
    """自动记忆提取器"""
    def __init__(self, min_importance: float = 0.3):
        self.min_importance = min_importance
    
    def extract_from_conversation(self, message: str, conversation_history: List[Dict] = None) -> List[Dict[str, Any]]:
        """从对话中提取记忆"""
        memories = []
        
        # 检测可能的重要信息
        importance = self._calculate_importance(message, conversation_history)
        
        if importance >= self.min_importance:
            memory_type = self._classify_message_type(message)
            
            memory = {
                "content": message,
                "importance": importance,
                "type": memory_type,
                "source": "auto_extract",
                "extracted_at": datetime.now().isoformat()
            }
            memories.append(memory)
        
        return memories
    
    def _calculate_importance(self, message: str, conversation_history: List[Dict] = None) -> float:
        """计算消息重要性"""
        importance = 0.1
        
        # 包含个人信息
        personal_indicators = ["我", "我的", "自己", "个人"]
        if any(indicator in message for indicator in personal_indicators):
            importance += 0.3
        
        # 包含偏好信息
        preference_indicators = ["喜欢", "讨厌", "爱", "恨", "偏好", "习惯"]
        if any(indicator in message for indicator in preference_indicators):
            importance += 0.4
        
        # 包含事实信息
        fact_indicators = ["是", "有", "在", "属于", "知道", "记得"]
        if any(indicator in message for indicator in fact_indicators):
            importance += 0.2
        
        # 包含时间信息
        time_indicators = ["昨天", "今天", "明天", "上周", "去年"]
        if any(indicator in message for indicator in time_indicators):
            importance += 0.2
        
        # 对话上下文增强
        if conversation_history:
            # 检查是否是重要问题的回答
            last_user_msg = None
            for msg in reversed(conversation_history):
                if msg.get("role") == "user":
                    last_user_msg = msg.get("content", "")
                    break
            
            if last_user_msg and any(q in last_user_msg for q in ["什么", "为什么", "怎么", "如何", "吗？"]):
                importance += 0.3
        
        return min(importance, 1.0)
    
    def _classify_message_type(self, message: str) -> str:
        """分类消息类型"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['喜欢', '讨厌', '爱', '恨', '偏好']):
            return 'preference'
        elif any(word in message_lower for word in ['认为', '觉得', '想', '应该']):
            return 'opinion'
        elif any(word in message_lower for word in ['昨天', '今天', '明天', '小时', '分钟']):
            return 'event'
        elif any(word in message_lower for word in ['是', '有', '在', '属于']):
            return 'fact'
        else:
            return 'other'

class DataExportManager:
    """数据导出管理器"""
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
    
    def export_memories(self, memories: Dict[str, Any], format: str = "json") -> str:
        """导出记忆数据"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if format == "json":
                filename = f"memories_export_{timestamp}.json"
                filepath = os.path.join(self.storage_path, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(memories, f, ensure_ascii=False, indent=2)
                
                return filepath
            
            elif format == "csv":
                import csv
                filename = f"memories_export_{timestamp}.csv"
                filepath = os.path.join(self.storage_path, filename)
                
                with open(filepath, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["ID", "Content", "Type", "Importance", "Created At", "Last Accessed"])
                    
                    for memory_id, memory in memories.items():
                        writer.writerow([
                            memory_id,
                            memory.get("content", ""),
                            memory.get("type", ""),
                            memory.get("importance", 0),
                            memory.get("created_at", ""),
                            memory.get("last_accessed", "")
                        ])
                
                return filepath
            
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            astrbot_logger.error(f"Export memories failed: {e}")
            return None
    
    def import_memories(self, filepath: str, format: str = "json") -> Dict[str, Any]:
        """导入记忆数据"""
        try:
            if format == "json":
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            elif format == "csv":
                import csv
                memories = {}
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        memory_id = row.get("ID", str(uuid.uuid4()))
                        memory = {
                            "id": memory_id,
                            "content": row.get("Content", ""),
                            "type": row.get("Type", "other"),
                            "importance": float(row.get("Importance", 0.5)),
                            "created_at": row.get("Created At", datetime.now().isoformat()),
                            "last_accessed": datetime.now().isoformat(),
                            "access_count": 0
                        }
                        memories[memory_id] = memory
                
                return memories
            
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            astrbot_logger.error(f"Import memories failed: {e}")
            return {}

class MemoryOrganizer:
    """记忆梳理器 - 使用AI模型智能整理记忆"""
    
    def __init__(self, context: Context):
        self.context = context
        self.available_models = {}
        self._discover_models()
    
    def _discover_models(self):
        """发现可用的AI模型"""
        try:
            # 获取所有可用的LLM提供商
            providers = self.context.get_all_providers()
            astrbot_logger.info(f"Found {len(providers)} providers in context")
            
            for provider in providers:
                provider_id = getattr(provider, 'id', 'unknown')
                provider_name = getattr(provider, 'name', 'Unknown')
                self.available_models[provider_id] = {
                    'name': provider_name,
                    'provider': provider
                }
                astrbot_logger.info(f"Discovered model: {provider_id} - {provider_name}")
            
            astrbot_logger.info(f"Total discovered models: {len(self.available_models)}")
        except Exception as e:
            astrbot_logger.error(f"Failed to discover models: {e}")
    
    async def organize_memories(self, memories: List[Dict[str, Any]], 
                            model_id: str = None,
                            tasks: List[str] = None) -> Dict[str, Any]:
        """使用AI模型梳理记忆 - 增强错误处理"""
        if not tasks:
            tasks = ["categorize", "summarize", "suggest_associations"]
        
        provider = None
        if model_id and model_id in self.available_models:
            provider = self.available_models[model_id]['provider']
            astrbot_logger.info(f"Using specified model: {model_id}")
        else:
            # 使用默认提供商
            provider = self.context.get_using_provider()
            if provider:
                astrbot_logger.info(f"Using default provider: {getattr(provider, 'name', 'Unknown')}")
            else:
                astrbot_logger.warning("No default provider available")
                return {"error": "No available AI model found"}
        
        if not provider:
            return {"error": "No available AI model found"}
        
        try:
            results = {}
            
            # 准备记忆文本
            memory_texts = []
            for memory in memories:
                memory_texts.append(f"记忆ID: {memory.get('id', 'unknown')}")
                memory_texts.append(f"内容: {memory.get('content', '')}")
                memory_texts.append(f"类型: {memory.get('type', 'unknown')}")
                memory_texts.append(f"重要性: {memory.get('importance', 0.5)}")
                memory_texts.append("---")
            
            memory_context = "\n".join(memory_texts)
            
            # 根据任务生成提示
            for task in tasks:
                try:
                    if task == "categorize":
                        prompt = self._build_categorize_prompt(memory_context)
                        response = await provider.text_chat(prompt=prompt)
                        results["categorization"] = self._parse_categorization_response(response.content)
                    
                    elif task == "summarize":
                        prompt = self._build_summarize_prompt(memory_context)
                        response = await provider.text_chat(prompt=prompt)
                        results["summary"] = response.content
                    
                    elif task == "find_duplicates":
                        prompt = self._build_duplicate_prompt(memory_context)
                        response = await provider.text_chat(prompt=prompt)
                        results["duplicates"] = self._parse_duplicate_response(response.content)
                    
                    elif task == "suggest_associations":
                        prompt = self._build_association_prompt(memory_context)
                        response = await provider.text_chat(prompt=prompt)
                        results["associations"] = self._parse_association_response(response.content)
                    
                    elif task == "suggest_importance":
                        prompt = self._build_importance_prompt(memory_context)
                        response = await provider.text_chat(prompt=prompt)
                        results["importance_suggestions"] = self._parse_importance_response(response.content)
                    
                    elif task == "sentiment_analysis":
                        prompt = self._build_sentiment_prompt(memory_context)
                        response = await provider.text_chat(prompt=prompt)
                        results["sentiment_analysis"] = self._parse_sentiment_response(response.content)
                        
                except Exception as task_error:
                    astrbot_logger.error(f"Task {task} failed: {task_error}")
                    results[f"{task}_error"] = str(task_error)
            
            return results
            
        except Exception as e:
            astrbot_logger.error(f"Memory organization failed: {e}")
            return {"error": f"Organization failed: {str(e)}"}
    
    def _build_categorize_prompt(self, memory_context: str) -> str:
        """构建分类提示"""
        return f"""请分析以下记忆内容，并建议更好的分类方式。当前分类有：事实(fact)、观点(opinion)、用户偏好(preference)、事件(event)、其他(other)。

请为每段记忆建议更准确的分类，并可以建议新的分类类别。

记忆内容：
{memory_context}

请以JSON格式回复，包含：
1. memory_id: 记忆ID
2. suggested_category: 建议的分类
3. reason: 分类理由
4. confidence: 置信度(0-1)

格式示例：
[
{{
    "memory_id": "记忆ID",
    "suggested_category": "新分类",
    "reason": "分类理由",
    "confidence": 0.9
}}
]"""
    
    def _build_summarize_prompt(self, memory_context: str) -> str:
        """构建总结提示"""
        return f"""请总结以下记忆库的主要内容、主题分布和关键信息：

{memory_context}

请提供：
1. 主要主题和类别
2. 最重要的几个记忆点
3. 记忆库的整体特点
4. 建议的改进方向"""
    
    def _build_duplicate_prompt(self, memory_context: str) -> str:
        """构建重复检测提示"""
        return f"""请分析以下记忆内容，找出可能重复或高度相似的记忆对：

{memory_context}

请以JSON格式回复可能重复的记忆对：
[
{{
    "memory_id_1": "记忆ID1",
    "memory_id_2": "记忆ID2", 
    "similarity_reason": "重复原因",
    "suggestion": "处理建议(合并/删除/保留)"
}}
]"""
    
    def _build_association_prompt(self, memory_context: str) -> str:
        """构建关联建议提示"""
        return f"""请分析以下记忆内容，建议应该建立关联的记忆对：

{memory_context}

请以JSON格式回复建议的关联：
[
{{
    "memory_id_1": "记忆ID1",
    "memory_id_2": "记忆ID2",
    "relation_type": "关联类型(如: 因果关系/时间顺序/主题相关等)",
    "relation_strength": 关联强度(0-1),
    "reason": "关联理由"
}}
]"""
    
    def _build_importance_prompt(self, memory_context: str) -> str:
        """构建重要性评估提示"""
        return f"""请重新评估以下记忆的重要性(0-1分)，1分最重要：

{memory_context}

请以JSON格式回复重要性建议：
[
{{
    "memory_id": "记忆ID",
    "suggested_importance": 新重要性分数,
    "reason": "调整理由"
}}
]"""

    def _build_sentiment_prompt(self, memory_context: str) -> str:
        """构建情感分析提示"""
        return f"""请分析以下记忆内容的情感倾向和情绪状态：

{memory_context}

请以JSON格式回复情感分析结果：
[
{{
    "memory_id": "记忆ID",
    "sentiment": "情感倾向(积极/消极/中性)",
    "emotion": "具体情绪",
    "intensity": "强度(0-1)",
    "reason": "分析理由"
}}
]"""
    
    def _parse_categorization_response(self, response: str) -> List[Dict]:
        """解析分类响应"""
        try:
            # 尝试提取JSON部分
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # 如果找不到JSON，返回原始响应
                return [{"raw_response": response}]
        except:
            return [{"raw_response": response}]
    
    def _parse_duplicate_response(self, response: str) -> List[Dict]:
        """解析重复检测响应"""
        return self._parse_categorization_response(response)
    
    def _parse_association_response(self, response: str) -> List[Dict]:
        """解析关联建议响应"""
        return self._parse_categorization_response(response)
    
    def _parse_importance_response(self, response: str) -> List[Dict]:
        """解析重要性评估响应"""
        return self._parse_categorization_response(response)
    
    def _parse_sentiment_response(self, response: str) -> List[Dict]:
        """解析情感分析响应"""
        return self._parse_categorization_response(response)
    
    def get_available_models(self) -> Dict[str, Any]:
        """获取可用模型列表"""
        return self.available_models

class EnhancedMemoryManager:
    """增强记忆管理器 - 优化版"""
    
    def __init__(self, storage_path: str, context: Context = None, 
                 # AI模型配置参数
                 use_framework_models: bool = True,
                 primary_model_id: str = "",
                 auto_extraction_model_id: str = "", 
                 classification_model_id: str = "",
                 fallback_to_default: bool = True,
                 model_load_strategy: str = "dynamic",
                 processing_tasks: List[str] = None,
                 batch_processing_size: int = 10,
                 max_concurrent_requests: int = 3,
                 model_cache_ttl: int = 60,
                 # 自动提取配置
                 auto_extract_min_importance: float = 0.3,
                 extraction_prompt: str = None):
        
        self.storage_path = storage_path
        self.context = context
        self.memories = {}
        self.embedding_model = None
        self.association_manager = MemoryAssociationManager(storage_path)
        self.extractor = AutoMemoryExtractor()
        self.export_manager = DataExportManager(storage_path)
        self.organizer = MemoryOrganizer(context) if context else None
        
        # ==================== 保存AI模型配置 ====================
        self.use_framework_models = use_framework_models
        self.primary_model_id = primary_model_id
        self.auto_extraction_model_id = auto_extraction_model_id
        self.classification_model_id = classification_model_id
        self.fallback_to_default = fallback_to_default
        self.model_load_strategy = model_load_strategy
        self.processing_tasks = processing_tasks or ["categorize", "summarize", "suggest_associations"]
        self.batch_processing_size = batch_processing_size
        self.max_concurrent_requests = max_concurrent_requests
        self.model_cache_ttl = model_cache_ttl
        self.auto_extract_min_importance = auto_extract_min_importance
        self.extraction_prompt = extraction_prompt or "请从以下对话中提取可能重要的信息作为长期记忆。重点关注：个人偏好、重要事实、情感表达、重复提到的话题。"
        
        # 模型缓存和并发控制
        self.model_cache = {}
        self.last_model_access = {}
        self._concurrent_requests = 0
        self._request_lock = asyncio.Lock()
        # ==================== 配置保存结束 ====================
        
        # 确保存储路径存在
        self._ensure_storage_path()
        self._initialize_components()
        self.load_memories()
        
        astrbot_logger.info(f"EnhancedMemoryManager initialized with {len(self.memories)} memories")
        astrbot_logger.info(f"AI Framework Models: {self.use_framework_models}")
        astrbot_logger.info(f"Primary Model: {self.primary_model_id}")

    def _ensure_storage_path(self):
        """确保存储路径存在"""
        try:
            # 规范化路径，避免重复的data目录
            normalized_path = os.path.normpath(self.storage_path)
            os.makedirs(normalized_path, exist_ok=True)
            astrbot_logger.info(f"Created storage path: {normalized_path}")
        except Exception as e:
            astrbot_logger.error(f"Failed to create storage path: {e}")
            import tempfile
            self.storage_path = os.path.join(tempfile.gettempdir(), "enhanced_memory")
            os.makedirs(self.storage_path, exist_ok=True)
            astrbot_logger.info(f"Using fallback storage: {self.storage_path}")
    
    def _initialize_components(self):
        """初始化组件"""
        # 检查并初始化嵌入模型
        try:
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            astrbot_logger.info("Embedding model initialized")
        except ImportError:
            astrbot_logger.warning("sentence-transformers not available, semantic search disabled")
        except Exception as e:
            astrbot_logger.error(f"Failed to initialize embedding model: {e}")
    
    def load_memories(self):
        """加载记忆"""
        try:
            memories_path = os.path.join(self.storage_path, "memories.json")
            if os.path.exists(memories_path):
                with open(memories_path, 'r', encoding='utf-8') as f:
                    self.memories = json.load(f)
                astrbot_logger.info(f"Loaded {len(self.memories)} memories")
            else:
                self.memories = {}
                astrbot_logger.info("No existing memories found, starting fresh")
        except Exception as e:
            astrbot_logger.error(f"Failed to load memories: {e}")
            self.memories = {}
    
    def save_memories(self):
        """保存记忆"""
        try:
            memories_path = os.path.join(self.storage_path, "memories.json")
            with open(memories_path, 'w', encoding='utf-8') as f:
                json.dump(self.memories, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            astrbot_logger.error(f"Failed to save memories: {e}")
            return False
    
    async def _acquire_request_slot(self):
        """获取请求槽位，控制并发数量"""
        async with self._request_lock:
            while self._concurrent_requests >= self.max_concurrent_requests:
                await asyncio.sleep(0.1)
            self._concurrent_requests += 1

    def _release_request_slot(self):
        """释放请求槽位"""
        self._concurrent_requests = max(0, self._concurrent_requests - 1)

    def _get_model_for_task(self, task_type: str = "processing"):
        """根据任务类型获取合适的AI模型"""
        try:
            if not self.use_framework_models or not hasattr(self, 'organizer') or not self.organizer:
                return None
            
            # 根据任务类型选择模型ID
            model_id = self.primary_model_id
            if task_type == "auto_extraction" and self.auto_extraction_model_id:
                model_id = self.auto_extraction_model_id
            elif task_type == "classification" and self.classification_model_id:
                model_id = self.classification_model_id
            
            # 检查模型缓存
            cache_key = f"{task_type}_{model_id}"
            current_time = datetime.now().timestamp()
            
            if cache_key in self.model_cache:
                last_access = self.last_model_access.get(cache_key, 0)
                # 检查缓存是否过期
                if current_time - last_access < self.model_cache_ttl * 60:
                    self.last_model_access[cache_key] = current_time
                    return self.model_cache[cache_key]
            
            # 获取模型
            provider = None
            if model_id and model_id in self.organizer.available_models:
                provider = self.organizer.available_models[model_id]['provider']
                astrbot_logger.info(f"Using specified model for {task_type}: {model_id}")
            elif self.fallback_to_default:
                # 回退到默认模型
                if hasattr(self, 'context') and self.context:
                    provider = self.context.get_using_provider()
                    if provider:
                        astrbot_logger.info(f"Using default provider for {task_type}: {getattr(provider, 'name', 'Unknown')}")
            
            # 缓存模型
            if provider:
                self.model_cache[cache_key] = provider
                self.last_model_access[cache_key] = current_time
            
            return provider
            
        except Exception as e:
            astrbot_logger.error(f"Error getting model for task {task_type}: {e}")
            return None

    def add_memory(self, content: str, importance: float = 0.5, memory_type: str = None, 
                  auto_associate: bool = True, **kwargs):
        """添加记忆"""
        memory_id = str(uuid.uuid4())
        
        # 自动分类记忆类型
        if memory_type is None:
            memory_type = self._classify_memory_type(content)
        
        memory_data = {
            "id": memory_id,
            "content": content,
            "importance": importance,
            "type": memory_type,
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "access_count": 0
        }
        
        # 尝试提取关键词
        try:
            import jieba.analyse
            keywords = jieba.analyse.extract_tags(content, topK=5)
            memory_data["keywords"] = keywords
        except ImportError:
            memory_data["keywords"] = []
        
        self.memories[memory_id] = memory_data
        self.save_memories()
        
        # 自动创建关联
        if auto_associate and len(self.memories) > 1:
            created_count = self.association_manager.auto_create_associations(memory_id, content, self.memories)
            astrbot_logger.info(f"Auto created {created_count} associations for memory {memory_id}")
        
        astrbot_logger.info(f"Added memory: {content[:50]}...")
        return memory_id
    
    def delete_memory(self, memory_id: str):
        """删除记忆"""
        if memory_id in self.memories:
            # 移除关联
            if memory_id in self.association_manager.associations:
                related_ids = list(self.association_manager.associations[memory_id].keys())
                for related_id in related_ids:
                    self.association_manager.remove_association(memory_id, related_id)
                del self.association_manager.associations[memory_id]
            
            # 移除记忆
            del self.memories[memory_id]
            self.save_memories()
            self.association_manager.save_associations()
            return True
        return False
    
    def update_memory(self, memory_id: str, **kwargs):
        """更新记忆"""
        if memory_id in self.memories:
            memory = self.memories[memory_id]
            memory.update(kwargs)
            memory["last_accessed"] = datetime.now().isoformat()
            self.save_memories()
            return True
        return False
    
    def _classify_memory_type(self, content: str) -> str:
        """分类记忆类型"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['喜欢', '讨厌', '爱', '恨', '偏好']):
            return 'preference'
        elif any(word in content_lower for word in ['认为', '觉得', '想', '应该']):
            return 'opinion'
        elif any(word in content_lower for word in ['昨天', '今天', '明天', '小时', '分钟']):
            return 'event'
        elif any(word in content_lower for word in ['是', '有', '在', '属于']):
            return 'fact'
        else:
            return 'other'
        
    def search_memories(self, query: str, limit: int = 5, use_semantic: bool = True, 
                       include_associated: bool = False, **kwargs):
        """搜索记忆 - 修复版"""
        results = []
        
        # 调试信息
        astrbot_logger.info(f"搜索查询: '{query}', 记忆库总数: {len(self.memories)}")
        
        # 首先进行关键词搜索（确保基础搜索工作）
        query_lower = query.lower()
        match_count = 0
        
        for memory_id, memory in self.memories.items():
            content = memory.get("content", "")
            content_lower = content.lower()
            
            # 改进的搜索逻辑：检查查询是否在内容中
            if query_lower in content_lower:
                memory_copy = memory.copy()
                memory_copy["match_type"] = "keyword"
                memory_copy["similarity"] = 1.0
                results.append(memory_copy)
                match_count += 1
                astrbot_logger.info(f"关键词匹配: {content[:50]}...")
        
        astrbot_logger.info(f"关键词搜索找到 {match_count} 条匹配")
        
        # 如果启用了语义搜索且有嵌入模型，尝试语义搜索
        if use_semantic and self.embedding_model is not None and not results:
            try:
                semantic_results = self._semantic_search(query, limit * 2)
                for result in semantic_results:
                    memory_id = result["memory_id"]
                    if memory_id in self.memories:
                        memory = self.memories[memory_id].copy()
                        memory["similarity"] = result["similarity"]
                        memory["match_type"] = "semantic"
                        results.append(memory)
            except Exception as e:
                astrbot_logger.error(f"语义搜索失败: {e}")
        
        # 包含关联记忆
        if include_associated and results:
            all_results = results.copy()
            for memory in results:
                associated = self.association_manager.get_associated_memories(memory["id"], limit=3)
                for assoc in associated:
                    assoc_id = assoc["memory_id"]
                    if assoc_id in self.memories and assoc_id not in [r["id"] for r in all_results]:
                        assoc_memory = self.memories[assoc_id].copy()
                        assoc_memory["association_strength"] = assoc["strength"]
                        assoc_memory["match_type"] = "associated"
                        all_results.append(assoc_memory)
            results = all_results
        
        # 按重要性排序
        results.sort(key=lambda x: x.get("importance", 0), reverse=True)
        
        astrbot_logger.info(f"搜索完成，找到 {len(results)} 条结果")
        return results[:limit]
    
    def _semantic_search(self, query: str, k: int = 5):
        """语义搜索"""
        if not self.embedding_model:
            return []
        
        try:
            import numpy as np
            
            # 生成查询向量
            query_embedding = self.embedding_model.encode([query])
            query_embedding = np.array(query_embedding, dtype='float32')
            
            # 构建临时索引进行搜索
            embeddings = []
            memory_ids = []
            
            for memory_id, memory in self.memories.items():
                memory_embedding = self.embedding_model.encode([memory["content"]])
                embeddings.append(memory_embedding[0])
                memory_ids.append(memory_id)
            
            if not embeddings:
                return []
            
            embeddings = np.array(embeddings, dtype='float32')
            
            # 使用FAISS如果可用，否则使用numpy计算
            try:
                import faiss
                index = faiss.IndexFlatL2(embeddings.shape[1])
                index.add(embeddings)
                distances, indices = index.search(query_embedding, min(k, len(embeddings)))
            except ImportError:
                # 使用numpy计算相似度
                distances = np.linalg.norm(embeddings - query_embedding, axis=1)
                indices = np.argsort(distances)[:k]
                distances = distances[indices].reshape(1, -1)
                indices = indices.reshape(1, -1)
            
            results = []
            for i, idx in enumerate(indices[0]):
                if idx < len(memory_ids):
                    results.append({
                        "memory_id": memory_ids[idx],
                        "similarity": 1.0 / (1.0 + distances[0][i]),
                        "distance": distances[0][i]
                    })
            
            return results
            
        except Exception as e:
            astrbot_logger.error(f"Semantic search error: {e}")
            return []
    
    def auto_extract_from_message(self, message: str, conversation_history: List[Dict] = None):
        """从消息自动提取记忆"""
        extracted_memories = self.extractor.extract_from_conversation(message, conversation_history)
        memory_ids = []
        
        for memory_data in extracted_memories:
            memory_id = self.add_memory(
                content=memory_data["content"],
                importance=memory_data["importance"],
                memory_type=memory_data["type"],
                auto_associate=True
            )
            memory_ids.append(memory_id)
        
        return memory_ids

    async def ai_auto_extract(self, message: str, conversation_history: List[Dict] = None) -> List[str]:
        """使用AI模型进行智能记忆提取"""
        if not self.use_framework_models:
            return []
        
        try:
            await self._acquire_request_slot()
            
            extraction_provider = self._get_model_for_task("auto_extraction")
            if not extraction_provider:
                astrbot_logger.warning("No AI model available for auto extraction")
                return []
            
            # 构建提取提示
            context_text = ""
            if conversation_history:
                # 只取最近几条对话作为上下文
                recent_history = conversation_history[-5:]
                context_text = "\n".join([f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" 
                                        for msg in recent_history])
            
            prompt = f"{self.extraction_prompt}\n\n当前对话:\n{context_text}\n\n最新消息: {message}\n\n请提取重要信息作为记忆:"
            
            # 调用AI模型
            response = await extraction_provider.text_chat(prompt=prompt)
            
            if response and response.content:
                # 解析AI返回的记忆内容
                extracted_contents = self._parse_ai_extraction_response(response.content)
                memory_ids = []
                
                for content in extracted_contents:
                    if len(content.strip()) > 10:  # 确保内容足够长
                        memory_id = self.add_memory(
                            content=content,
                            importance=0.7,  # AI提取的记忆默认重要性较高
                            memory_type="ai_extracted",
                            auto_associate=True
                        )
                        memory_ids.append(memory_id)
                        astrbot_logger.info(f"AI extracted memory: {content[:50]}...")
                
                return memory_ids
            
        except Exception as e:
            astrbot_logger.error(f"AI auto extraction failed: {e}")
        finally:
            self._release_request_slot()
        
        return []

    def _parse_ai_extraction_response(self, response: str) -> List[str]:
        """解析AI提取的记忆响应"""
        try:
            # 尝试按行分割并过滤空行
            lines = [line.strip() for line in response.split('\n') if line.strip()]
            
            # 移除编号和标记
            cleaned_lines = []
            for line in lines:
                # 移除行首的编号（如 "1. ", "2. "等）
                line = re.sub(r'^\d+\.\s*', '', line)
                # 移除引号
                line = line.strip('"\'')
                if line and len(line) > 5:  # 确保有实际内容
                    cleaned_lines.append(line)
            
            return cleaned_lines[:5]  # 最多返回5条记忆
            
        except Exception as e:
            astrbot_logger.error(f"Failed to parse AI extraction response: {e}")
            return []

    def auto_extract_with_model(self, message: str, conversation_history: List[Dict] = None) -> List[str]:
        """智能记忆提取 - 结合规则和AI"""
        memory_ids = []
        
        # 首先使用规则提取
        rule_based_ids = self.auto_extract_from_message(message, conversation_history)
        memory_ids.extend(rule_based_ids)
        
        # 如果启用了AI模型，并且规则提取的结果较少，使用AI提取
        if (self.use_framework_models and 
            len(rule_based_ids) <= 1 and 
            len(message) > 20):  # 消息足够长时才使用AI
            
            # 异步调用AI提取（不等待结果，避免阻塞）
            asyncio.create_task(self._async_ai_extract(message, conversation_history))
        
        return memory_ids

    async def _async_ai_extract(self, message: str, conversation_history: List[Dict] = None):
        """异步执行AI提取"""
        try:
            ai_memory_ids = await self.ai_auto_extract(message, conversation_history)
            if ai_memory_ids:
                astrbot_logger.info(f"AI auto extracted {len(ai_memory_ids)} memories")
        except Exception as e:
            astrbot_logger.error(f"Async AI extraction failed: {e}")
    
    def add_manual_association(self, memory_id_1: str, memory_id_2: str, strength: float = 1.0):
        """手动添加关联"""
        return self.association_manager.add_association(memory_id_1, memory_id_2, strength)
    
    def get_associated_memories(self, memory_id: str, limit: int = 5):
        """获取关联记忆"""
        associations = self.association_manager.get_associated_memories(memory_id, limit)
        results = []
        
        for assoc in associations:
            assoc_id = assoc["memory_id"]
            if assoc_id in self.memories:
                memory = self.memories[assoc_id].copy()
                memory["association_strength"] = assoc["strength"]
                results.append(memory)
        
        return results
    
    def export_data(self, format: str = "json"):
        """导出数据"""
        return self.export_manager.export_memories(self.memories, format)
    
    def import_data(self, filepath: str, format: str = "json"):
        """导入数据"""
        imported_memories = self.export_manager.import_memories(filepath, format)
        
        for memory_id, memory in imported_memories.items():
            if memory_id not in self.memories:
                self.memories[memory_id] = memory
        
        self.save_memories()
        return len(imported_memories)
    
    def get_context_memories(self, query: str, limit: int = 3):
        """获取上下文相关记忆（用于AI集成）"""
        relevant_memories = self.search_memories(query, limit=limit, use_semantic=True)
        
        context_text = "相关记忆：\n"
        for i, memory in enumerate(relevant_memories, 1):
            context_text += f"{i}. {memory['content']}\n"
        
        return context_text
    
    async def organize_with_model(self, model_id: str = None, tasks: List[str] = None) -> Dict[str, Any]:
        """使用AI模型梳理记忆 - 增强版"""
        if not self.organizer:
            return {"error": "Memory organizer not initialized"}
        
        # 获取所有记忆
        all_memories = list(self.memories.values())
        
        if not all_memories:
            return {"error": "No memories to organize"}
        
        # 使用配置的模型
        if not model_id and self.use_framework_models:
            processing_provider = self._get_model_for_task("processing")
            if processing_provider:
                # 使用配置的模型
                return await self.organizer.organize_memories(
                    all_memories, 
                    getattr(processing_provider, 'id', None), 
                    tasks or self.processing_tasks
                )
        
        # 回退到原来的逻辑
        return await self.organizer.organize_memories(all_memories, model_id, tasks or self.processing_tasks)
    
    def apply_organization_results(self, results: Dict[str, Any]) -> Dict[str, int]:
        """应用梳理结果"""
        applied_changes = {
            "categorization": 0,
            "importance_updates": 0,
            "associations_created": 0
        }
        
        try:
            # 应用分类建议
            if "categorization" in results and isinstance(results["categorization"], list):
                for item in results["categorization"]:
                    if "memory_id" in item and "suggested_category" in item:
                        memory_id = item["memory_id"]
                        if memory_id in self.memories:
                            self.memories[memory_id]["type"] = item["suggested_category"]
                            applied_changes["categorization"] += 1
            
            # 应用重要性建议
            if "importance_suggestions" in results and isinstance(results["importance_suggestions"], list):
                for item in results["importance_suggestions"]:
                    if "memory_id" in item and "suggested_importance" in item:
                        memory_id = item["memory_id"]
                        if memory_id in self.memories:
                            new_importance = float(item["suggested_importance"])
                            if 0 <= new_importance <= 1:
                                self.memories[memory_id]["importance"] = new_importance
                                applied_changes["importance_updates"] += 1
            
            # 应用关联建议
            if "associations" in results and isinstance(results["associations"], list):
                for item in results["associations"]:
                    if "memory_id_1" in item and "memory_id_2" in item:
                        memory_id_1 = item["memory_id_1"]
                        memory_id_2 = item["memory_id_2"]
                        strength = float(item.get("relation_strength", 0.5))
                        
                        if memory_id_1 in self.memories and memory_id_2 in self.memories:
                            self.association_manager.add_association(memory_id_1, memory_id_2, strength)
                            applied_changes["associations_created"] += 1
            
            # 保存更改
            if any(applied_changes.values()):
                self.save_memories()
                self.association_manager.save_associations()
            
            return applied_changes
            
        except Exception as e:
            astrbot_logger.error(f"Failed to apply organization results: {e}")
            return applied_changes
    
    def get_available_models(self) -> Dict[str, Any]:
        """获取可用模型列表"""
        if self.organizer:
            return self.organizer.get_available_models()
        return {}
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        if not self.organizer:
            return {"error": "Organizer not initialized"}
        
        available_models = self.organizer.get_available_models()
        active_models = {}
        
        # 获取当前激活的模型
        processing_model = self._get_model_for_task("processing")
        extraction_model = self._get_model_for_task("auto_extraction")
        classification_model = self._get_model_for_task("classification")
        
        if processing_model:
            active_models["processing"] = getattr(processing_model, 'name', 'Unknown')
        if extraction_model:
            active_models["auto_extraction"] = getattr(extraction_model, 'name', 'Unknown')
        if classification_model:
            active_models["classification"] = getattr(classification_model, 'name', 'Unknown')
        
        return {
            "use_framework_models": self.use_framework_models,
            "available_models": {k: v['name'] for k, v in available_models.items()},
            "active_models": active_models,
            "configured_models": {
                "primary": self.primary_model_id,
                "auto_extraction": self.auto_extraction_model_id,
                "classification": self.classification_model_id
            },
            "concurrent_requests": f"{self._concurrent_requests}/{self.max_concurrent_requests}",
            "model_cache_size": len(self.model_cache)
        }
    
    def simple_search(self, query: str, limit: int = 5):
        """简单但有效的搜索方法"""
        results = []
        query_lower = query.lower()
        
        for memory_id, memory in self.memories.items():
            content = memory.get("content", "").lower()
            if query_lower in content:
                results.append(memory)
        
        # 按重要性排序
        results.sort(key=lambda x: x.get("importance", 0), reverse=True)
        return results[:limit]    
    
    def get_stats(self):
        """获取统计信息"""
        total = len(self.memories)
        type_counts = {}
        
        for memory in self.memories.values():
            mem_type = memory.get('type', 'other')
            type_counts[mem_type] = type_counts.get(mem_type, 0) + 1
        
        avg_importance = sum(m.get('importance', 0) for m in self.memories.values()) / total if total > 0 else 0
        
        # 关联统计
        total_associations = sum(len(v) for v in self.association_manager.associations.values())
        
        component_status = {
            "semantic_search": self.embedding_model is not None,
            "auto_extraction": True,
            "association_management": True,
            "data_import_export": True,
            "ai_integration": True,
            "ai_organization": self.organizer is not None
        }
        
        return {
            "total_memories": total,
            "type_counts": type_counts,
            "average_importance": avg_importance,
            "total_associations": total_associations,
            "component_status": component_status,
            "storage_path": self.storage_path
        }

@register(
    "enhanced_memory",
    "xingchenxiangyu", 
    "Enhanced memory plugin with AI-powered organization - 增强记忆插件",
    "1.0.0"  # 更新版本号
)
class EnhancedMemoryPlugin(Star):
    def __init__(self, context: Context, config: Optional[Dict[str, Any]] = None):
        super().__init__(context)
        
        self.context = context
        self.config = config or {}
        self.conversation_history = []
        
        # 修复存储路径问题
        storage_config = self.config.get("storage_config", {})
        storage_path = storage_config.get("storage_path", "plugin_data/enhanced_memory")
        
        # 使用AstrBot的数据目录，但避免重复的data目录
        data_dir = getattr(context, 'data_dir', 'data')
        
        # 如果存储路径已经是绝对路径，直接使用；否则与data_dir拼接
        if os.path.isabs(storage_path):
            self.storage_path = storage_path
        else:
            # 检查存储路径是否已经包含data目录
            if storage_path.startswith('data/'):
                # 如果已经包含data/前缀，直接使用
                self.storage_path = os.path.join(data_dir, storage_path[5:])  # 去掉前面的"data/"
            else:
                # 否则正常拼接
                self.storage_path = os.path.join(data_dir, storage_path)
        
        # 规范化路径，解决Windows/Unix路径分隔符问题
        self.storage_path = os.path.normpath(self.storage_path)
        
        # ==================== AI模型配置读取 ====================
        ai_model_config = self.config.get("ai_model_settings", {})
        self.use_framework_models = ai_model_config.get("use_framework_models", True)
        self.primary_model_id = ai_model_config.get("primary_processing_model", "")
        self.auto_extraction_model_id = ai_model_config.get("auto_extraction_model", "")
        self.classification_model_id = ai_model_config.get("classification_model", "")
        self.fallback_to_default = ai_model_config.get("fallback_to_default", True)
        self.model_load_strategy = ai_model_config.get("model_load_strategy", "dynamic")
        
        # 记忆处理配置
        processing_config = self.config.get("memory_processing_config", {})
        self.processing_tasks = processing_config.get("processing_tasks", ["categorize", "summarize", "suggest_associations"])
        self.auto_process_interval = processing_config.get("auto_process_interval", 7)
        self.process_new_memories = processing_config.get("process_new_memories", True)
        self.batch_processing_size = processing_config.get("batch_processing_size", 10)
        
        # 高级配置
        advanced_config = self.config.get("advanced_settings", {})
        self.max_concurrent_ai_requests = advanced_config.get("max_concurrent_ai_requests", 3)
        self.model_cache_ttl = advanced_config.get("model_cache_ttl", 60)
        
        # 自动提取配置
        auto_extract_config = self.config.get("auto_extraction_config", {})
        self.auto_extract_min_importance = auto_extract_config.get("min_importance", 0.3)
        self.extraction_prompt = auto_extract_config.get("extraction_prompt", "请从以下对话中提取可能重要的信息作为长期记忆。重点关注：个人偏好、重要事实、情感表达、重复提到的话题。")
        # ==================== AI模型配置读取结束 ====================
        
        self.memory_manager = None
        self._initialized = False
        self.auto_extract_enabled = self.config.get("feature_switches", {}).get("auto_extraction_enabled", True)
        self.organization_enabled = self.config.get("feature_switches", {}).get("organization_enabled", True)
        self.ai_integration_enabled = self.config.get("feature_switches", {}).get("ai_integration_enabled", True)
        
        self._initialize_memory_manager()
        
        astrbot_logger.info("Enhanced Memory Plugin v1.0.0 initialized successfully")
        astrbot_logger.info(f"Storage path: {self.storage_path}")
        astrbot_logger.info(f"Auto extraction: {'Enabled' if self.auto_extract_enabled else 'Disabled'}")
        astrbot_logger.info(f"AI Organization: {'Enabled' if self.organization_enabled else 'Disabled'}")
        astrbot_logger.info(f"Use framework models: {self.use_framework_models}")
        astrbot_logger.info(f"Primary model: {self.primary_model_id}")
        astrbot_logger.info(f"Auto extraction model: {self.auto_extraction_model_id}")
        astrbot_logger.info(f"Classification model: {self.classification_model_id}")
        astrbot_logger.info(f"Model load strategy: {self.model_load_strategy}")

    def _initialize_memory_manager(self):
        """初始化内存管理器"""
        try:
            # 传递AI模型配置到记忆管理器
            self.memory_manager = EnhancedMemoryManager(
                self.storage_path, 
                self.context,
                # AI模型配置
                use_framework_models=self.use_framework_models,
                primary_model_id=self.primary_model_id,
                auto_extraction_model_id=self.auto_extraction_model_id,
                classification_model_id=self.classification_model_id,
                fallback_to_default=self.fallback_to_default,
                model_load_strategy=self.model_load_strategy,
                processing_tasks=self.processing_tasks,
                batch_processing_size=self.batch_processing_size,
                max_concurrent_requests=self.max_concurrent_ai_requests,
                model_cache_ttl=self.model_cache_ttl,
                # 自动提取配置
                auto_extract_min_importance=self.auto_extract_min_importance,
                extraction_prompt=self.extraction_prompt
            )
            self._initialized = True
            astrbot_logger.info("Memory manager initialized successfully")
        except Exception as e:
            astrbot_logger.error(f"Failed to initialize memory manager: {e}")
            self._initialized = False

    # ==================== 事件监听器 ====================

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_all_messages(self, event: AstrMessageEvent):
        """监听所有消息，用于自动提取记忆 - 优化版"""
        if not self._initialized or not self.auto_extract_enabled:
            return
        
        try:
            message_content = event.message_str
            
            # 过滤命令消息和过短消息，避免重复记忆
            if (message_content.startswith('/') or 
                len(message_content.strip()) < 5 or
                message_content.strip() in ['', ' ', '。', '！', '？']):
                return
            
            user_id = event.get_sender_id()
            
            # 更新对话历史
            self.conversation_history.append({
                "role": "user",
                "content": message_content,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            })
            
            # 保持历史长度
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]
            
            # 使用智能提取（结合规则和AI）
            extracted_ids = self.memory_manager.auto_extract_with_model(
                message_content, 
                self.conversation_history
            )
            
            if extracted_ids:
                astrbot_logger.info(f"Auto extracted {len(extracted_ids)} memories from message")
                
        except Exception as e:
            astrbot_logger.error(f"Auto extraction failed: {e}")

    @filter.on_llm_request()
    async def on_llm_request(self, event: AstrMessageEvent, req: Any):
        """在LLM请求前注入相关记忆"""
        if not self._initialized:
            return
        
        try:
            # 获取当前消息内容
            current_message = event.message_str
            
            # 搜索相关记忆
            context_memories = self.memory_manager.get_context_memories(current_message, limit=3)
            
            # 如果有相关记忆，添加到系统提示中
            if context_memories and len(context_memories.strip()) > 20:  # 确保不是空内容
                if hasattr(req, 'system_prompt'):
                    req.system_prompt = f"{req.system_prompt}\n\n{context_memories}"
                elif hasattr(req, 'messages') and req.messages:
                    # 添加到系统消息
                    system_message = None
                    for msg in req.messages:
                        if msg.get('role') == 'system':
                            system_message = msg
                            break
                    
                    if system_message:
                        system_message['content'] = f"{system_message['content']}\n\n{context_memories}"
                    else:
                        req.messages.insert(0, {'role': 'system', 'content': context_memories})
                
                astrbot_logger.info("Injected relevant memories into LLM context")
                
        except Exception as e:
            astrbot_logger.error(f"Failed to inject memories into LLM context: {e}")

    # ==================== 命令处理器 ====================

    @filter.command("memo_add", aliases=["记忆添加", "添加记忆"])
    async def memo_add_command(self, event: AstrMessageEvent, content: str):
        """添加记忆"""
        try:
            if not self._initialized:
                yield event.plain_result("❌ 记忆系统未初始化")
                return

            memory_id = self.memory_manager.add_memory(content)
            
            if memory_id:
                yield event.plain_result("✅ 记忆已成功添加！")
            else:
                yield event.plain_result("❌ 添加记忆失败")
                
        except Exception as e:
            astrbot_logger.error(f"Error adding memory: {e}")
            yield event.plain_result("❌ 添加记忆时发生错误")

    @filter.command("memo_delete", aliases=["记忆删除", "删除记忆"])
    async def memo_delete_command(self, event: AstrMessageEvent, memory_id: str):
        """删除记忆"""
        try:
            if not self._initialized:
                yield event.plain_result("❌ 记忆系统未初始化")
                return

            if self.memory_manager.delete_memory(memory_id):
                yield event.plain_result("✅ 记忆已成功删除！")
            else:
                yield event.plain_result("❌ 删除记忆失败，记忆ID不存在")
                
        except Exception as e:
            astrbot_logger.error(f"Error deleting memory: {e}")
            yield event.plain_result("❌ 删除记忆时发生错误")

    @filter.command("memo_search", aliases=["记忆搜索", "搜索记忆"])
    async def memo_search_command(self, event: AstrMessageEvent, query: str, limit: int = 5):
        """搜索记忆 - 增强调试版"""
        try:
            if not self._initialized:
                yield event.plain_result("❌ 记忆系统未初始化")
                return

            astrbot_logger.info(f"开始搜索: '{query}', 限制: {limit}")
        
        # 显示当前记忆总数
            total_memories = len(self.memory_manager.memories)
            astrbot_logger.info(f"当前记忆库总数: {total_memories}")
        
            results = self.memory_manager.simple_search(query, limit=limit)
        
            if results:
                response = f"🔍 找到 {len(results)} 条相关记忆 (共{total_memories}条):\n\n"
                for i, memory in enumerate(results, 1):
                    content = memory['content']
                    mem_type = memory.get('type', '未知')
                    importance = memory.get('importance', 0.5)
                    match_type = memory.get('match_type', 'unknown')
                
                    response += f"{i}. {content}\n"
                    response += f"   类型: {mem_type} | 重要性: {importance:.2f} | 匹配方式: {match_type}"
                
                    if memory.get('similarity'):
                        response += f" | 相似度: {memory['similarity']:.3f}"
                    if memory.get('association_strength'):
                        response += f" | 关联强度: {memory['association_strength']:.3f}"
                
                    response += f" | ID: {memory['id'][:8]}...\n\n"
                
                yield event.plain_result(response)
            else:
                # 显示调试信息
                debug_info = f"❌ 没有找到相关记忆 (搜索: '{query}')\n"
                debug_info += f"当前记忆库: {total_memories} 条记忆\n"
                debug_info += "💡 提示: 尝试使用更简单的关键词或检查记忆内容"
                yield event.plain_result(debug_info)
            
        except Exception as e:
            astrbot_logger.error(f"搜索记忆时发生错误: {e}")
            yield event.plain_result(f"❌ 搜索记忆时发生错误: {str(e)}")

    @filter.command("memo_associate", aliases=["记忆关联", "关联记忆"])
    async def memo_associate_command(self, event: AstrMessageEvent, memory_id_1: str, memory_id_2: str):
        """关联记忆"""
        try:
            if not self._initialized:
                yield event.plain_result("❌ 记忆系统未初始化")
                return
    
            if self.memory_manager.add_manual_association(memory_id_1, memory_id_2):
                yield event.plain_result("✅ 记忆关联已建立！")
            else:
                yield event.plain_result("❌ 关联记忆失败，请检查记忆ID")
                
        except Exception as e:
            astrbot_logger.error(f"Error associating memories: {e}")
            yield event.plain_result("❌ 关联记忆时发生错误")
    
    @filter.command("memo_organize", aliases=["记忆梳理", "梳理记忆"])
    async def memo_organize_command(self, event: AstrMessageEvent, tasks: str = "all", model_id: str = None):
        """使用AI模型梳理记忆"""
        try:
            if not self._initialized:
                yield event.plain_result("❌ 记忆系统未初始化")
                return
            
            if not self.organization_enabled:
                yield event.plain_result("❌ 记忆梳理功能未启用，请在配置中启用")
                return
    
            # 解析任务列表
            task_list = []
            if tasks == "all":
                task_list = ["categorize", "summarize", "find_duplicates", "suggest_associations", "suggest_importance", "sentiment_analysis"]
            else:
                task_list = [task.strip() for task in tasks.split(",")]
            
            # 获取可用模型
            available_models = self.memory_manager.get_available_models()
            if not available_models:
                yield event.plain_result("❌ 没有可用的AI模型，请先配置LLM提供商")
                return
            
            # 显示模型选择
            model_info = ""
            if model_id and model_id in available_models:
                model_info = f"使用模型: {available_models[model_id]['name']}"
            else:
                default_provider = self.context.get_using_provider()
                if default_provider:
                    model_info = f"使用默认模型: {getattr(default_provider, 'name', 'Unknown')}"
                else:
                    model_info = "使用系统默认模型"
            
            yield event.plain_result(f"🔧 开始使用AI梳理记忆...\n{model_info}\n任务: {', '.join(task_list)}")
            
            # 执行梳理
            organization_results = await self.memory_manager.organize_with_model(model_id, task_list)
            
            if "error" in organization_results:
                yield event.plain_result(f"❌ 梳理失败: {organization_results['error']}")
                return
            
            # 显示梳理结果
            response = "🎯 AI梳理结果：\n\n"
            
            if "summary" in organization_results:
                response += f"📝 记忆库总结：\n{organization_results['summary']}\n\n"
            
            if "categorization" in organization_results:
                cat_count = len(organization_results['categorization'])
                response += f"🏷️ 分类建议: {cat_count} 条\n"
            
            if "duplicates" in organization_results:
                dup_count = len(organization_results['duplicates'])
                response += f"🔄 重复检测: {dup_count} 对\n"
            
            if "associations" in organization_results:
                assoc_count = len(organization_results['associations'])
                response += f"🔗 关联建议: {assoc_count} 对\n"
            
            if "importance_suggestions" in organization_results:
                imp_count = len(organization_results['importance_suggestions'])
                response += f"⭐ 重要性调整: {imp_count} 条\n"

            if "sentiment_analysis" in organization_results:
                sent_count = len(organization_results['sentiment_analysis'])
                response += f"😊 情感分析: {sent_count} 条\n"
            
            response += "\n💡 使用 /memo_apply_org 应用这些建议"
            
            # 保存梳理结果供后续应用
            self.last_organization_results = organization_results
            
            yield event.plain_result(response)
                
        except Exception as e:
            astrbot_logger.error(f"Error organizing memories: {e}")
            yield event.plain_result("❌ 记忆梳理时发生错误")
    
    @filter.command("memo_apply_org", aliases=["应用梳理", "应用建议"])
    async def memo_apply_org_command(self, event: AstrMessageEvent):
        """应用梳理结果"""
        try:
            if not self._initialized:
                yield event.plain_result("❌ 记忆系统未初始化")
                return
            
            if not hasattr(self, 'last_organization_results') or not self.last_organization_results:
                yield event.plain_result("❌ 没有可应用的梳理结果，请先使用 /memo_organize")
                return
    
            yield event.plain_result("🔄 正在应用AI梳理建议...")
            
            applied_changes = self.memory_manager.apply_organization_results(self.last_organization_results)
            
            response = "✅ 已应用AI梳理建议：\n\n"
            if applied_changes["categorization"] > 0:
                response += f"• 更新分类: {applied_changes['categorization']} 条\n"
            if applied_changes["importance_updates"] > 0:
                response += f"• 调整重要性: {applied_changes['importance_updates']} 条\n"
            if applied_changes["associations_created"] > 0:
                response += f"• 新建关联: {applied_changes['associations_created']} 对\n"
            
            if not any(applied_changes.values()):
                response = "ℹ️ 没有需要应用的更改"
            
            # 清理结果
            del self.last_organization_results
            
            yield event.plain_result(response)
                    
        except Exception as e:
            astrbot_logger.error(f"Error applying organization: {e}")
            yield event.plain_result("❌ 应用梳理结果时发生错误")
    
    @filter.command("memo_models", aliases=["可用模型", "模型列表"])
    async def memo_models_command(self, event: AstrMessageEvent):
        """显示可用模型"""
        try:
            if not self._initialized:
                yield event.plain_result("❌ 记忆系统未初始化")
                return
    
            available_models = self.memory_manager.get_available_models()
            
            if not available_models:
                yield event.plain_result("❌ 没有可用的AI模型，请先配置LLM提供商")
                return
            
            response = "🤖 可用AI模型：\n\n"
            
            for model_id, model_info in available_models.items():
                response += f"• {model_id}: {model_info['name']}\n"
            
            response += "\n💡 使用 /memo_organize model_id=模型ID 指定使用的模型"
            
            yield event.plain_result(response)
                
        except Exception as e:
            astrbot_logger.error(f"Error listing models: {e}")
            yield event.plain_result("❌ 获取模型列表时发生错误")

    @filter.command("memo_model_info", aliases=["模型信息", "记忆模型"])
    async def memo_model_info_command(self, event: AstrMessageEvent):
        """显示模型信息"""
        try:
            if not self._initialized:
                yield event.plain_result("❌ 记忆系统未初始化")
                return
    
            model_info = self.memory_manager.get_model_info()
            
            if "error" in model_info:
                yield event.plain_result(f"❌ {model_info['error']}")
                return
            
            response = "🤖 记忆AI模型信息：\n\n"
            
            # 基本配置
            response += f"📋 使用框架模型: {'✅' if model_info['use_framework_models'] else '❌'}\n"
            response += f"🔄 并发请求: {model_info['concurrent_requests']}\n"
            response += f"💾 模型缓存: {model_info['model_cache_size']} 个\n\n"
            
            # 配置的模型
            response += "🎯 配置的模型：\n"
            for model_type, model_id in model_info['configured_models'].items():
                status = "✅" if model_id else "❌"
                response += f"  • {model_type}: {status} {model_id or '未配置'}\n"
            
            response += "\n🔧 激活的模型：\n"
            for task, model_name in model_info['active_models'].items():
                response += f"  • {task}: {model_name}\n"
            
            response += f"\n📊 可用模型总数: {len(model_info['available_models'])}"
            
            yield event.plain_result(response)
                
        except Exception as e:
            astrbot_logger.error(f"Error getting model info: {e}")
            yield event.plain_result("❌ 获取模型信息时发生错误")

    @filter.command("memo_ai_extract", aliases=["AI提取", "智能提取"])
    async def memo_ai_extract_command(self, event: AstrMessageEvent, content: str):
        """使用AI智能提取记忆"""
        try:
            if not self._initialized:
                yield event.plain_result("❌ 记忆系统未初始化")
                return
    
            if not self.use_framework_models:
                yield event.plain_result("❌ AI模型功能未启用，请在配置中启用")
                return
    
            yield event.plain_result("🤖 AI正在分析并提取记忆...")
            
            memory_ids = await self.memory_manager.ai_auto_extract(content, self.conversation_history)
            
            if memory_ids:
                response = f"✅ AI智能提取完成！\n\n新增 {len(memory_ids)} 条记忆：\n"
                for i, memory_id in enumerate(memory_ids, 1):
                    if memory_id in self.memory_manager.memories:
                        memory = self.memory_manager.memories[memory_id]
                        response += f"{i}. {memory['content']}\n"
                yield event.plain_result(response)
            else:
                yield event.plain_result("❌ AI未提取到重要信息，或提取失败")
                
        except Exception as e:
            astrbot_logger.error(f"AI extraction command failed: {e}")
            yield event.plain_result("❌ AI提取记忆时发生错误")
    
    @filter.command("memo_export", aliases=["记忆导出", "导出记忆"])
    async def memo_export_command(self, event: AstrMessageEvent, format: str = "json"):
        """导出记忆"""
        try:
            if not self._initialized:
                yield event.plain_result("❌ 记忆系统未初始化")
                return
    
            filepath = self.memory_manager.export_data(format)
            
            if filepath:
                yield event.plain_result(f"✅ 记忆已导出到：{filepath}")
            else:
                yield event.plain_result("❌ 导出记忆失败")
                
        except Exception as e:
            astrbot_logger.error(f"Error exporting memories: {e}")
            yield event.plain_result("❌ 导出记忆时发生错误")
    
    @filter.command("memo_import", aliases=["记忆导入", "导入记忆"])
    async def memo_import_command(self, event: AstrMessageEvent, filepath: str, format: str = "json"):
        """导入记忆"""
        try:
            if not self._initialized:
                yield event.plain_result("❌ 记忆系统未初始化")
                return
    
            count = self.memory_manager.import_data(filepath, format)
                
            if count > 0:
                yield event.plain_result(f"✅ 成功导入 {count} 条记忆！")
            else:
                yield event.plain_result("❌ 导入记忆失败或没有新记忆可导入")
                
        except Exception as e:
            astrbot_logger.error(f"Error importing memories: {e}")
            yield event.plain_result("❌ 导入记忆时发生错误")
    
    @filter.command("memo_stats", aliases=["记忆统计", "记忆状态"])
    async def memo_stats_command(self, event: AstrMessageEvent):
        """记忆统计"""
        try:
            if not self._initialized:
                yield event.plain_result("❌ 记忆系统未初始化")
                return
    
            stats = self.memory_manager.get_stats()
            
            response = "📊 记忆系统统计信息：\n\n"
            response += f"• 总记忆数量: {stats['total_memories']} 条\n"
            response += f"• 总关联数量: {stats['total_associations']} 个\n"
            response += f"• 存储路径: {stats['storage_path']}\n"
            response += f"• 平均重要性: {stats['average_importance']:.2f}\n"
            
            if stats.get('type_counts'):
                response += "\n📁 记忆类型分布：\n"
                for mem_type, count in stats['type_counts'].items():
                    response += f"  • {mem_type}: {count} 条\n"
            
            if stats.get('component_status'):
                response += "\n⚙️ 组件状态：\n"
                comp_status = stats['component_status']
                response += f"  • 语义搜索: {'✅' if comp_status.get('semantic_search') else '❌'}\n"
                response += f"  • 自动提取: {'✅' if comp_status.get('auto_extraction') else '❌'}\n"
                response += f"  • 关联管理: {'✅' if comp_status.get('association_management') else '❌'}\n"
                response += f"  • 数据导入导出: {'✅' if comp_status.get('data_import_export') else '❌'}\n"
                response += f"  • AI集成: {'✅' if comp_status.get('ai_integration') else '❌'}\n"
                response += f"  • AI梳理: {'✅' if comp_status.get('ai_organization') else '❌'}\n"
                
            yield event.plain_result(response)
            
        except Exception as e:
            astrbot_logger.error(f"Error getting stats: {e}")
            yield event.plain_result("❌ 获取统计信息时发生错误")
    
    @filter.command("memo_deps", aliases=["记忆依赖", "依赖检查"])
    async def memo_deps_command(self, event: AstrMessageEvent):
        """依赖检查"""
        deps_info = "🔧 依赖检查结果：\n\n"
        
        dependencies = {
            'faiss': '向量搜索',
            'sentence_transformers': '语义嵌入', 
            'jieba': '中文分词'
        }
        
        for dep, desc in dependencies.items():
            try:
                __import__(dep)
                status = "✅ 可用"
            except ImportError:
                status = "❌ 不可用"
            deps_info += f"• {dep} ({desc}): {status}\n"
        
        deps_info += "\n💡 安装命令: pip install faiss-cpu sentence-transformers jieba"
        deps_info += "\n\n🎯 当前功能: 自动提取 ✅ | 记忆关联 ✅ | 数据导入导出 ✅ | AI集成 ✅ | AI梳理 ✅"
        
        yield event.plain_result(deps_info)
    
    @filter.command("memo_help", aliases=["记忆帮助"])
    async def memo_help_command(self, event: AstrMessageEvent):
        """帮助命令 - 更新版"""
        help_text = """
🤖 增强记忆插件 v1.0.0 - AI智能梳理版

📝 记忆管理：
/memo_add [内容] - 添加记忆
/memo_delete [记忆ID] - 删除记忆  
/memo_search [关键词] [数量] - 搜索记忆

🔗 记忆关联：
/memo_associate [记忆ID1] [记忆ID2] - 手动关联记忆

🤖 AI智能功能：
/memo_ai_extract [内容] - 使用AI智能提取记忆
/memo_organize [任务] [模型ID] - 使用AI梳理记忆
/memo_apply_org - 应用梳理建议
/memo_models - 查看可用模型
/memo_model_info - 查看模型信息

📊 数据管理：
/memo_export [格式] - 导出记忆 (json/csv)
/memo_import [文件路径] [格式] - 导入记忆

📈 系统信息：
/memo_stats - 查看统计信息
/memo_deps - 检查依赖状态

❓ 显示帮助：
/memo_help - 显示此帮助信息

🎯 AI梳理任务：
• categorize - 重新分类记忆
• summarize - 总结记忆库  
• find_duplicates - 检测重复记忆
• suggest_associations - 建议关联
• suggest_importance - 调整重要性
• sentiment_analysis - 情感分析

💡 示例：
/memo_organize all
/memo_organize categorize,suggest_associations
/memo_organize all model_id=your_model_id
/memo_apply_org
/memo_ai_extract 今天学到了很多关于机器学习的新知识
"""
        yield event.plain_result(help_text)
    
    async def terminate(self):
        """插件停止时的清理工作"""
        astrbot_logger.info("Enhanced Memory Plugin v1.0.0 is shutting down...")
        try:
            if self._initialized and hasattr(self.memory_manager, 'save_memories'):
                self.memory_manager.save_memories()
                astrbot_logger.info("Memories saved successfully")
        except Exception as e:
            astrbot_logger.error(f"Error saving memories during shutdown: {e}")