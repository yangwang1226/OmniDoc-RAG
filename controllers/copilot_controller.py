from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import uuid
import time
import logging
from pydantic import BaseModel
from typing import Dict, Any, Optional

from vector_db import get_vector_db_client
from service.llm_service import create_llm_service
from service.regulation_copilot_service import RegulationCopilotService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/copilot", tags=["规章制度伴写专属"])

DEMO_COLLECTION = "enterprise_knowledge_base"

class RegulationOutlineRequest(BaseModel):
    topic: str
    category: Optional[str] = None
    top_k: int = 10  # 稍微搜多一点，以便涵盖更多的业务结构

class RegulationChapterRequest(BaseModel):
    main_topic: str # 总的制度背景，如：暖通管理制度
    chapter_title: str  # 具体章节标题，如：2.1 部门职责
    top_k: int = 5
    category: Optional[str] = None  # 可限制在特定历史文档库中


@router.post("/generate-outline")
async def copilot_generate_outline(request: RegulationOutlineRequest):
    """生成规章制度的大纲目录"""
    request_id = str(uuid.uuid4())
    
    try:
        logger.info(f"[Copilot-{request_id}] 开始生成大纲，topic: {request.topic}")
        
        vector_db = get_vector_db_client()
        vector_db.connect()
        
        # 增加一些结构相关的提示词进行检索，更容易召回历史目录或总则片段
        enhanced_query = f"{request.topic} 目录 总则 管理规定 职责 考核标准"
        query_vector = vector_db.text_to_vector_dashscope_api(enhanced_query)
        
        expr = None
        if request.category:
            expr = f"category == '{request.category}'"
            
        search_results = vector_db.search_vectors(
            collection_name=DEMO_COLLECTION,
            query_vectors=[query_vector],
            top_k=request.top_k,
            output_fields=["chunk_content"],
            search_params={"metric_type": "COSINE", "params": {"nprobe": 10}},
            filter_expr=expr
        )
        
        vector_db.disconnect()
        
        contexts = []
        if search_results and len(search_results) > 0:
            for hit in search_results[0]:
                contexts.append(hit.get("chunk_content", ""))
                
        logger.info(f"[Copilot-{request_id}] 检索完成，找到 {len(contexts)} 条相关结构参考")
        
        # 调用大模型生成大纲
        base_llm = create_llm_service(temperature=0.3, streaming=False)
        copilot_service = RegulationCopilotService(base_llm)
        
        outline_data = copilot_service.generate_regulation_outline(
            topic=request.topic,
            contexts=contexts
        )
        
        return {
            "code": 200,
            "message": "大纲生成成功",
            "data": outline_data
        }
        
    except Exception as e:
        logger.error(f"[Copilot-{request_id}] 大纲生成异常: {e}", exc_info=True)
        return {"code": 500, "message": str(e)}


@router.post("/generate-regulation-chapter")
async def copilot_generate_regulation_chapter(request: RegulationChapterRequest):
    """基于历史资料生成某一领域的专业规章制度章节"""
    request_id = str(uuid.uuid4())
    try:
        start_time = time.time()
        logger.info(f"[Copilot-{request_id}] 开始起草章节, 主干: {request.main_topic}, 章节: {request.chapter_title}")
        
        # 1. 检索该主题相关的历史资料
        vector_db = get_vector_db_client()
        vector_db.connect()
        # 组合查询词，兼顾宏观与微观
        enhanced_query = f"{request.main_topic} {request.chapter_title}"
        query_vector = vector_db.text_to_vector_dashscope_api(enhanced_query)
        
        expr = None
        if request.category:
            expr = f"category == '{request.category}'"
            
        search_results = vector_db.search_vectors(
            collection_name=DEMO_COLLECTION,
            query_vectors=[query_vector],
            top_k=request.top_k,
            output_fields=["file_name", "chunk_content", "page_number"],
            search_params={"metric_type": "COSINE", "params": {"nprobe": 10}},
            filter_expr=expr
        )
        vector_db.disconnect()
        
        contexts = []
        context_metadata = []
        if search_results and len(search_results) > 0:
            for hit in search_results[0]:
                contexts.append(hit.get("chunk_content", ""))
                context_metadata.append({
                    'file_name': hit.get("file_name", ""),
                    'page_number': hit.get("page_number", 0)
                })
                
        logger.info(f"[Copilot-{request_id}] 检索完成，找到 {len(contexts)} 条相关参考，耗时 {time.time() - start_time:.2f}s")
        
        if not contexts:
            logger.warning(f"[Copilot-{request_id}] 未检索到片段，使用大模型纯原创能力起草。")
            
        # 2. 调用LLM生成制度草案
        base_llm = create_llm_service(temperature=0.3)
        copilot_service = RegulationCopilotService(base_llm)
        
        regulation_draft = copilot_service.generate_regulation_clause_structured(
            main_topic=request.main_topic,
            chapter_title=request.chapter_title,
            contexts=contexts,
            context_metadata=context_metadata
        )
        
        # 3. 对来源档案进行去重整理，准备传给前端展示
        unique_sources = []
        seen = set()
        for meta in context_metadata:
            file_name = meta.get('file_name', '未知文件')
            page_num = meta.get('page_number', 0)
            identifier = f"{file_name}_{page_num}"
            if identifier not in seen and file_name:
                seen.add(identifier)
                unique_sources.append({"file_name": file_name, "page_number": page_num})
        
        return {
            "code": 200,
            "message": "章节起草成功",
            "data": {
                "topic": request.chapter_title,
                "draft_result": regulation_draft,
                "sources": unique_sources,
                "stats": {
                    "time_cost": round(time.time() - start_time, 2)
                }
            }
        }
    except Exception as e:
        logger.error(f"[Copilot-{request_id}] 起草异常: {e}", exc_info=True)
        return {"code": 500, "message": str(e)}

@router.get('/sys_config')
async def get_sys_config():
    """获取系统前台展示配置"""
    from config.env_loader import EnvLoader
    display_type = EnvLoader.get('DISPLAY_TYPE', 'opensource').lower()
    return {
        "code": 200,
        "data": {
            "display_type": display_type
        }
    }

@router.get('/ui', response_class=HTMLResponse)
async def copilot_ui():
    """返回企业级智能知识伴写系统的前端主界面"""
    with open('frontend/index.html', 'r', encoding='utf-8') as f:
        return f.read()


from fastapi.responses import FileResponse
@router.get('/css/style.css')
async def copilot_css():
    return FileResponse('frontend/css/style.css')

@router.get('/js/app.js')
async def copilot_js():
    return FileResponse('frontend/js/app.js')

