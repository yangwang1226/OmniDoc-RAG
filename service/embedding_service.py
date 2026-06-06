import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from service.base_service import BaseService
from logging import Logger
from typing import List, Dict
from vector_db import get_vector_db_client
from utils.task_manager import task_manager
# 新的（正确）
from langchain_core.documents import Document
import time
import os

# 向量检索服务
class EmbeddingService(BaseService):
    def __init__(self):
        super().__init__()
        self.vector_db = get_vector_db_client()
        self.vector_db.connect()
        self.collection_name = "file_embedding"

    # 批量处理父子块（只保存子块，父块作为 metadata）
    def embedding_child_chunks_batch(self, file_id: int, file_name: str,
                                 node_school_ids: List[int],  # 节点学校ID列表
                                 space_id: int,          # 空间ID
                                 material_id: int,       # 素材ID
                                 chunk_result: Dict,
                                 file_path: str = None,
                                 file_extension: str = None,
                                 material_school_ids: List[int] = None) -> Dict:
        """
        批量处理父子块（只保存子块，父块作为 metadata）
        
        Args:
            file_id: 文件ID
            file_name: 文件名
            node_school_ids: 节点学校ID列表
            space_id: 空间ID
            material_id: 素材ID
            chunk_result: chunk_document_with_hierarchy 返回的结果
                        包含 parent_chunks 和 child_chunks
            file_path: 文件绝对路径
        Returns:
            Dict: 处理结果统计
        """
        self.log_info("="*60)
        self.log_info("开始父子块批量向量化")
        self.log_info("="*60)
        
        # 提取子块
        child_chunks = chunk_result.get("child_chunks", [])
        parent_chunks = chunk_result.get("parent_chunks", [])
        
        self.log_info(f"父块数量: {len(parent_chunks)}")
        self.log_info(f"子块数量: {len(child_chunks)}")
        
        if not child_chunks:
            self.log_error("没有子块需要处理")
            return {"success": False, "error": "No child chunks"}
        
        success_count = 0
        failed_count = 0
        entities = []
        
        try:
            with self.vector_db as db:
                # 只向量化子块
                for i, child_chunk in enumerate(child_chunks):
                    try:
                        # 提取子块文本
                        child_text = child_chunk.page_content
                        # 文件扩展名
                        if file_extension is None:
                            file_extension = os.path.splitext(file_path)[1].lower()
                        else:
                            file_extension = file_extension
                        # 页码 - 确保始终有有效值
                        page_number = child_chunk.metadata.get("page_number")
                        # 显式处理None值，确保始终是整数
                        page_number = int(page_number) if page_number is not None else -1
                        self.log_info(f"子块文本: {child_text}，页码: {page_number}")
                        
                        # 提取 metadata 中的父块信息
                        parent_content = child_chunk.metadata.get("parent_content")
                        
                        # 向量化子块（用于检索）
                        vector = self.vector_db.text_to_vector(child_text)
                        
                        # 在构建 entity 前添加
                        child_text = child_chunk.page_content
                        # 强制截断，确保不超过 Milvus 限制
                        max_chunk_length = 3000
                        if len(child_text) > max_chunk_length:
                            child_text = child_text[:max_chunk_length]

                        # 构建实体（关键：包含父块内容）
                        entity = {
                            "file_id": file_id,
                            "file_name": file_name,
                            "material_id": material_id,
                            "file_extension": file_extension,
                            "page_number": page_number,
                            "node_school_ids": node_school_ids,
                            "space_id": space_id,
                            "chunk_content": child_text,
                            "embedding_vector": vector,  # 子块的向量
                            "parent_content": parent_content,  # 🔑 关键：存储完整父块
                            "create_timestamp": int(time.time()),
                            "is_searchable": True,
                            "material_school_ids": material_school_ids
                        }
                        
                        entities.append(entity)
                        success_count += 1
                        
                        if (i + 1) % 10 == 0:
                            self.log_info(f"进度: {i + 1}/{len(child_chunks)} 子块已向量化")
                            
                    except Exception as e:
                        self.log_error(f"子块 {i} 向量化失败", e)
                        failed_count += 1
                        continue
                
                # 批量保存
                if entities:
                    self.log_info(f"\n保存 {len(entities)} 个子块向量到数据库...")
                    try:
                        result = self.vector_db.insert_data(self.collection_name, entities)
                        self.log_info("✓ 批量保存成功")
                    except Exception as e:
                        self.log_error(f"✗ 批量保存失败, 失败原因：{e}")
                        failed_count = len(entities)
                        success_count = 0
                
                # 返回统计
                result = {
                    "success": success_count > 0,
                    "total_parent_chunks": len(parent_chunks),
                    "total_child_chunks": len(child_chunks),
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "entities_created": len(entities)
                }
                
                self.log_info("\n" + "="*60)
                self.log_info("父子块向量化完成:")
                self.log_info(f"  父块: {result['total_parent_chunks']}")
                self.log_info(f"  子块: {result['total_child_chunks']}")
                self.log_info(f"  成功: {result['success_count']}")
                self.log_info(f"  失败: {result['failed_count']}")
                self.log_info("="*60)
                
                return result
                
        except Exception as e:
            self.log_error("父子块批量向量化失败", e)
            return {
                "success": False,
                "total_child_chunks": len(child_chunks),
                "success_count": success_count,
                "failed_count": failed_count,
                "error": str(e)
            }

     


    def embedding_for_demo(self, file_id: str, file_name: str,
                          chunk_result: Dict,
                          file_extension: str = None,
                          category: str = None,
                          task_id: str = None) -> Dict:
        """
        演示专用的向量化方法（去除业务字段）
        
        Args:
            file_id: 文件ID（demo_xxxxx）
            file_name: 文件名
            chunk_result: chunk_document_with_hierarchy 返回的结果
            file_extension: 文件扩展名
            
        Returns:
            Dict: 处理结果统计和实体列表
        """
        self.log_info("="*60)
        self.log_info("[Demo] 开始父子块批量向量化")
        self.log_info("="*60)
        
        # 提取子块
        child_chunks = chunk_result.get("child_chunks", [])
        parent_chunks = chunk_result.get("parent_chunks", [])
        
        self.log_info(f"[Demo] 父块数量: {len(parent_chunks)}")
        self.log_info(f"[Demo] 子块数量: {len(child_chunks)}")
        
        if not child_chunks:
            self.log_error("[Demo] 没有子块需要处理")
            return {"success": False, "error": "No child chunks", "entities": []}
        
        success_count = 0
        failed_count = 0
        entities = []
        current_time = int(time.time())
        
        try:
            # 只向量化子块
            import uuid
            BATCH_SIZE = 10  # 百炼 API 限制最多 10 条
            for batch_start in range(0, len(child_chunks), BATCH_SIZE):
                batch_chunks = child_chunks[batch_start:batch_start + BATCH_SIZE]
                texts_to_embed = [chunk.page_content for chunk in batch_chunks]
                
                try:
                    batch_vectors = self.vector_db.texts_to_vectors(texts_to_embed)
                except Exception as e:
                    self.log_error(f"[Demo] 批次 {batch_start//BATCH_SIZE + 1} 向量化失败: {str(e)}")
                    failed_count += len(batch_chunks)
                    continue
                    
                for j, child_chunk in enumerate(batch_chunks):
                    try:
                        child_text = child_chunk.page_content
                        page_number = child_chunk.metadata.get("page_number")
                        page_number = int(page_number) if page_number is not None else 0
                        parent_content = child_chunk.metadata.get("parent_content", child_text)
                        
                        child_text = child_text[:3000] if len(child_text) > 3000 else child_text
                        parent_content = parent_content[:10000] if len(parent_content) > 10000 else parent_content
                        
                        vector = batch_vectors[j]
                        chunk_uuid = str(uuid.uuid4())
                        
                        entity = {
                            "chunk_id": chunk_uuid,
                            "file_id": file_id,
                            "file_name": file_name,
                            "file_extension": file_extension or "unknown",
                            "category": category or "",
                            "chunk_content": child_text,
                            "parent_content": parent_content,
                            "page_number": page_number,
                            "embedding_vector": vector,
                            "created_at": current_time,
                            "updated_at": current_time
                        }
                        entities.append(entity)
                        success_count += 1
                    except Exception as e:
                        self.log_error(f"[Demo] 子块组装失败: {e}")
                        failed_count += 1
                        continue
                
                progress = min(batch_start + BATCH_SIZE, len(child_chunks))
                self.log_info(f"[Demo] 进度: {progress}/{len(child_chunks)} 子块已批量向量化")
                
                if task_id:
                    # 30% 到 90% 之间表示向量化的进度
                    percent = 30 + int((progress / len(child_chunks)) * 60)
                    task_manager.set_task(task_id, {
                        "status": "processing",
                        "file_name": file_name,
                        "progress": percent,
                        "message": f"正在调用百炼模型向量化... ({progress}/{len(child_chunks)})"
                    })
            
            # 返回统计和实体
            result = {
                "success": success_count > 0,
                "total_parent_chunks": len(parent_chunks),
                "total_child_chunks": len(child_chunks),
                "success_count": success_count,
                "failed_count": failed_count,
                "entities": entities,  # 返回实体列表，由调用方决定是否保存
                "error": "所有子块向量化均失败，请查看日志中 '向量化失败' 的原因" if success_count == 0 else None
            }
            
            self.log_info("" + "="*60)
            self.log_info("[Demo] 向量化完成:")
            self.log_info(f"  父块: {result['total_parent_chunks']}")
            self.log_info(f"  子块: {result['total_child_chunks']}")
            self.log_info(f"  成功: {result['success_count']}")
            self.log_info(f"  失败: {result['failed_count']}")
            self.log_info("="*60)
            
            return result
            
        except Exception as e:
            self.log_error(f"[Demo] 批量向量化失败: {e}")
            return {
                "success": False,
                "total_child_chunks": len(child_chunks),
                "success_count": success_count,
                "failed_count": failed_count,
                "entities": entities,
                "error": str(e)
            }

    def __del__(self):
        """析构函数，确保资源释放"""
        if self.vector_db and hasattr(self.vector_db, 'disconnect'):
            try:
                self.vector_db.disconnect()
            except:
                pass
    
