# astrbot_plugin_enhanced_memory（可能不太好用）
⚙️ 环境配置
必需依赖
bash
# 基础依赖（必需）
pip install jieba pydantic
增强依赖（推荐安装）
bash
# 语义搜索功能
pip install faiss-cpu sentence-transformers

# 记忆图谱功能  
pip install networkx

# AI梳理功能（需要LLM提供商）
pip install transformers torch
完整一键安装
bash
pip install jieba pydantic faiss-cpu sentence-transformers networkx transformers torch
🔧 AstrBot配置
1. 启用插件
启动AstrBot

访问WebUI (通常是 http://localhost:8000)

进入"插件管理"

找到"增强记忆插件 v3.0"

点击"启用"

2. 配置LLM提供商（AI梳理功能必需）
进入"设置" → "AI提供商"

添加你喜欢的LLM提供商：

OpenAI GPT系列

Azure OpenAI

其他兼容的LLM服务

配置API密钥和参数

保存配置

3. 插件配置（可选）
在插件配置页面可以调整：

存储路径: 记忆数据保存位置

自动提取: 是否从对话自动提取记忆

AI梳理: 启用智能记忆整理

搜索设置: 搜索结果数量和搜索方式

🚀 基础使用
1. 添加记忆
bash
# 基础添加
/memo_add "用户喜欢蓝色"

# 带重要性评分
/memo_add "用户是程序员" --importance 0.8

# 指定类型
/memo_add "明天要开会" --type event
2. 搜索记忆
bash
# 基础搜索
/memo_search "颜色"

# 限制结果数量
/memo_search "工作" 10

# 语义搜索（需要sentence-transformers）
/memo_search "编程相关" --use_semantic
3. 管理记忆
bash
# 查看统计
/memo_stats

# 删除记忆（需要记忆ID）
/memo_delete "记忆ID"

# 关联记忆
/memo_associate "记忆ID1" "记忆ID2"
🤖 高级功能
AI智能梳理
bash
# 全面梳理记忆库
/memo_organize all

# 指定任务梳理
/memo_organize categorize,suggest_associations

# 使用特定模型
/memo_organize all model_id=your_model_id

# 应用梳理建议
/memo_apply_org
数据管理
bash
# 导出记忆（JSON格式）
/memo_export json

# 导出记忆（CSV格式）
/memo_export csv

# 导入记忆
/memo_import "路径/记忆文件.json"
系统信息
bash
# 检查依赖状态
/memo_deps

# 查看可用AI模型
/memo_models

# 显示完整帮助
/memo_help
💡 使用技巧
1. 自动化记忆提取
插件会自动从对话中提取重要信息

包含个人信息、偏好、事实等内容

可配置提取敏感度

2. 智能关联建立
自动基于关键词相似度建立记忆关联

支持手动建立特定关联

关联记忆会在搜索时一并显示

3. AI梳理最佳实践
bash
# 定期梳理保持记忆库整洁
/memo_organize all

# 先预览再应用
/memo_organize categorize
/memo_apply_org

# 针对性梳理特定问题
/memo_organize find_duplicates
🎯 实战示例
场景一：个人助理
bash
# 记录用户偏好
/memo_add "用户不喜欢吃辣"
/memo_add "用户每天早9点上班"

# 搜索相关信息
/memo_search "饮食偏好"
/memo_search "工作时间"
场景二：知识管理
bash
# 添加技术知识
/memo_add "Python的GIL是全局解释器锁"
/memo_add "JavaScript是单线程语言"

# 建立知识关联
/memo_associate "记忆ID1" "记忆ID2"

# AI梳理知识结构
/memo_organize categorize,suggest_associations
场景三：项目跟踪
bash
# 记录项目信息
/memo_add "项目A需要在周五前完成"
/memo_add "客户对UI颜色有特殊要求"

# 导出项目记忆
/memo_export json
🔍 故障排除
常见问题
Q: 插件无法加载

text
A: 检查：
1. 插件目录是否正确：AstrBot/data/plugins/astrbot_plugin_enhanced_memory
2. 依赖是否安装：pip install jieba pydantic
3. 查看AstrBot日志文件
Q: AI梳理功能不可用

text
A: 检查：
1. LLM提供商是否配置正确
2. API密钥是否有效
3. 网络连接是否正常
Q: 语义搜索不工作

text
A: 安装依赖：
pip install faiss-cpu sentence-transformers
Q: 记忆数据丢失

text
A: 数据存储在：data/plugin_data/enhanced_memory/
定期使用 /memo_export 备份数据
日志检查
查看AstrBot日志了解详细状态：

bash
# 查看实时日志
tail -f AstrBot/logs/astrbot.log

# 搜索插件相关日志
grep "enhanced_memory" AstrBot/logs/astrbot.log
📊 功能对比
功能	基础版	增强版	完整版
基础记忆管理	✅	✅	✅
自动记忆提取	✅	✅	✅
关键词搜索	  ✅	✅	✅
语义向量搜索	❌	✅	✅
记忆关联      ❌	✅	✅
AI智能梳理	  ❌	✅	✅
数据导入导出	❌	✅	✅
多模型支持	  ❌	❌	✅
🎉 进阶技巧
1. 批量操作
python
# 可以通过脚本批量导入记忆
import json
memories = {
    "记忆1": {"content": "内容1", "type": "fact"},
    "记忆2": {"content": "内容2", "type": "preference"}
}
with open("batch_import.json", "w") as f:
    json.dump(memories, f)
# 然后使用 /memo_import 导入
2. 自定义配置
在 _conf_schema.json 中可以自定义：

记忆分类类型

自动提取规则

搜索参数

AI梳理任务

3. 集成工作流
将记忆插件与其他插件结合：

与任务管理插件联动

与日程安排插件集成

作为AI对话的长期记忆库
✨ 现在就开始使用增强记忆插件，打造属于你的智能记忆系统！
# 支持

[帮助文档](https://astrbot.app)
