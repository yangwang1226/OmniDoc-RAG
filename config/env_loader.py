"""
环境配置加载器
优先读取根目录下的 .env 文件
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class EnvLoader:
    """环境配置加载器"""
    
    _loaded = False
    
    @classmethod
    def load(cls) -> bool:
        """
        加载环境配置文件
        """
        if cls._loaded:
            return True
        
        # 构建配置文件路径 (.env)
        project_root = Path(__file__).parent.parent
        env_file = project_root / '.env'
        
        if not env_file.exists():
            print("\n" + "=" * 60)
            print("[致命错误] 未找到 .env 配置文件！")
            print("\n解决办法：")
            print("  请在项目根目录下，将 '.env.example' 复制并重命名为 '.env'")
            print("  然后打开 '.env' 文件填写您的配置信息。")
            print("=" * 60 + "\n")
            import sys
            sys.exit(1)
        
        # 加载配置文件
        load_dotenv(env_file, override=True)
        cls._loaded = True
        
        print("=" * 60)
        print(f"[INFO] 环境变量加载成功: {env_file.name}")
        print("=" * 60)
        
        return True
    
    @classmethod
    def get(cls, key: str, default: Optional[str] = None) -> Optional[str]:
        """获取环境变量"""
        return os.getenv(key, default)
    
    @staticmethod
    def get_int(key: str, default: int = 0) -> int:
        """获取整数类型环境变量"""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            return default
    
    @staticmethod
    def get_float(key: str, default: float = 0.0) -> float:
        """获取浮点数类型环境变量"""
        try:
            return float(os.getenv(key, str(default)))
        except ValueError:
            return default
    
    @staticmethod
    def get_bool(key: str, default: bool = False) -> bool:
        """获取布尔类型环境变量"""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')

# 自动加载（导入时执行）
EnvLoader.load()
