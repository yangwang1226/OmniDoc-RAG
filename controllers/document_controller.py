from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Form
import os
import uuid
from typing import Dict, Any
import logging

from utils.task_manager import task_manager
from service.doc_chunking_service import DocChunkingService
from service.embedding_service import EmbeddingService
from vector_db import get_vector_db_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/document", tags=["1. 文档管理与知识库"])
COLLECTION_NAME = "enterprise_knowledge_base"

def process_file_async(task_id: str, file_path: str, file_name: str, category: str = None):
    """后台异步向量化处理流"""
    try:
        logger.info(f"[Document] 开始处理文件: {file_name} (Task: {task_id})")
        
        task_manager.set_task(task_id, {
            "status": "processing",
            "file_name": file_name,
            "progress": 10,
            "message": "正在切分文档块..."
        })
        
        # 1. 切片
        chunking_service = DocChunkingService()
        chunk_result = chunking_service.chunk_document_with_hierarchy(file_path)
        
        child_chunks = chunk_result.get('child_chunks', [])
        if not child_chunks:
            msg = "文件切片失败，没有生成任何块"
            logger.error(f"[Document] {msg}: {file_name}")
            task_manager.set_task(task_id, {"status": "error", "file_name": file_name, "message": msg})
            return
            
        task_manager.set_task(task_id, {
            "status": "processing",
            "file_name": file_name,
            "progress": 30,
            "message": f"切分完成，共 {len(child_chunks)} 个数据块。正在调用大模型向量化..."
        })
        
        # 2. 向量化
        file_id = f"doc_{uuid.uuid4().hex[:16]}"
        file_ext = os.path.splitext(file_name)[1].replace('.', '') or 'unknown'
        
        embedding_service = EmbeddingService()
        embedding_result = embedding_service.embedding_for_demo(
            file_id=file_id,
            file_name=file_name,
            chunk_result=chunk_result,
            file_extension=file_ext,
            category=category,
            task_id=task_id
        )
        
        if not embedding_result.get('success'):
            err_msg = embedding_result.get('error', '未知向量化错误')
            logger.error(f"[Document] 向量化失败: {err_msg}")
            task_manager.set_task(task_id, {"status": "error", "file_name": file_name, "message": f"向量化失败: {err_msg}"})
            return
        
        entities = embedding_result.get('entities', [])
        
        task_manager.set_task(task_id, {
            "status": "processing",
            "file_name": file_name,
            "progress": 90,
            "message": "正在将向量数据写入本地 Qdrant 数据库..."
        })
        
        # 3. 入库
        vector_db = get_vector_db_client()
        vector_db.connect()
        
        success = vector_db.insert_data(
            collection_name=COLLECTION_NAME,
            data=entities
        )
        
        if success:
            logger.info(f"[Document] ✅ {file_name} 成功插入 {len(entities)} 条数据")
            task_manager.set_task(task_id, {
                "status": "completed",
                "file_name": file_name,
                "progress": 100,
                "message": "✅ 入库完成！",
                "stats": {"total": len(entities)}
            })
        else:
            logger.error(f"[Document] ❌ {file_name} 插入数据库失败")
            task_manager.set_task(task_id, {"status": "error", "file_name": file_name, "message": "写入数据库失败"})
            
        vector_db.disconnect()
        
        # 清理临时文件
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        logger.error(f"[Document] 处理异常: {e}", exc_info=True)
        task_manager.set_task(task_id, {"status": "error", "file_name": file_name, "message": f"系统异常: {str(e)}"})

@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category: str = Form(None)
) -> Dict[str, Any]:
    """上传文档并触发异步向量化入库处理"""
    try:
        temp_dir = "temp_file"
        os.makedirs(temp_dir, exist_ok=True)
        file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'unknown'
        save_name = f"doc_{uuid.uuid4().hex}.{file_ext}"
        file_path = os.path.join(temp_dir, save_name)
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            
        logger.info(f"[Document] 文件已保存到本地: {file_path}, 分类: {category}")
        
        # 初始化任务状态
        task_id = str(uuid.uuid4())
        task_manager.set_task(task_id, {
            "status": "processing",
            "file_name": file.filename,
            "progress": 0,
            "message": "正在准备解析文件..."
        })
        
        # 添加到后台任务
        background_tasks.add_task(process_file_async, task_id, file_path, file.filename, category)
        
        return {
            "code": 200, 
            "message": "文件已接收，正在后台处理...",
            "data": {
                "task_id": task_id,
                "file_name": file.filename
            }
        }
    except Exception as e:
        logger.error(f"[Document] 上传异常: {e}", exc_info=True)
        return {"code": 500, "message": str(e)}

@router.get("/task_status/{task_id}")
async def get_task_status(task_id: str):
    """获取异步上传任务的处理进度"""
    status_data = task_manager.get_task(task_id)
    if not status_data:
        return {"code": 404, "message": "未找到该任务"}
    return {"code": 200, "data": status_data}
