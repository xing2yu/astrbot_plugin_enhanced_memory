import os
import threading
import logging
from typing import Dict, Any, List, Optional

from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api.event import AstrMessageEvent, filter

# 首先定义命令组
@filter.command_group("memory", aliases=["记忆", "内存"])
def memory_group():
    """记忆管理命令组 /memory 或 /记忆 或 /内存"""
    pass

# 导入内存管理器
try:
    from .memory_manager import EnhancedMemoryManager
except ImportError:
    # 如果导入失败，创建一个简单的占位类
    class EnhancedMemoryManager:
        def __init__(self, config):
            pass
        
        def add_memory(self, content, importance=0.5):
            return "mock_memory_id"
        
        def search_memories(self, query, limit=5):
            return []
        
        def add_association(self, memory_id_1, memory_id_2, relation_type):
            return True
        
        def export_memories(self, file_path, format):
            return True
        
        def import_memories(self, file_path, format):
            return True
        
        def get_stats(self):
            return {
                "total_memories": 0,
                "type_counts": {},
                "average_importance": 0,
                "graph_stats": {"nodes": 0, "edges": 0, "clusters": 0}
            }
        
        def save_memories(self):
            pass

@register(
    "EnhancedMemory",
    "星辰向鱼",
    "星鱼自制的记忆插件",
    "0.0.0",
    "https://github.com/xing2yu/astrbot_plugin_enhanced_memory",
)
class EnhancedMemoryPlugin(Star):
    def __init__(self, context: Context, config: Optional[Dict[str, Any]] = None):
        # 确保正确调用父类构造函数
        super().__init__(context)
        
        # 处理配置参数
        self.config = config or {}
        
        # 设置日志格式，避免 plugin_tag 错误
        # 获取插件特定的日志记录器
        self.logger = logging.getLogger("astrbot.plugin.enhanced_memory")
        # 移除所有现有的处理器
        self.logger.handlers = []
        # 设置不传播到父记录器
        self.logger.propagate = False
        
        # 添加一个简单的控制台处理器
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        self.logger.setLevel(logging.INFO)
        
        # 推迟初始化到实际需要时
        self.memory_manager = None
        self._storage_path = None
        self._initialized = False
        self._init_lock = threading.Lock()
        
        self.logger.info("EnhancedMemory插件初始化完成")
    
    def _initialize(self):
        """同步初始化方法"""
        with self._init_lock:
            if self._initialized:
                return
                
            # 获取数据目录
            data_dir = StarTools.get_data_dir()
            storage_path = self.config.get("storage_path", "data/plugin_data/enhanced_memory")
            
            # 如果是相对路径，转换为绝对路径
            if not os.path.isabs(storage_path):
                storage_path = os.path.join(data_dir, storage_path)
            
            # 确保存储路径存在
            os.makedirs(storage_path, exist_ok=True)
            
            # 初始化记忆管理器
            try:
                self.memory_manager = EnhancedMemoryManager({
                    **self.config,
                    "storage_path": storage_path
                })
                self._storage_path = storage_path
                self._initialized = True
                self.logger.info("EnhancedMemory插件记忆管理器初始化完成")
            except Exception as e:
                self.logger.error(f"初始化记忆管理器失败: {e}")
                # 使用简化版内存管理器作为后备
                self.memory_manager = EnhancedMemoryManager({})
                self._initialized = True
    
    async def ensure_initialized(self):
        """确保插件已初始化"""
        if not self._initialized:
            self._initialize()
    
    # 定义记忆命令
    @memory_group.command("add", aliases=["添加"])
    async def memory_add(self, event: AstrMessageEvent, content: str, importance: float = 0.5):
        """添加新记忆 /memory add <内容> [重要性] 或 /记忆添加 <内容> [重要性]"""
        try:
            await self.ensure_initialized()
            memory_id = self.memory_manager.add_memory(content, importance)
            yield event.plain_result(f"✅ 已添加记忆 (ID: {memory_id})")
        except Exception as e:
            self.logger.error(f"添加记忆失败: {e}")
            yield event.plain_result("❌ 添加记忆失败")
    
    @memory_group.command("search", aliases=["搜索"])
    async def memory_search(self, event: AstrMessageEvent, query: str, limit: int = 5):
        """搜索记忆 /memory search <查询词> [数量] 或 /记忆搜索 <查询词> [数量]"""
        try:
            await self.ensure_initialized()
            
            # 添加调试信息
            self.logger.info(f"开始搜索: {query}, 限制: {limit}")
            self.logger.info(f"记忆管理器类型: {type(self.memory_manager)}")
            
            memories = self.memory_manager.search_memories(query, limit)
            
            # 添加更多调试信息
            self.logger.info(f"找到的记忆数量: {len(memories)}")
            
            if memories:
                response = "找到的相关记忆:\n\n"
                for i, memory in enumerate(memories, 1):
                    response += f"{i}. {memory['content']}\n"
                    response += f"   类型: {memory.get('type', '未知')}\n"
                    response += f"   重要性: {memory.get('importance', 0):.2f}\n\n"
                yield event.plain_result(response)
            else:
                yield event.plain_result("❌ 未找到相关记忆")
        except Exception as e:
            self.logger.error(f"搜索记忆失败: {e}")
            yield event.plain_result("❌ 搜索记忆失败")
    
    @memory_group.command("associate", aliases=["关联"])
    async def memory_associate(self, event: AstrMessageEvent, memory_id_1: str, memory_id_2: str, relation_type: str):
        """关联记忆 /memory associate <ID1> <ID2> <关系类型> 或 /记忆关联 <ID1> <ID2> <关系类型>"""
        try:
            await self.ensure_initialized()
            if self.memory_manager.add_association(memory_id_1, memory_id_2, relation_type):
                yield event.plain_result("✅ 已关联记忆")
            else:
                yield event.plain_result("❌ 关联记忆失败")
        except Exception as e:
            self.logger.error(f"关联记忆失败: {e}")
            yield event.plain_result("❌ 关联记忆失败")
    
    @memory_group.command("export", aliases=["导出"])
    async def memory_export(self, event: AstrMessageEvent, format: str = "json"):
        """导出记忆 /memory export [格式:json/csv] 或 /记忆导出 [格式:json/csv]"""
        try:
            await self.ensure_initialized()
            file_path = os.path.join(self._storage_path, f"memories_export.{format}")
            if self.memory_manager.export_memories(file_path, format):
                yield event.plain_result(f"✅ 记忆已导出到 {file_path}")
            else:
                yield event.plain_result("❌ 导出记忆失败")
        except Exception as e:
            self.logger.error(f"导出记忆失败: {e}")
            yield event.plain_result("❌ 导出记忆失败")
    
    @memory_group.command("import", aliases=["导入"])
    async def memory_import(self, event: AstrMessageEvent, format: str = "json"):
        """导入记忆 /memory import [格式:json/csv] 或 /记忆导入 [格式:json/csv]"""
        try:
            await self.ensure_initialized()
            file_path = os.path.join(self._storage_path, f"memories_export.{format}")
            if self.memory_manager.import_memories(file_path, format):
                yield event.plain_result(f"✅ 已从 {file_path} 导入记忆")
            else:
                yield event.plain_result("❌ 导入记忆失败")
        except Exception as e:
            self.logger.error(f"导入记忆失败: {e}")
            yield event.plain_result("❌ 导入记忆失败")
    
    @memory_group.command("stats", aliases=["统计"])
    async def memory_stats(self, event: AstrMessageEvent):
        """查看记忆统计 /memory stats 或 /记忆统计"""
        try:
            await self.ensure_initialized()
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
        except Exception as e:
            self.logger.error(f"获取统计信息失败: {e}")
            yield event.plain_result("❌ 获取统计信息失败")
    
    # API方法，供其他插件调用
    def add_memory_api(self, content: str, importance: float = 0.5, memory_type: str = None) -> str:
        """API: 添加新记忆"""
        try:
            if not self._initialized:
                self._initialize()
            return self.memory_manager.add_memory(content, importance, memory_type)
        except Exception as e:
            self.logger.error(f"API添加记忆失败: {e}")
            return "error"
    
    def search_memories_api(self, query: str, limit: int = 5, memory_type: str = None) -> List[Dict[str, Any]]:
        """API: 搜索记忆"""
        try:
            if not self._initialized:
                self._initialize()
            return self.memory_manager.search_memories(query, limit, memory_type=memory_type)
        except Exception as e:
            self.logger.error(f"API搜索记忆失败: {e}")
            return []
    
    def get_associated_memories_api(self, memory_id: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """API: 获取关联记忆"""
        try:
            if not self._initialized:
                self._initialize()
            return self.memory_manager.get_associated_memories(memory_id, max_results)
        except Exception as e:
            self.logger.error(f"API获取关联记忆失败: {e}")
            return []
    
    async def terminate(self):
        """插件停止时的清理逻辑"""
        self.logger.info("EnhancedMemory插件正在停止...")
        try:
            if self._initialized and hasattr(self.memory_manager, 'save_memories'):
                self.memory_manager.save_memories()
            self.logger.info("EnhancedMemory插件已成功停止。")
        except Exception as e:
            self.logger.error(f"插件停止时保存记忆失败: {e}")