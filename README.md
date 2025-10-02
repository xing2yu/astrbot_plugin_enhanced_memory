# astrbot_plugin_enhanced_memory（可能不太好用）
需要手动安装依赖

可以在文件memory_extractor内更改自动记忆的具体存储规则


步骤1：以管理员身份运行命令提示符
按 Win + X，选择"Windows PowerShell（管理员）"或"命令提示符（管理员）"

步骤2：执行安装命令
复制以下命令到管理员命令提示符中执行：

bash
pip install networkx faiss-cpu sentence-transformers jieba numpy transformers torch --upgrade
步骤3：如果遇到网络问题，使用国内镜像：
bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple networkx faiss-cpu sentence-transformers jieba numpy transformers torch --upgrade
🔧 Windows 特定优化安装
由于你是 Windows 系统，某些包可能需要特殊处理：

如果 torch 安装失败，使用官方命令：
bash
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
如果 faiss-cpu 安装失败，尝试：
bash
# 先安装依赖
pip install numpy
# 然后安装 faiss
pip install faiss-cpu --no-cache-dir
专门的验证脚本
运行验证脚本：
bash
python check_enhanced_deps.py

常见问题解决方案：
问题1：torch 安装失败

bash
# 使用官方PyTorch安装命令
pip install torch --index-url https://download.pytorch.org/whl/cpu
问题2：faiss-cpu 安装失败

bash
# 先确保numpy已安装
pip install numpy
# 然后安装faiss
pip install faiss-cpu --no-cache-dir --force-reinstall
问题3：内存不足

关闭其他应用程序

分批安装依赖

📊 预期结果
安装成功后，/memory stats 应该显示类似这样的信息：

text
📊 记忆统计:
总记忆数: 3
平均重要性: 0.50
存储模式: 完整功能模式

按类型统计:
  观点: 1
  事件: 1  
  其他: 1

组件状态:
  FAISS向量搜索: ✅ 可用
  智能分类器: ✅ 可用
  记忆关联图: ✅ 可用
  自动提取器: ✅ 可用
# 支持

[帮助文档](https://astrbot.app)
