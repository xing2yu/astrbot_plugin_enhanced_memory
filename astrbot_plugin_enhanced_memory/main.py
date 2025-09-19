import os
from typing import Dict, Any, List

from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger

from .memory_manager import EnhancedMemoryManager

@register(
    "EnhancedMemory",
    "你的名字",
    "增强版本地记忆插件，支持向量搜索、分类、关联和自动提取",
    "1.0.0",
    "https://github.com/your-repo/astrbot_plugin_enhanced_memory",
)
class EnhancedMemoryPlugin(Star):
    def __init__(self, context: Context, config: Dict[str, Any]):
        super().__init__(context)
        self.config = config.get("enhanced_memory", {})
        
        # 获取数据目录
        data_dir = StarTools.get_data_dir()
        storage_path = self.config.get("storage_path", "data/plugin_data/enhanced_memory")
        
        # 如果是相对路径，转换为绝对路径
        if not os.path.isabs(storage_path):
            storage_path = os.path.join(data_dir, storage_path)
        
        # 初始化记忆管理器
        self.memory_manager = EnhancedMemoryManager({
            **self.config,
            "storage_path": storage_path
        })
        
        logger.info("EnhancedMemory插件初始化完成")
    
    # 使用更简单的事件处理方式
    async def on_message(self, event: AstrMessageEvent):
        """处理所有消息，自动提取记忆"""
        if not self.config.get("auto_extraction", {}).get("enabled", True):
            return
        
        try:
            # 获取对话上下文（最近几条消息）
            conversation_context = await self.context.conversation_manager.get_recent_messages(
                event.unified_msg_origin, 
                limit=5
            )
            
            # 提取并添加记忆
            memory_ids = self.memory_manager.extract_and_add_memories(
                event.plain_text, 
                conversation_context
            )
            
            if memory_ids:
                logger.info(f"从消息中自动提取了 {len(memory_ids)} 条记忆")
        
        except Exception as e:
            logger.error(f"自动提取记忆失败: {e}")
    
    @filter.command_group("memory")
    def memory_group(self):
        """记忆管理命令组 /memory"""
        pass
    
    @memory_group.command("add")
    async def add_memory(self, event: AstrMessageEvent, content: str, importance: float = 0.5):
        """添加新记忆 /memory add <内容> [重要性]"""
        memory_id = self.memory_manager.add_memory(content, importance)
        yield event.plain_result(f"✅ 已添加记忆 (ID: {memory_id})")
    
    @memory_group.command("search")
    async def search_memories(self, event: AstrMessageEvent, query: str, limit: int = 5):
        """搜索记忆 /memory search <查询词> [数量]"""
        memories = self.memory_manager.search_memories(query, limit)
        if memories:
            response = "找到的相关记忆:\n\n"
            for i, memory in enumerate(memories, 1):
                response += f"{i}. {memory['content']}\n"
                response += f"   类型: {memory.get('type', '未知')}\n"
                response += f"   重要性: {memory.get('importance', 0):.2f}\n\n"
            yield event.plain_result(response)
        else:
            yield event.plain_result("❌ 未找到相关记忆")
    
    @memory_group.command("associate")
    async def associate_memories(self, event: AstrMessageEvent, memory_id_1: str, memory_id_2: str, relation_type: str):
        """关联记忆 /memory associate <ID1> <ID2> <关系类型>"""
        if self.memory_manager.add_association(memory_id_1, memory_id_2, relation_type):
            yield event.plain_result("✅ 已关联记忆")
        else:
            yield event.plain_result("❌ 关联记忆失败")
    
    @memory_group.command("export")
    async def export_memories(self, event: AstrMessageEvent, format: str = "json"):
        """导出记忆 /memory export [格式:json/csv]"""
        file_path = os.path.join(self.memory_manager.storage_path, f"memories_export.{format}")
        if self.memory_manager.export_memories(file_path, format):
            yield event.plain_result(f"✅ 记忆已导出到 {file_path}")
        else:
            yield event.plain_result("❌ 导出记忆失败")
    
    @memory_group.command("import")
    async def import_memories(self, event: AstrMessageEvent, format: str = "json"):
        """导入记忆 /memory import [格式:json/csv]"""
        file_path = os.path.join(self.memory_manager.storage_path, f"memories_export.{format}")
        if self.memory_manager.import_memories(file_path, format):
            yield event.plain_result(f"✅ 已从 {file_path} 导入记忆")
        else:
            yield event.plain_result("❌ 导入记忆失败")
    
    @memory_group.command("stats")
    async def memory_stats(self, event: AstrMessageEvent):
        """查看记忆统计 /memory stats"""
        stats = self.memory_manager.get_stats()
        
        response = "📊 记忆统计:\n"
        response += f"总记忆数: {stats['total_memories']}\n"
        response += f"平均重要性: {stats['average_importance']:.2f}\n\n"
        
        response += "按类型统计:\n"
        for mem_type, count in stats['type_counts'].items():
            response += f"  {mem_type}: {count}\n"
        
        response += f"\n图统计:\n"
        response += f"  节点: {stats['graph_stats']['nodes']}\n"
        response += f"  边: {stats['graph_stats']['edges']}\n"
        response += f"  聚类: {stats['graph_stats']['clusters']}\n"
        
        yield event.plain_result(response)
    
    # API方法，供其他插件调用
    def add_memory_api(self, content: str, importance: float = 0.5, memory_type: str = None) -> str:
        """API: 添加新记忆"""
        return self.memory_manager.add_memory(content, importance, memory_type)
    
    def search_memories_api(self, query: str, limit: int = 5, memory_type: str = None) -> List[Dict[str, Any]]:
        """API: 搜索记忆"""
        return self.memory_manager.search_memories(query, limit, memory_type=memory_type)
    
    def get_associated_memories_api(self, memory_id: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """API: 获取关联记忆"""
        return self.memory_manager.get_associated_memories(memory_id, max_results)
    
    async def terminate(self):
        """插件停止时的清理逻辑"""
        logger.info("EnhancedMemory插件正在停止...")
        self.memory_manager.save_memories()
        logger.info("EnhancedMemory插件已成功停止。")