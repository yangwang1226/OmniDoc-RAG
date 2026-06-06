"""
基础响应模型
"""
from pydantic import BaseModel, Field
from typing import Generic, TypeVar, Optional

# 定义泛型类型变量
T = TypeVar('T')


class BaseResponse(BaseModel, Generic[T]):
    """
    基础响应模型（对应 Java CommonResult<T>）
    """
    code: str = Field(default="200", description="状态码")
    message: str = Field(..., description="响应消息")
    success: bool = Field(..., description="操作是否成功")
    data: Optional[T] = Field(default=None, description="响应数据")
    traceId: Optional[str] = Field(default=None, description="追踪ID")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "200",
                "message": "操作成功",
                "success": True,
                "data": None,
                "traceId": None
            }
        }

    @classmethod
    def ok(cls, data: T = None, message: str = "操作成功", trace_id: Optional[str] = None) -> "BaseResponse[T]":
        """创建成功响应（使用 ok 避免与 success 字段冲突）"""
        return cls(
            code="200",
            message=message,
            success=True,
            data=data,
            traceId=trace_id
        )

    @classmethod
    def fail(cls, code: str = "500", message: str = "操作失败", trace_id: Optional[str] = None) -> "BaseResponse[None]":
        """创建错误响应"""
        return cls(
            code=code,
            message=message,
            success=False,
            data=None,
            traceId=trace_id
        )