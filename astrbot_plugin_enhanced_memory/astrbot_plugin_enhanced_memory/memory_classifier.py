import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np
import os
from typing import List, Dict, Any
import logging

logger = logging.getLogger("astrbot.plugin.enhanced_memory")

class MemoryClassifier:
    def __init__(self, model_path: str, categories: List[str]):
        self.model_path = model_path
        self.categories = categories
        self.tokenizer = None
        self.model = None
        
        self._ensure_storage_path()
        self.load_model()
    
    def _ensure_storage_path(self):
        """确保存储路径存在"""
        os.makedirs(self.model_path, exist_ok=True)
    
    def load_model(self):
        """加载分类模型"""
        try:
            if os.path.exists(os.path.join(self.model_path, "config.json")):
                # 加载已训练的模型
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
                self.model = AutoModelForSequenceClassification.from_pretrained(self.model_path)
                logger.info("已加载记忆分类模型")
            else:
                # 初始化新模型
                from transformers import BertConfig, BertForSequenceClassification
                
                config = BertConfig.from_pretrained(
                    "bert-base-uncased", 
                    num_labels=len(self.categories)
                )
                self.model = BertForSequenceClassification.from_pretrained(
                    "bert-base-uncased", 
                    config=config
                )
                self.tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
                
                logger.info("初始化了新的记忆分类模型")
        except Exception as e:
            logger.error(f"加载记忆分类模型失败: {e}")
    
    def save_model(self):
        """保存分类模型"""
        try:
            if self.model and self.tokenizer:
                self.model.save_pretrained(self.model_path)
                self.tokenizer.save_pretrained(self.model_path)
                logger.info("已保存记忆分类模型")
                return True
        except Exception as e:
            logger.error(f"保存记忆分类模型失败: {e}")
        return False
    
    def classify(self, text: str) -> Dict[str, float]:
        """对记忆文本进行分类"""
        try:
            if not self.model or not self.tokenizer:
                return {category: 0.0 for category in self.categories}
            
            # 编码文本
            inputs = self.tokenizer(
                text, 
                return_tensors="pt", 
                truncation=True, 
                padding=True, 
                max_length=128
            )
            
            # 获取预测
            with torch.no_grad():
                outputs = self.model(**inputs)
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
            
            # 转换为类别概率
            probabilities = predictions[0].numpy()
            result = {self.categories[i]: float(probabilities[i]) for i in range(len(self.categories))}
            
            return result
        except Exception as e:
            logger.error(f"记忆分类失败: {e}")
            return {category: 0.0 for category in self.categories}
    
    def train(self, training_data: List[Dict[str, Any]]):
        """训练分类模型"""
        # 实现模型训练逻辑
        # 需要标注好的训练数据: [{"text": "记忆内容", "label": "类别"}, ...]
        pass