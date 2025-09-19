import re
import jieba
import jieba.analyse
from typing import List, Dict, Any
import logging

logger = logging.getLogger("astrbot.plugin.enhanced_memory")

class MemoryExtractor:
    def __init__(self, min_importance: float = 0.3, extract_keywords: bool = True, max_keywords: int = 5):
        self.min_importance = min_importance
        self.extract_keywords = extract_keywords
        self.max_keywords = max_keywords
        
        # 初始化jieba
        jieba.initialize()
    
    def extract_from_text(self, text: str, conversation_context: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """从文本中提取潜在记忆"""
        memories = []
        
        # 简单规则：提取包含重要信息的句子
        sentences = self._split_into_sentences(text)
        
        for sentence in sentences:
            importance = self._calculate_importance(sentence, conversation_context)
            
            if importance >= self.min_importance:
                memory = {
                    "content": sentence,
                    "importance": importance,
                    "type": self._determine_memory_type(sentence),
                    "keywords": self._extract_keywords(sentence) if self.extract_keywords else []
                }
                
                memories.append(memory)
        
        return memories
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """将文本分割成句子"""
        # 简单的中文分句规则
        sentences = re.split(r'[。！？!?;；]', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _calculate_importance(self, sentence: str, conversation_context: List[Dict[str, Any]] = None) -> float:
        """计算句子重要性"""
        # 基于规则的重要性评估
        importance = 0.1  # 基础重要性
        
        # 包含人称代词（可能关于用户）
        if any(pronoun in sentence for pronoun in ["我", "你", "他", "她", "我们", "你们", "他们"]):
            importance += 0.2
        
        # 包含情感词
        emotion_words = ["喜欢", "讨厌", "爱", "恨", "开心", "难过", "生气", "害怕"]
        if any(word in sentence for word in emotion_words):
            importance += 0.3
        
        # 包含重要动词
        important_verbs = ["记得", "知道", "认为", "觉得", "想要", "需要", "希望"]
        if any(verb in sentence for verb in important_verbs):
            importance += 0.2
        
        # 包含数字（可能是重要信息）
        if re.search(r'\d+', sentence):
            importance += 0.1
        
        # 基于上下文的重要性调整
        if conversation_context:
            # 检查是否在回应重要问题
            last_user_message = None
            for msg in reversed(conversation_context):
                if msg.get("role") == "user":
                    last_user_message = msg.get("content", "")
                    break
            
            if last_user_message and any(q in last_user_message for q in ["吗?", "吗？", "什么", "为什么", "怎么"]):
                importance += 0.2
        
        return min(importance, 1.0)  # 确保不超过1.0
    
    def _determine_memory_type(self, sentence: str) -> str:
        """确定记忆类型"""
        # 简单基于关键词的类型判断
        if any(word in sentence for word in ["是", "有", "在", "属于"]):
            return "事实"
        elif any(word in sentence for word in ["认为", "觉得", "想", "应该"]):
            return "观点"
        elif any(word in sentence for word in ["喜欢", "讨厌", "爱", "恨"]):
            return "用户偏好"
        elif any(word in sentence for word in ["昨天", "今天", "明天", "小时", "分钟"]):
            return "事件"
        else:
            return "其他"
    
    def _extract_keywords(self, sentence: str) -> List[str]:
        """提取关键词"""
        try:
            keywords = jieba.analyse.extract_tags(
                sentence, 
                topK=self.max_keywords, 
                withWeight=False
            )
            return keywords
        except Exception as e:
            logger.error(f"提取关键词失败: {e}")
            return []