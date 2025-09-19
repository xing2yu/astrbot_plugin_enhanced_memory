import os
from typing import List, Dict, Any
import logging

# 使用根记录器而不是特定名称的记录器
logger = logging.getLogger()

class MemoryClassifier:
    def __init__(self, model_path: str, categories: List[str]):
        self.model_path = model_path
        self.categories = categories
        self.tokenizer = None
        self.model = None
        
        self._ensure_storage_path()
        
        # 检查是否安装了 torch 和 transformers
        self.has_torch = self._check_torch_available()
        
        if self.has_torch:
            self.load_model()
        else:
            logger.warning("torch 或 transformers 未安装，将使用简化版分类器")
    
    def _check_torch_available(self):
        """检查 torch 和 transformers 是否可用"""
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            return True
        except ImportError:
            return False
    
    def _ensure_storage_path(self):
        """确保存储路径存在"""
        os.makedirs(self.model_path, exist_ok=True)
    
    def load_model(self):
        """加载分类模型"""
        if not self.has_torch:
            return
            
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            
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
        if not self.has_torch:
            return False
            
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
        if not self.has_torch:
            # 使用简化版分类逻辑
            return self._simple_classify(text)
            
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
    
    def _simple_classify(self, text: str) -> Dict[str, float]:
        """简化版分类逻辑"""
        # 基于简单规则进行分类
        result = {category: 0.0 for category in self.categories}
        
        # 默认类别
        result["其他"] = 0.5
        
        # 简单关键词匹配
        if any(word in text for word in ["是", "有", "在", "属于"]):
            result["事实"] = 0.1
            result["其他"] = 0.3
        
        if any(word in text for word in ["认为", "觉得", "想", "应该"]):
            result["观点"] = 0.5
            result["其他"] = 0.3
        
        if any(word in text for word in ["喜欢", "讨厌", "爱", "恨"]):
            result["用户偏好"] = 0.2
            result["其他"] = 0.3
        
        if any(word in text for word in ["昨天", "今天", "明天", "小时", "分钟"]):
            result["事件"] = 0.3
            result["其他"] = 0.3
        
        return result
    
    def train(self, training_data: List[Dict[str, Any]]):
        """训练分类模型"""
        if not self.has_torch:
            logger.warning("无法训练模型，torch 或 transformers 未安装")
            return
            
        # 实现模型训练逻辑
        # 需要标注好的训练数据: [{"text": "记忆内容", "label": "类别"}, ...]
        pass