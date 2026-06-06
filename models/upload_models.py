from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class UploadFileRequest(BaseModel):
    """文件上传请求模型"""
    file_id: str = Field(..., description="文件ID")
    node_school_ids: List[int] = Field(..., description="节点学校ID列表")
    file_url: str = Field(..., description="可下载的文件密钥地址")
    space_id: int = Field(..., description="空间ID")
    material_id: int = Field(..., description="素材ID")
    material_school_ids: Optional[List[int]] = Field(None, description="素材学校ID列表（可选）")

class UploadContentRequest(BaseModel):
    """内容上传请求模型"""
    file_id: str = Field(..., description="文件ID")
    file_name: str = Field(..., description="文件名称")
    file_extension: str = Field(..., description="文件类型")
    content: str = Field(..., description="内容")
    node_school_ids: List[int] = Field(..., description="节点学校ID列表")
    space_id: int = Field(..., description="空间ID")
    material_id: int = Field(..., description="素材ID")
    material_school_ids: Optional[List[int]] = Field(None, description="素材学校ID列表（可选）")

class ProcessResponse(BaseModel):
    """处理响应模型"""
    file_id: str
    chunks_count: int
    embeddings_count: int
    processing_time: float

# 新增：异步任务响应模型
class AsyncTaskResponse(BaseModel):
    """异步任务响应模型"""
    file_id: str
    task_id: Optional[str] = None
    status: str = "pending"  # "pending", "processing", "completed", "failed"