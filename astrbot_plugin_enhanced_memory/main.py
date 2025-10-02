import os
import threading
import logging
import tempfile
import json
from typing import Dict, Any, List, Optional

from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api.event import AstrMessageEvent, filter

# 导入完整功能的内存管理器
try:
    from .memory_manager import EnhancedMemoryManager
    HAS_FULL_FUNCTIONALITY = True
except ImportError as e:
    logging.error(f"导入完整内存管理器失败: {e}")
    HAS_FULL_FUNCTIONALITY = False

# 创建功能完整的后备管理器
class FallbackMemoryManager:
    def __init__(self, config):
        self.config = config
        self.storage_path = config.get("storage_path", "data/plugin_data/enhanced_memory")
        self.memories = {}
        self.logger = logging.getLogger("astrbot.plugin.enhanced_memory.fallback")
        self._ensure_storage_path()
        self.load_memories()
    
    def _ensure_storage_path(self):
        """确保存储路径存在"""
        try:
            os.makedirs(self.storage_path, exist_ok=True)
            self.logger.info(f"确保存储路径存在: {self.storage_path}")
        except Exception as e:
            self.logger.error(f"创建存储路径失败: {e}")
            raise
    
    def load_memories(self):
        """从文件加载记忆"""
        try:
            memories_path = os.path.join(self.storage_path, "memories.json")
            if os.path.exists(memories_path):
                with open(memories_path, 'r', encoding='utf-8') as f:
                    self.memories = json.load(f)
                self.logger.info(f"已加载 {len(self.memories)} 条记忆")
            else:
                self.memories = {}
                self.logger.info("未找到记忆文件，将创建新文件")
        except Exception as e:
            self.logger.error(f"加载记忆失败: {e}")
            self.memories = {}
    
    def save_memories(self):
        """保存记忆到文件"""
        try:
            memories_path = os.path.join(self.storage_path, "memories.json")
            with open(memories_path, 'w', encoding='utf-8') as f:
                json.dump(self.memories, f, ensure_ascii=False, indent=2)
            self.logger.info(f"已保存 {len(self.memories)} 条记忆")
            return True
        except Exception as e:
            self.logger.error(f"保存记忆失败: {e}")
            return False
    
    def add_memory(self, content: str, importance: float = 0.5, memory_type: str = None) -> str:
        """添加新记忆"""
        import uuid
        from datetime import datetime
        
        memory_id = str(uuid.uuid4())
        
        memory = {
            "id": memory_id,
            "content": content,
            "importance": importance,
            "type": memory_type or "其他",
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
        }
        
        self.memories[memory_id] = memory
        self.save_memories()
        self.logger.info(f"已添加新记忆: {content[:50]}...")
        return memory_id
    
    def search_memories(self, query: str, limit: int = 5, memory_type: str = None) -> List[Dict[str, Any]]:
        """搜索相关记忆"""
        results = []
        
        for memory_id, memory in self.memories.items():
            if query.lower() in memory["content"].lower():
                if memory_type is None or memory.get("type") == memory_type:
                    results.append(memory)
        
        # 按重要性排序
        results.sort(key=lambda x: x.get("importance", 0), reverse=True)
        return results[:limit]
    
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
        
        return {
            "total_memories": total_memories,
            "type_counts": type_counts,
            "average_importance": avg_importance,
            "storage_mode": "文件存储（后备模式）"
        }
    
    def add_association(self, memory_id_1: str, memory_id_2: str, relation_type: str) -> bool:
        """添加记忆关联"""
        # 简化版实现
        return True
    
    def get_associated_memories(self, memory_id: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """获取关联记忆"""
        return []
    
    def export_memories(self, file_path: str, format: str = "json") -> bool:
        """导出记忆"""
        return self.save_memories()
    
    def import_memories(self, file_path: str, format: str = "json") -> bool:
        """导入记忆"""
        return self.load_memories()

# 紧急内存模式管理器
class EmergencyMemoryManager:
    def __init__(self, config):
        self.memories = {}
        self.logger = logging.getLogger("astrbot.plugin.enhanced_memory.emergency")
        self.logger.warning("使用紧急内存模式 - 数据不会持久化")
    
    def add_memory(self, content: str, importance: float = 0.5, memory_type: str = None) -> str:
        """添加新记忆"""
        import uuid
        from datetime import datetime
        
        memory_id = str(uuid.uuid4())
        memory = {
            "id": memory_id,
            "content": content,
            "importance": importance,
            "type": memory_type or "其他",
            "created_at": datetime.now().isoformat(),
        }
        
        self.memories[memory_id] = memory
        self.logger.info(f"已添加记忆到内存: {content[:50]}...")
        return memory_id
    
    def search_memories(self, query: str, limit: int = 5, memory_type: str = None) -> List[Dict[str, Any]]:
        """搜索相关记忆"""
        results = []
        for memory in self.memories.values():
            if query.lower() in memory["content"].lower():
                results.append(memory)
        return results[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取记忆统计信息"""
        return {
            "total_memories": len(self.memories),
            "type_counts": {"内存模式": len(self.memories)},
            "average_importance": 0.5,
            "storage_mode": "紧急内存模式（数据不持久化）"
        }
    
    def save_memories(self):
        """保存记忆 - 在内存模式下无效"""
        self.logger.warning("紧急内存模式不支持持久化存储")
        return False

@register(
    "EnhancedMemory",
    "星辰向鱼",
    "星鱼自制的记忆插件（完整功能修复版）",
    "1.0.0",
    "https://github.com/xing2yu/astrbot_plugin_enhanced_memory",
)
class EnhancedMemoryPlugin(Star):
    def __init__(self, context: Context, config: Optional[Dict[str, Any]] = None):
        super().__init__(context)
        
        # 处理配置参数
        self.config = config or {}
        
        # 设置日志格式
        self.logger = logging.getLogger("astrbot.plugin.enhanced_memory")
        self.logger.handlers = []
        self.logger.propagate = False
        
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
        self._using_fallback = False
        self._using_emergency = False
        
        self.logger.info("EnhancedMemory插件（修复版）初始化完成")
        self.logger.info(f"完整功能可用: {HAS_FULL_FUNCTIONALITY}")
    
    def _initialize(self):
        """同步初始化方法 - 修复版"""
        with self._init_lock:
            if self._initialized:
                return
                
            try:
                # 获取数据目录
                try:
                    data_dir = StarTools.get_data_dir()
                    self.logger.info(f"AstrBot 数据目录: {data_dir}")
                except Exception as e:
                    self.logger.error(f"获取数据目录失败: {e}")
                    data_dir = "data"  # 默认值
                
                # 直接使用插件数据目录，避免嵌套
                storage_path = os.path.join(data_dir, "enhanced_memory")
                self.logger.info(f"最终存储路径: {storage_path}")
                
                # 确保存储路径存在并有写权限
                try:
                    os.makedirs(storage_path, exist_ok=True)
                    self.logger.info(f"存储路径已创建: {storage_path}")
                    
                    # 测试写入权限
                    test_file = os.path.join(storage_path, "permission_test.txt")
                    with open(test_file, 'w', encoding='utf-8') as f:
                        f.write("permission test")
                    os.remove(test_file)
                    self.logger.info("存储路径写入权限验证成功")
                    
                except PermissionError as e:
                    self.logger.error(f"权限错误: {e}")
                    # 使用用户主目录作为后备
                    home_dir = os.path.expanduser("~")
                    storage_path = os.path.join(home_dir, ".astrbot", "plugins", "enhanced_memory")
                    os.makedirs(storage_path, exist_ok=True)
                    self.logger.info(f"使用用户目录作为存储路径: {storage_path}")
                    
                except Exception as e:
                    self.logger.error(f"创建存储路径失败: {e}")
                    # 使用临时目录作为最后的后备
                    storage_path = os.path.join(tempfile.gettempdir(), "astrbot_enhanced_memory")
                    os.makedirs(storage_path, exist_ok=True)
                    self.logger.info(f"使用临时目录作为存储路径: {storage_path}")
                
                self._storage_path = storage_path
                
                # 初始化记忆管理器
                if HAS_FULL_FUNCTIONALITY:
                    try:
                        self.memory_manager = EnhancedMemoryManager({
                            **self.config,
                            "storage_path": storage_path
                        })
                        self._initialized = True
                        self.logger.info("完整功能记忆管理器初始化成功")
                        
                    except Exception as e:
                        self.logger.error(f"完整功能记忆管理器初始化失败: {e}")
                        self._initialize_fallback_manager(storage_path)
                else:
                    self.logger.warning("完整功能不可用，使用后备管理器")
                    self._initialize_fallback_manager(storage_path)
                    
            except Exception as e:
                self.logger.error(f"插件初始化失败: {e}")
                # 最终后备方案
                self._initialize_emergency_fallback()
    
    def _initialize_fallback_manager(self, storage_path):
        """初始化后备记忆管理器"""
        try:
            self.memory_manager = FallbackMemoryManager({"storage_path": storage_path})
            self._initialized = True
            self._using_fallback = True
            self.logger.info("后备记忆管理器初始化成功")
            
        except Exception as e:
            self.logger.error(f"后备管理器初始化失败: {e}")
            self._initialize_emergency_fallback()
    
    def _initialize_emergency_fallback(self):
        """紧急后备方案 - 纯内存模式"""
        self.memory_manager = EmergencyMemoryManager({})
        self._initialized = True
        self._using_emergency = True
        self.logger.info("紧急内存模式激活")
    
    async def ensure_initialized(self):
        """确保插件已初始化"""
        if not self._initialized:
            self._initialize()
    
    # 定义记忆命令组
    @filter.command_group("memory", aliases=["记忆", "内存"])
    def memory_group(self):
        """记忆管理命令组 /memory 或 /记忆 或 /内存"""
        pass
    
    @memory_group.command("add", aliases=["添加"])
    async def memory_add(self, event: AstrMessageEvent, content: str, importance: float = 0.5):
        """添加新记忆 /memory add <内容> [重要性]"""
        try:
            await self.ensure_initialized()
            memory_id = self.memory_manager.add_memory(content, importance)
            mode = "紧急内存" if self._using_emergency else "后备" if self._using_fallback else "完整"
            yield event.plain_result(f"✅ 已添加记忆 (ID: {memory_id}) [模式: {mode}]")
        except Exception as e:
            self.logger.error(f"添加记忆失败: {e}")
            yield event.plain_result("❌ 添加记忆失败")
    
    @memory_group.command("search", aliases=["搜索"])
    async def memory_search(self, event: AstrMessageEvent, query: str, limit: int = 5):
        """搜索记忆 /memory search <查询词> [数量]"""
        try:
            await self.ensure_initialized()
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
        except Exception as e:
            self.logger.error(f"搜索记忆失败: {e}")
            yield event.plain_result("❌ 搜索记忆失败")
    
    @memory_group.command("stats", aliases=["统计"])
    async def memory_stats(self, event: AstrMessageEvent):
        """查看记忆统计 /memory stats"""
        try:
            await self.ensure_initialized()
            stats = self.memory_manager.get_stats()
            
            response = "📊 记忆统计:\n"
            response += f"总记忆数: {stats['total_memories']}\n"
            response += f"平均重要性: {stats['average_importance']:.2f}\n"
            response += f"存储模式: {stats.get('storage_mode', '未知')}\n\n"
            
            response += "按类型统计:\n"
            for mem_type, count in stats['type_counts'].items():
                response += f"  {mem_type}: {count}\n"
            
            # 显示当前模式
            mode = "完整功能" if not self._using_fallback and not self._using_emergency else "后备模式" if self._using_fallback else "紧急内存模式"
            response += f"\n当前模式: {mode}\n"
            
            yield event.plain_result(response)
        except Exception as e:
            self.logger.error(f"获取统计信息失败: {e}")
            yield event.plain_result("❌ 获取统计信息失败")
    
    @memory_group.command("diagnose", aliases=["诊断"])
    async def memory_diagnose(self, event: AstrMessageEvent):
        """诊断记忆插件状态 /memory diagnose"""
        try:
            await self.ensure_initialized()
            
            response = "🔍 记忆插件诊断信息:\n\n"
            response += f"存储路径: {self._storage_path}\n"
            response += f"已初始化: {self._initialized}\n"
            response += f"完整功能可用: {HAS_FULL_FUNCTIONALITY}\n"
            response += f"使用后备模式: {self._using_fallback}\n"
            response += f"使用紧急模式: {self._using_emergency}\n"
            response += f"记忆管理器类型: {type(self.memory_manager).__name__}\n\n"
            
            # 检查文件状态
            if self._storage_path and os.path.exists(self._storage_path):
                memories_path = os.path.join(self._storage_path, "memories.json")
                response += f"记忆文件: {'存在' if os.path.exists(memories_path) else '不存在'}\n"
                
                if os.path.exists(memories_path):
                    try:
                        with open(memories_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            response += f"记忆数量: {len(data)}\n"
                    except Exception as e:
                        response += f"记忆文件读取失败: {e}\n"
            else:
                response += "存储路径不存在\n"
            
            yield event.plain_result(response)
            
        except Exception as e:
            self.logger.error(f"诊断失败: {e}")
            yield event.plain_result("❌ 诊断失败")
    
    @memory_group.command("systeminfo", aliases=["系统信息"])
    async def memory_system_info(self, event: AstrMessageEvent):
        """检查系统信息 /memory systeminfo"""
        import platform
        import sys
        
        response = "🖥️ 系统信息:\n\n"
        response += f"操作系统: {platform.system()} {platform.release()}\n"
        response += f"Python版本: {sys.version}\n"
        response += f"工作目录: {os.getcwd()}\n"
        response += f"插件存储路径: {getattr(self, '_storage_path', '未设置')}\n"
        
        # 检查重要目录的权限
        important_dirs = [
            os.getcwd(),
            getattr(self, '_storage_path', ''),
            "data",
            "data/plugin_data"
        ]
        
        response += "\n目录权限检查:\n"
        for dir_path in important_dirs:
            if dir_path and os.path.exists(dir_path):
                try:
                    test_file = os.path.join(dir_path, "test.tmp")
                    with open(test_file, 'w', encoding='utf-8') as f:
                        f.write("test")
                    os.remove(test_file)
                    response += f"  {dir_path}: ✅ 可读写\n"
                except:
                    response += f"  {dir_path}: ❌ 无写权限\n"
            elif dir_path:
                response += f"  {dir_path}: ❌ 目录不存在\n"
        
        yield event.plain_result(response)
    
    @memory_group.command("export", aliases=["导出"])
    async def memory_export(self, event: AstrMessageEvent, format: str = "json"):
        """导出记忆 /memory export [格式:json/csv]"""
        try:
            await self.ensure_initialized()
            if hasattr(self.memory_manager, 'export_memories'):
                file_path = os.path.join(self._storage_path, f"memories_export.{format}")
                if self.memory_manager.export_memories(file_path, format):
                    yield event.plain_result(f"✅ 记忆已导出到 {file_path}")
                else:
                    yield event.plain_result("❌ 导出记忆失败")
            else:
                yield event.plain_result("❌ 当前模式不支持导出功能")
        except Exception as e:
            self.logger.error(f"导出记忆失败: {e}")
            yield event.plain_result("❌ 导出记忆失败")
    
    @memory_group.command("import", aliases=["导入"])
    async def memory_import(self, event: AstrMessageEvent, format: str = "json"):
        """导入记忆 /memory import [格式:json/csv]"""
        try:
            await self.ensure_initialized()
            if hasattr(self.memory_manager, 'import_memories'):
                file_path = os.path.join(self._storage_path, f"memories_export.{format}")
                if self.memory_manager.import_memories(file_path, format):
                    yield event.plain_result(f"✅ 已从 {file_path} 导入记忆")
                else:
                    yield event.plain_result("❌ 导入记忆失败")
            else:
                yield event.plain_result("❌ 当前模式不支持导入功能")
        except Exception as e:
            self.logger.error(f"导入记忆失败: {e}")
            yield event.plain_result("❌ 导入记忆失败")
    
    async def terminate(self):
        """插件停止时的清理逻辑"""
        self.logger.info("EnhancedMemory插件正在停止...")
        try:
            if self._initialized and hasattr(self.memory_manager, 'save_memories'):
                self.memory_manager.save_memories()
            self.logger.info("EnhancedMemory插件已成功停止。")
        except Exception as e:
            self.logger.error(f"插件停止时保存记忆失败: {e}")