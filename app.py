"""
后端应用入口文件
功能：
1. 启动 FastAPI 服务
2. 加载路由控制器
"""
import sys
from pathlib import Path
import os

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging

from config.logging_config import setup_logging
from config.env_loader import EnvLoader

# 导入控制器
from controllers.document_controller import router as document_router
from controllers.rag_controller import router as rag_router
from controllers.copilot_controller import router as copilot_router

# 配置日志
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("=" * 60)
    logger.info("🚀 启动企业级知识库伴写系统")
    logger.info("=" * 60)
    
    # 加载环境变量
    EnvLoader.load()
    
    yield  # 应用运行期间
    
    # 关闭时执行
    logger.info("")
    logger.info("=" * 60)
    logger.info("🛑 关闭应用")
    logger.info("=" * 60)

# 创建 FastAPI 应用
app = FastAPI(
    title="企业级知识库伴写系统",
    description="基于 RAG 的智能规章制度起草与知识检索系统",
    version="1.0.0",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许的源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# 注册路由
app.include_router(document_router, prefix="/api")
app.include_router(rag_router, prefix="/api")
app.include_router(copilot_router, prefix="/api")

from fastapi.responses import RedirectResponse

@app.get("/")
async def root():
    """根路径自动重定向到伴写前端界面"""
    return RedirectResponse(url="/api/copilot/ui")

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy"
    }

if __name__ == "__main__":
    # 配置日志
    setup_logging(log_level=logging.INFO)
    
    PORT = int(os.getenv("PORT", 8000))
    HOST = os.getenv("HOST", "0.0.0.0")
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("🚀 正在启动企业级知识库伴写系统...")
    logger.info("=" * 70)
    logger.info(f"🌍 服务地址: http://localhost:{PORT}")
    logger.info(f"📚 API 文档: http://localhost:{PORT}/docs")
    logger.info(f"🔥 伴写演示: http://localhost:{PORT}/api/copilot/ui")
    logger.info("=" * 70)
    logger.info("💡 提示: 按 Ctrl+C 停止服务")
    logger.info("")
    
    try:
        uvicorn.run(
            "app:app",
            host=HOST,
            port=PORT,
            reload=True,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        pass
