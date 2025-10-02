import os
import tempfile
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FileSystemDiagnose")

def diagnose_filesystem():
    """诊断文件系统访问权限"""
    print("=== 文件系统诊断开始 ===")
    
    # 测试当前工作目录
    cwd = os.getcwd()
    print(f"当前工作目录: {cwd}")
    print(f"可写: {os.access(cwd, os.W_OK)}")
    
    # 测试常见的数据目录
    test_dirs = [
        "data",
        "data/plugin_data",
        "data/plugin_data/enhanced_memory",
        tempfile.gettempdir() + "/enhanced_memory"
    ]
    
    for test_dir in test_dirs:
        print(f"\n测试目录: {test_dir}")
        try:
            # 确保目录存在
            os.makedirs(test_dir, exist_ok=True)
            print(f"  ✓ 目录创建/访问成功")
            
            # 测试写入权限
            test_file = os.path.join(test_dir, "test_write.txt")
            with open(test_file, 'w') as f:
                f.write("test content")
            print(f"  ✓ 文件写入成功")
            
            # 测试读取权限
            with open(test_file, 'r') as f:
                content = f.read()
            print(f"  ✓ 文件读取成功: {content}")
            
            # 清理测试文件
            os.remove(test_file)
            print(f"  ✓ 文件删除成功")
            
        except Exception as e:
            print(f"  ✗ 错误: {e}")
    
    print("\n=== 文件系统诊断完成 ===")

if __name__ == "__main__":
    diagnose_filesystem()