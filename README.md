# 记忆插件（可能不太好用）
好吧，真的不太好用！！！
最起码这一版不行...

可以在文件memory_extractor内更改自动记忆的具体存储规则


一下为具体命令


英文：
/memory add <内容> [重要性]

/memory search <查询词> [数量]

/memory associate <ID1> <ID2> <关系类型>

/memory export [格式:json/csv]

/memory import [格式:json/csv]

/memory stats


中文：
/记忆添加 <内容> [重要性]

/记忆搜索 <查询词> [数量]

/记忆关联 <ID1> <ID2> <关系类型>

/记忆导出 [格式:json/csv]

/记忆导入 [格式:json/csv]

/记忆统计


主要命令组

英文

/memory - 记忆管理命令组

中文

/记忆 - 记忆管理命令组（中文别名）

/内存 - 记忆管理命令组（中文别名）


具体命令

1. 添加记忆
2. 
英文命令: /memory add <内容> [重要性]

中文命令: /记忆添加 <内容> [重要性] 或 /内存添加 <内容> [重要性]

功能: 添加新记忆到系统中

参数:

<内容>: 要添加的记忆内容（必需）

[重要性]: 记忆的重要性评分，范围0.0-1.0（可选，默认0.5）

2. 搜索记忆
英文命令: /memory search <查询词> [数量]

中文命令: /记忆搜索 <查询词> [数量] 或 /内存搜索 <查询词> [数量]

功能: 搜索相关记忆

参数:

<查询词>: 搜索关键词（必需）

[数量]: 返回结果的最大数量（可选，默认5）

3. 关联记忆

英文命令: /memory associate <ID1> <ID2> <关系类型>

中文命令: /记忆关联 <ID1> <ID2> <关系类型> 或 /内存关联 <ID1> <ID2> <关系类型>

功能: 关联两个记忆

参数:

<ID1>: 第一个记忆的ID（必需）

<ID2>: 第二个记忆的ID（必需）

<关系类型>: 关联关系类型（必需）

4. 导出记忆

英文命令: /memory export [格式]

中文命令: /记忆导出 [格式] 或 /内存导出 [格式]

功能: 导出所有记忆到文件

参数:

[格式]: 导出格式，支持json或csv（可选，默认json）

5. 导入记忆

英文命令: /memory import [格式]

中文命令: /记忆导入 [格式] 或 /内存导入 [格式]

功能: 从文件导入记忆

参数:

[格式]: 导入格式，支持json或csv（可选，默认json）

6. 查看统计

英文命令: /memory stats

中文命令: /记忆统计 或 /内存统计

功能: 查看记忆统计信息

参数: 无

API方法（供其他插件调用）

除了用户命令外，该插件还提供以下API方法供其他插件调用：

add_memory_api(content: str, importance: float = 0.5, memory_type: str = None) -> str

添加新记忆

search_memories_api(query: str, limit: int = 5, memory_type: str = None) -> List[Dict[str, Any]]

搜索记忆

get_associated_memories_api(memory_id: str, max_results: int = 5) -> List[Dict[str, Any]]

获取关联记忆



使用示例

添加记忆：

/memory add 我喜欢编程 0.8

/记忆添加 我最喜欢的水果是苹果 0.9

搜索记忆：


/memory search 编程

/记忆搜索 水果

查看统计：


/memory stats

/记忆统计

导出记忆：

/memory export json

/记忆导出 csv

A template plugin for AstrBot plugin feature

# 支持

[帮助文档](https://astrbot.app)
