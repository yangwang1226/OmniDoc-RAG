from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json
import time
import uuid
import asyncio
from typing import AsyncGenerator, Optional
import logging
from pydantic import BaseModel

from service.llm_service import LLMService
from vector_db import get_vector_db_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["2. 知识检索与问答"])
COLLECTION_NAME = "enterprise_knowledge_base"

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    stream: bool = False
    enable_answer: bool = True
    category: Optional[str] = None

async def search_stream_generator(
    query: str,
    top_k: int,
    enable_answer: bool,
    request_id: str,
    category: str = None
) -> AsyncGenerator[str, None]:
    """流式搜索并生成答案"""
    try:
        start_time = time.time()
        yield f"data: {json.dumps({'type': 'status', 'content': '正在向量化查询问题...'})}\n\n"
        
        vector_db = get_vector_db_client()
        vector_db.connect()
        query_vector = vector_db.text_to_vector(query)
        
        yield f"data: {json.dumps({'type': 'status', 'content': '正在从本地知识库检索相关片段...'})}\n\n"
        search_results = vector_db.search_vectors(
            collection_name=COLLECTION_NAME,
            query_vectors=[query_vector],
            top_k=top_k
        )
        
        results_data = []
        contexts = []
        if search_results and len(search_results) > 0:
            for hit in search_results[0]:
                res_item = {
                    "file_name": hit.get("file_name", ""),
                    "page_number": hit.get("page_number", 0),
                    "content": hit.get("chunk_content", ""),
                    "distance": round(float(hit.get("distance", 0.0)), 4)
                }
                results_data.append(res_item)
                contexts.append(res_item["content"])
        
        vector_db.disconnect()
        
        yield f"data: {json.dumps({'type': 'results', 'data': results_data})}\n\n"
        
        if enable_answer and contexts:
            yield f"data: {json.dumps({'type': 'status', 'content': '正在调用大模型生成专业解答...'})}\n\n"
            llm = LLMService(temperature=0.3, streaming=True)
            stream = llm.answer_for_property_tender(
                question=query,
                contexts=contexts
            )
            
            for chunk in stream:
                yield f"data: {json.dumps({'type': 'answer_chunk', 'content': chunk})}\n\n"
                await asyncio.sleep(0.01)
                
        stats = {
            "total_time": round(time.time() - start_time, 2)
        }
        yield f"data: {json.dumps({'type': 'done', 'stats': stats})}\n\n"
        
    except Exception as e:
        logger.error(f"[RAG] 搜索异常: {e}", exc_info=True)
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

@router.post("/search")
async def search_knowledge(request: SearchRequest):
    """企业知识库 RAG 检索接口"""
    request_id = str(uuid.uuid4())
    try:
        if request.stream:
            return StreamingResponse(
                search_stream_generator(request.query, request.top_k, request.enable_answer, request_id, request.category),
                media_type="text/event-stream"
            )
        else:
            # 非流式处理
            start_time = time.time()
            vector_db = get_vector_db_client()
            vector_db.connect()
            query_vector = vector_db.text_to_vector(request.query)
            
            search_results = vector_db.search_vectors(
                collection_name=COLLECTION_NAME,
                query_vectors=[query_vector],
                top_k=request.top_k
            )
            
            results_data = []
            contexts = []
            if search_results and len(search_results) > 0:
                for hit in search_results[0]:
                    res_item = {
                        "file_name": hit.get("file_name", ""),
                        "page_number": hit.get("page_number", 0),
                        "content": hit.get("chunk_content", ""),
                        "distance": round(float(hit.get("distance", 0.0)), 4)
                    }
                    results_data.append(res_item)
                    contexts.append(res_item["content"])
            
            vector_db.disconnect()
            
            structured_answer = None
            if request.enable_answer and contexts:
                llm = LLMService(temperature=0.3, streaming=False)
                structured_answer = llm.answer_for_property_tender_structured(
                    question=request.query,
                    contexts=contexts
                )
            
            return {
                "code": 200,
                "message": "success",
                "data": {
                    "query": request.query,
                    "results": results_data,
                    "answer": structured_answer,
                    "total": len(results_data),
                    "stats": {"total_time": round(time.time() - start_time, 2)}
                }
            }
            
    except Exception as e:
        logger.error(f"[RAG] 搜索异常: {e}", exc_info=True)
        return {"code": 500, "message": str(e)}
