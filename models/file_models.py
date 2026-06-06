"""
文件管理相关的数据模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional

# ==================== 请求/响应模型 ====================

class UpdateNodeSchoolIdsRequest(BaseModel):
    """更新节点学校ID请求模型"""
    material_id: int = Field(..., description="素材ID")
    node_school_ids: List[int] = Field(..., description="新的节点学校ID列表")


class UpdateNodeSchoolIdsResponse(BaseModel):
    """更新节点学校ID响应模型"""
    material_id: int
    updated_count: int
    node_school_ids: List[int]

class UpdateIsSearchableRequest(BaseModel):
    """更新是否允许搜索请求模型"""
    material_ids: Optional[List[int]] = Field(None, description="素材ID列表")
    file_id: Optional[str] = Field(None, description="文件ID")
    deleted_type: int = Field(..., description="是否允许搜索", ge=0, le=1)

class UpdateIsSearchableResponse(BaseModel):
    """更新是否允许搜索响应模型"""
    material_ids: Optional[List[int]] = Field(None, description="素材ID列表")
    file_id: Optional[str] = Field(None, description="文件ID")
    updated_count: int