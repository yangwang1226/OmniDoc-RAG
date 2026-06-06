""" 
向量数据库连接模块
目前默认使用本地 Qdrant 作为向量数据库，轻量级，支持一键部署
"""
import logging
from .qdrant_client import QdrantAdapter as VectorDBClient

logger = logging.getLogger(__name__)

def get_vector_db_client():
    """
    获取向量数据库客户端实例
    
    Returns:
        VectorDBClient (基于 Qdrant)
    """
    return VectorDBClient()

__all__ = ['VectorDBClient', 'get_vector_db_client']
