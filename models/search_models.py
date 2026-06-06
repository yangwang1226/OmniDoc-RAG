"""
搜索相关的数据模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from config.milvus_collections import FILE_EMBEDDING_COLLECTION_NAME


class SearchRequest(BaseModel):
    """检索请求模型"""
    query: str = Field(..., description="检索关键词", min_length=1)
    top_k: Optional[int] = Field(10, description="返回结果数量", ge=1, le=100)
    collection_name: Optional[str] = Field(FILE_EMBEDDING_COLLECTION_NAME, description="集合名称")
    score_threshold: Optional[float] = Field(0.5, description="相似度阈值", ge=0.0, le=1.0)
    enable_rerank: Optional[bool] = Field(True, description="是否启用重排序")
    final_top_n: Optional[int] = Field(3, description="重排序后的结果数量", ge=1, le=20)
    enable_answer: Optional[bool] = Field(True, description="是否生成答案")
    stream: Optional[bool] = Field(True, description="是否使用流式输出")


class SearchResult(BaseModel):
    """检索结果模型"""
    chunk_id: str
    file_id: int
    file_name: str
    content: str
    score: float
    metadata: Dict[str, Any]


class SearchResponse(BaseModel):
    """检索响应模型"""
    success: bool
    message: str
    total: int
    results: List[SearchResult]
    answer: Optional[str] = None
    stats: Dict[str, Any]


class FeedbackRequest(BaseModel):
    """反馈请求模型"""
    request_id: str = Field(..., description="请求ID")
    is_useful: bool = Field(..., description="是否有用")
    feedback_text: Optional[str] = Field(None, description="反馈文字")
    clicked_file_ids: Optional[List[str]] = Field(None, description="点击的文件ID列表")
    clicked_chunk_ids: Optional[List[str]] = Field(None, description="点击的chunk ID列表")


class FeedbackResponse(BaseModel):
    """反馈响应模型"""
    success: bool = Field(..., description="是否更新成功")
    message: str = Field(..., description="提示信息")