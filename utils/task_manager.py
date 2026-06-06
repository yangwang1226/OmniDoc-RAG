"""
任务状态管理器
支持 Memory (单机) 和 Redis (集群) 两种存储模式
用于存储诸如大文件异步向量化的进度状态
"""
import json
import logging
from typing import Dict, Any, Optional
from config.env_loader import EnvLoader

logger = logging.getLogger(__name__)

class TaskManager:
    _instance = None
    _memory_store = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
        
    def _initialize(self):
        self.mode = EnvLoader.get('TASK_STATE_MODE', 'memory').lower()
        self.redis_client = None
        
        if self.mode == 'redis':
            try:
                import redis
                host = EnvLoader.get('REDIS_HOST', 'localhost')
                port = EnvLoader.get_int('REDIS_PORT', 6379)
                password = EnvLoader.get('REDIS_PASSWORD', '')
                db = EnvLoader.get_int('REDIS_DB', 0)
                
                self.redis_client = redis.Redis(
                    host=host, 
                    port=port, 
                    password=password if password else None, 
                    db=db,
                    decode_responses=True
                )
                # 测试连接
                self.redis_client.ping()
                logger.info(f"🚀 TaskManager 已启动 [Redis 模式] ({host}:{port})")
            except ImportError:
                logger.error("❌ 缺失 redis 依赖，请执行: pip install redis")
                logger.warning("⚠️ 自动降级为 [Memory 模式]")
                self.mode = 'memory'
            except Exception as e:
                logger.error(f"❌ Redis 连接失败: {e}")
                logger.warning("⚠️ 自动降级为 [Memory 模式]")
                self.mode = 'memory'
        
        if self.mode == 'memory':
            logger.info("🚀 TaskManager 已启动 [Memory 模式] (适用于单机部署)")
            
    def set_task(self, task_id: str, status_data: Dict[str, Any], expire_seconds: int = 86400):
        """
        更新任务状态
        Args:
            task_id: 唯一任务 ID
            status_data: 状态数据 (如 {"status": "processing", "progress": 50})
            expire_seconds: 过期时间 (默认 1 天)
        """
        try:
            if self.mode == 'redis' and self.redis_client:
                self.redis_client.setex(
                    f"task:{task_id}", 
                    expire_seconds, 
                    json.dumps(status_data)
                )
            else:
                self._memory_store[task_id] = status_data
        except Exception as e:
            logger.error(f"任务状态保存失败 ({task_id}): {e}")

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态
        """
        try:
            if self.mode == 'redis' and self.redis_client:
                data = self.redis_client.get(f"task:{task_id}")
                return json.loads(data) if data else None
            else:
                return self._memory_store.get(task_id)
        except Exception as e:
            logger.error(f"任务状态读取失败 ({task_id}): {e}")
            return None
            
    def delete_task(self, task_id: str):
        """删除任务"""
        if self.mode == 'redis' and self.redis_client:
            self.redis_client.delete(f"task:{task_id}")
        else:
            self._memory_store.pop(task_id, None)

# 提供一个全局可用的单例
task_manager = TaskManager()
