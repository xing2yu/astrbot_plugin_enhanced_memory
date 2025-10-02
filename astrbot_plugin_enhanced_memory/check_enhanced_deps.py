import sys
import importlib

def check_detailed_dependencies():
    print("🔍 详细依赖检查 - 增强记忆插件")
    print("=" * 60)
    
    dependencies = [
        ("networkx", "2.8+", "记忆关联图"),
        ("faiss", "1.7+", "向量语义搜索"),
        ("sentence_transformers", "2.2+", "文本嵌入模型"),
        ("jieba", "0.42+", "中文分词"),
        ("numpy", "1.24+", "数值计算"),
        ("transformers", "4.30+", "自然语言处理"),
        ("torch", "2.0+", "深度学习框架")
    ]
    
    print(f"Python 版本: {sys.version}")
    print(f"Python 路径: {sys.executable}")
    print("=" * 60)
    
    all_success = True
    functionality_status = {}
    
    for package, min_version, description in dependencies:
        try:
            module = importlib.import_module(package)
            version = getattr(module, '__version__', '未知版本')
            
            # 简单版本检查（移除复杂的版本比较）
            status = "✅"
            try:
                # 尝试简单版本比较
                if package == "networkx" and int(version.split('.')[0]) >= 2:
                    status = "✅"
                elif package == "faiss" and int(version.split('.')[0]) >= 1:
                    status = "✅" 
                elif package == "sentence_transformers" and int(version.split('.')[0]) >= 2:
                    status = "✅"
                else:
                    status = "⚠️"
            except:
                status = "✅"  # 如果版本检查失败，默认为成功
                
            print(f"{status} {package:25} {version:15} - {description}")
            functionality_status[package] = True
            
        except ImportError as e:
            print(f"❌ {package:25} {'未安装':15} - {description}")
            print(f"   错误: {e}")
            functionality_status[package] = False
            all_success = False
    
    print("=" * 60)
    
    # 功能可用性报告
    print("📊 功能可用性报告:")
    print("-" * 40)
    
    if functionality_status.get("networkx"):
        print("✅ 记忆关联图 - 可用")
    else:
        print("❌ 记忆关联图 - 不可用")
        
    if functionality_status.get("faiss") and functionality_status.get("sentence_transformers"):
        print("✅ 语义向量搜索 - 可用")
    else:
        print("❌ 语义向量搜索 - 不可用")
        
    if functionality_status.get("jieba"):
        print("✅ 中文关键词提取 - 可用")
    else:
        print("❌ 中文关键词提取 - 不可用")
        
    if functionality_status.get("transformers") and functionality_status.get("torch"):
        print("✅ 智能分类 - 可用")
    else:
        print("❌ 智能分类 - 不可用")
    
    print("=" * 60)
    
    if all_success:
        print("🎉 所有依赖安装成功！完整功能已启用！")
        print("\n你现在可以享受：")
        print("  • 智能语义搜索（理解同义词和相似概念）")
        print("  • 自动记忆分类（智能识别记忆类型）")
        print("  • 记忆关联网络（发现记忆之间的联系）")
        print("  • 自动信息提取（从对话中智能提取重要信息）")
    else:
        print("⚠️ 部分依赖缺失，某些功能受限")
        print("\n缺失依赖安装命令：")
        missing = [pkg for pkg, installed in functionality_status.items() if not installed]
        if missing:
            print(f"pip install {' '.join(missing)}")
        
    return all_success

if __name__ == "__main__":
    check_detailed_dependencies()