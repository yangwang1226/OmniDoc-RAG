#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
大语言模型服务
基于 Azure OpenAI 提供聊天、总结等功能
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional, Generator, Union

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from service.base_service import BaseService
from config.env_loader import EnvLoader


class LLMService(BaseService):
    """大语言模型服务类"""
    
    def __init__(self, temperature: float = 0.7, streaming: bool = False):
        """
        初始化 LLM 服务 (支持 DashScope 和 Azure OpenAI 双引擎切换)
        """
        super().__init__()
        EnvLoader.load()
        provider = EnvLoader.get("LLM_PROVIDER", "dashscope").lower()
        
        if provider == "azure":
            from langchain_openai import AzureChatOpenAI
            self.api_key = EnvLoader.get("AZURE_OPENAI_API_KEY")
            self.endpoint = EnvLoader.get("AZURE_OPENAI_ENDPOINT")
            self.deployment = EnvLoader.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
            self.api_version = EnvLoader.get("OPENAI_API_VERSION", "2024-12-01-preview")
            
            if not self.api_key or not self.endpoint:
                raise ValueError("缺少 Azure OpenAI 配置！请检查 .env 文件。")
                
            self.llm = AzureChatOpenAI(
                azure_endpoint=self.endpoint,
                openai_api_key=self.api_key,
                azure_deployment=self.deployment,
                openai_api_version=self.api_version,
                temperature=temperature,
                streaming=streaming,
                max_tokens=4000,
                request_timeout=60
            )
            self.log_info(f"LLM 引擎: Azure OpenAI ({self.deployment})")
            
        else:
            self.api_key = EnvLoader.get("DASHSCOPE_API_KEY")
            self.endpoint = EnvLoader.get("LLM_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
            self.model_name = EnvLoader.get("LLM_MODEL_NAME", "qwen-plus")
            
            if not self.api_key:
                raise ValueError("缺少 DASHSCOPE_API_KEY 配置！请检查 .env 文件。")
                
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                base_url=self.endpoint,
                api_key=self.api_key,
                model=self.model_name,
                temperature=temperature,
                streaming=streaming,
                max_tokens=4000,
                request_timeout=60
            )
            self.log_info(f"LLM 引擎: 阿里百炼 ({self.model_name})")
      
    def chat(self, 
             user_message: str, 
             system_message: Optional[str] = None,
             history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        简单聊天接口
        
        Args:
            user_message: 用户消息
            system_message: 系统提示词（可选）
            history: 历史对话列表 [{"role": "user", "content": "..."}, ...]
            
        Returns:
            str: AI 回复内容
        """
        try:
            # 构建消息列表
            messages = []
            
            # 添加系统消息
            if system_message:
                messages.append(SystemMessage(content=system_message))
            
            # 添加历史消息
            if history:
                for msg in history:
                    role = msg.get("role")
                    content = msg.get("content")
                    if role == "user":
                        messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        messages.append(AIMessage(content=content))
            
            # 添加当前用户消息
            messages.append(HumanMessage(content=user_message))
            
            # 调用模型
            self.log_info(f"正在调用模型...")
            response = self.llm.invoke(messages)
            
            # 提取回复内容
            answer = response.content
            self.log_info(f"✓ 模型回复完成，长度: {len(answer)} 字符")
            
            return answer
            
        except Exception as e:
            self.log_error("模型调用失败", e)
            raise
    
    def chat_stream(self, 
                   user_message: str, 
                   system_message: Optional[str] = None,
                   history: Optional[List[Dict[str, str]]] = None) -> Generator[str, None, None]:
        """
        流式聊天接口
        
        Args:
            user_message: 用户消息
            system_message: 系统提示词（可选）
            history: 历史对话列表
            
        Yields:
            str: 流式返回的文本片段
        """
        try:
            # 构建消息列表
            messages = []
            
            if system_message:
                messages.append(SystemMessage(content=system_message))
            
            if history:
                for msg in history:
                    role = msg.get("role")
                    content = msg.get("content")
                    if role == "user":
                        messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        messages.append(AIMessage(content=content))
            
            messages.append(HumanMessage(content=user_message))
            
            # 流式调用
            self.log_info("正在流式调用模型...")
            for chunk in self.llm.stream(messages):
                if chunk.content:
                    yield chunk.content
            
            self.log_info("✓ 流式输出完成")
            
        except Exception as e:
            self.log_error("流式调用失败", e)
            raise
    
    def summarize_text(self, text: str, max_length: int = 200) -> str:
        """
        文本摘要
        
        Args:
            text: 需要总结的文本
            max_length: 摘要最大长度（字符数）
            
        Returns:
            str: 摘要内容
        """
        system_prompt = f"""你是一个专业的文本摘要助手。
请将用户提供的文本总结为不超过 {max_length} 字的摘要。
要求：
1. 提取核心要点
2. 语言简洁明了
3. 保留关键信息
4. 不超过指定长度"""
        
        return self.chat(
            user_message=f"请总结以下内容：\n\n{text}",
            system_message=system_prompt
        )
    
    def answer_with_context(self, 
                           question: str, 
                           contexts: List[str],
                           use_stream: bool = False) -> Union[str, Generator[str, None, None]]:
        """
        基于上下文回答问题（RAG 核心方法）
        """
        context_text = "\n\n".join([
            f"【参考资料 {i+1}】\n{ctx}" 
            for i, ctx in enumerate(contexts)
        ])
        
        system_prompt = """
你是一个专业的知识问答助手。
请根据提供的参考资料回答用户的问题。

要求：
1. 答案必须基于参考资料，不要编造信息
2. 如果参考资料中没有相关信息，请明确说明
3. 回答要准确、完整、易懂
4. 可以适当引用参考资料的内容，但禁止使用Markdown引用格式
5. 答案必须使用中文回答
6. 严格禁止使用任何Markdown格式
7. 直接输出纯文本答案，不要添加额外的格式修饰
"""

        user_message = f"""参考资料：
{context_text}

问题：{question}

请基于上述参考资料回答问题。"""
        
        if use_stream:
            return self.chat_stream(
                user_message=user_message,
                system_message=system_prompt
            )
        else:
            return self.chat(
                user_message=user_message,
                system_message=system_prompt
            )
    

    def answer_for_property_tender(self, 
                                  question: str, 
                                  contexts: List[str],
                                  use_stream: bool = False) -> Union[str, Generator[str, None, None]]:
        """
        专门针对企业内部档案检索场景的流式回答方法
        """
        context_text = "\n\n".join([
            f"【档案片段 {i+1}】\n{ctx}" 
            for i, ctx in enumerate(contexts)
        ])
        
        system_prompt = """
你是一位在大型国有企业担任资深业务分析师和知识管理专家的AI助手。
你深刻理解企业的日常运营、合同管理、安全生产合规、品质标准化等各类业务场景。

你的核心任务是：从海量的历史档案（合同、制度、会议纪要等）中，快速、精准地帮管理者和业务人员提取他们需要的条款、数据和经验，解决他们“查找资料耗时长”的痛点。

回答要求：
1. 精确客观：必须严格基于参考片段中的内容回答，绝不编造、不臆测。对于具体的人员配置、扣分标准、审批要求等，务必准确提取数值和条件。
2. 结构清晰：对复杂内容进行分类总结。如果是对比性问题，采用对比结构；如果是流程性问题，分步骤罗列。
3. 直击痛点：业务人员查档案往往是为了解决眼前的问题，你的回答要直接给到他们最关心的依据和结论。
4. 语言风格：专业、严谨、务实，符合国企公文和内部汇报的语境。不使用过度活泼或口语化的词汇。
5. 纯文本输出：绝不使用 Markdown 格式（不用井号、星号、减号、大于号等符号）。用纯文本的数字（1. 2. 3.）进行分段即可。

特别提醒：
- 当提取到具体的条款、数据、成功经验时，可以明确指出这有助于实际业务的落地。
- 如果参考内容中包含具体来源，可以在回答中自然带入，增强可信度。
"""

        user_message = f"""【内部档案片段】
{context_text}

【检索问题】{question}

请基于上述档案片段，给出精准、专业的业务分析或内容提取。"""
        
        if use_stream:
            return self.chat_stream(
                user_message=user_message,
                system_message=system_prompt
            )
        else:
            return self.chat(
                user_message=user_message,
                system_message=system_prompt
            )




    def generate_regulation_outline(self, topic: str, contexts: List[str]) -> Dict:
        """
        基于检索到的参考资料，生成规章制度的目录大纲
        """
        context_text = "\n\n".join([
            f"【参考片段 {i+1}】\n{ctx}" 
            for i, ctx in enumerate(contexts)
        ])
        
        system_prompt = """
你是一位在大型国有企业担任资深体系建设专家的AI助手。
你需要基于用户提供的内部档案片段，为一个特定的规章制度生成合理的目录大纲。

起草要求：
1. 结构完整：必须符合国企公文或规章制度的标准结构（通常包括：总则、管理职责/组织架构、具体业务流程与标准、应急与安全管理、监督与考核、附则等）。
2. 参考历史：必须尽最大努力从提供的参考片段中提取曾经出现过的核心业务环节，作为实际的章节。
3. 颗粒度适中：生成一级目录和关键的二级目录即可。

请以JSON格式返回，严格按照以下结构：
{
  "outline": [
    {
      "chapter": "第一章 总则",
      "sub_topics": ["1.1 目的与依据", "1.2 适用范围", "1.3 基本原则"]
    },
    {
      "chapter": "第二章 管理职责",
      "sub_topics": ["2.1 部门职责", "2.2 岗位职责"]
    }
  ]
}

注意：
- 必须返回合法的JSON字符串
- 不要凭空捏造脱离物业实际的无关模块。
"""

        user_message = f"""【要制定的制度名称/主题】{topic}

【相关历史档案片段】
{context_text}

请严格基于档案内容和国企规范，生成该制度的目录大纲。"""
        
        # 调用LLM获取回答
        response = self.chat(
            user_message=user_message,
            system_prompt=system_prompt
        )
        
        import json
        import re
        try:
            json_match = re.search(r'```json\s*(.+?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response
            
            return json.loads(json_str)
        except Exception as e:
            self.log_error("解析大纲JSON失败", e)
            return {
                "outline": [
                    {"chapter": "第一章 总则", "sub_topics": ["1.1 目的", "1.2 范围"]},
                    {"chapter": "第二章 基础管理", "sub_topics": ["内容解析失败，建议重新生成"]}
                ]
                        }

    def answer_for_property_tender_structured(self, 
                                             question: str, 
                                             contexts: List[str],
                                             context_metadata: List[Dict] = None) -> Dict:
        """
        企业内部知识库检索场景 - 返回结构化数据（包含原文摘录）
        """
        # 构建带元数据的参考资料
        enriched_contexts = []
        for i, ctx in enumerate(contexts):
            metadata = context_metadata[i] if context_metadata and i < len(context_metadata) else {}
            file_name = metadata.get('file_name', '内部档案')
            page_num = metadata.get('page_number', 0)
            
            source_info = f"（来源：{file_name}"
            if page_num > 0:
                source_info += f"，第{page_num}页"
            source_info += "）"
            
            enriched_contexts.append({
                'content': ctx,
                'source': source_info,
                'file_name': file_name,
                'page': page_num
            })
        
        context_text = "\n\n".join([
            f"【参考片段 {i+1}】{item['source']}\n{item['content']}" 
            for i, item in enumerate(enriched_contexts)
        ])
        
        system_prompt = """
你是一位在大型国有企业担任资深业务分析师和知识管理专家的AI助手。
你需要基于用户提供的内部档案片段，生成一个结构化的分析报告，以辅助管理层或业务人员快速决策。

请返回一个JSON结构，包含以下三部分：

1. 综合分析总结 (expert_summary)：
   - 200字左右的客观总结，直接回答用户的问题
   - 必须严格基于参考档案。如果涉及合同条款、扣分标准或流程规定，务必在此明确提炼出关键数据和步骤
   - 语气严谨、专业、务实

2. 原文关键摘录 (reusable_sections)：
   - 从档案片段中提取2-4段可以直接引用或复制执行的原文条款/规定
   - 必须保持档案的原始表述，不可篡改
   - 标注来源文件和页码
   - 给每段摘录起一个能概括其主旨的简短标题（如：保洁频次约定、危险作业审批条件）

3. 决策辅助建议 (additional_tips)：
   - 结合查到的档案，给出2-3条简短的执行建议或风险提示
   - 例如：检查合同履行时需注意的合规风险、制度落地时的监督建议等

请以JSON格式返回，严格按照以下结构：
{
  "expert_summary": "根据检索到的档案记录，...",
  "reusable_sections": [
    {
      "title": "XX合同关于保洁频次的约定",
      "content": "每日对大堂保洁不少于2次...",
      "source_file": "2023年XX外包合同.pdf",
      "page": 5
    }
  ],
  "additional_tips": [
    "建议在执行该条款时保存好巡查台账以备审计",
    "该制度要求必须在动火作业前24小时完成审批"
  ]
}

注意：
- 必须返回合法的JSON字符串
- 不要凭空捏造内容，必须基于提供的参考片段
"""

        user_message = f"""【检索问题】{question}

【相关内部档案片段】
{context_text}

请严格基于档案内容，生成结构化的分析报告。"""
        
        # 调用LLM获取回答
        response = self.chat(
            user_message=user_message,
            system_message=system_prompt
        )
        
        # 尝试解析JSON
        import json
        import re
        
        try:
            # 提取JSON部分（可能被包裹在markdown代码块中）
            json_match = re.search(r'```json\s*(.+?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 直接尝试解析整个响应
                json_str = response
            
            result = json.loads(json_str)
            
            # 补充元数据
            for section in result.get('reusable_sections', []):
                if 'source_file' not in section or not section['source_file']:
                    # 尝试从enriched_contexts匹配
                    for ctx in enriched_contexts:
                        if section['content'][:50] in ctx['content']:
                            section['source_file'] = ctx['file_name']
                            section['page'] = ctx['page']
                            break
            
            return result
            
        except Exception as e:
            # 如果解析失败，返回基本结构
            return {
                "expert_summary": response,
                "reusable_sections": [],
                "additional_tips": ["请手动查看相关文档片段获取更多信息"]
                        }

    def generate_regulation_clause_structured(self, main_topic: str, chapter_title: str, contexts: List[str], context_metadata: List[Dict] = None) -> Dict:
        """
        专门针对央国企规章制度生成场景，基于历史参考资料生成制度章节。
        """
        enriched_contexts = []
        for i, ctx in enumerate(contexts):
            metadata = context_metadata[i] if context_metadata and i < len(context_metadata) else {}
            file_name = metadata.get('file_name', '内部档案')
            page_num = metadata.get('page_number', 0)
            
            source_info = f"（来源：{file_name}"
            if page_num > 0:
                source_info += f"，第{page_num}页"
            source_info += "）"
            
            enriched_contexts.append({
                'content': ctx,
                'source': source_info,
                'file_name': file_name,
                'page': page_num
            })
        
        context_text = "\n\n".join([
            f"【参考片段 {i+1}】{item['source']}\n{item['content']}" 
            for i, item in enumerate(enriched_contexts)
        ])
        
        system_prompt = """
你是一位大型央国企物业公司的资深体系建设专家，深谙国企公文行文规范、安全生产法及高标准物业服务体系。
你的任务是：基于检索到的其他物业公司的历史档案片段，为我司起草或重写【特定领域的规章制度章节】。

起草要求：
1. 央企风格：必须使用严谨、规范的公文语言（如：严禁、应当、落实、台账、闭环管理等）。
2. 去粗取精：提取参考片段中的核心技术参数（如温度标准、频次要求），但剔除原公司特定的名称、不适用央企国资监管的违规流程。
3. 强化红线：在条款中务必突出“安全责任落实到人”和“合规留痕（台账记录）”。
4. 结构清晰：正文以自然段落形式编写，禁止添加任何数字章节编号（如 1.1、2.1、3.2.1 等），保持内容流畅连贯。

请以JSON格式返回，严格包含以下结构：
{
    "chapter_title": "建议的章节名称，例如：暖通设备日常巡检管理",
  "draft_content": "起草的具体制度正文（自然段落，禁止加数字编号，清晰严谨，字数控制在400-800字之间）",
  "extracted_parameters": ["提取到的核心参数1，例如：供水温度不低于XX度", "核心参数2"],
  "human_review_needed": ["列出需要人工确认或填写的空白项，例如：具体的处罚金额、最终审批层级等"]
}

注意：
- 必须返回合法的JSON字符串，不要有多余的话。
- 起草的内容必须能够体现出基于提供的参考片段。
"""

        user_message = f"""【总体制度背景/主课题】{main_topic}
【当前需要具体起草的章节】{chapter_title}

【检索到的相关历史参考片段】
{context_text}

请在【总体制度背景】的框架下，充分利用上述参考片段，专注为您起草【当前需要具体起草的章节】。
如果参考片段中没有任何与本章节相关的信息，请基于您的专业知识进行原创起草，并在返回时给出提示。"""
        
        response = self.chat(
            user_message=user_message,
            system_message=system_prompt
        )
        
        import json
        import re
        try:
            json_match = re.search(r'```json\s*(.+?)\s*```', response, re.DOTALL)
            json_str = json_match.group(1) if json_match else response
            result = json.loads(json_str)
            return result
        except Exception as e:
            self.log_error("JSON解析失败", e)
            return {
                "chapter_title": chapter_title,
                "draft_content": response,
                "extracted_parameters": [],
                "human_review_needed": ["解析失败，请手动检查大模型输出格式"]
                        }

    def extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """
        提取关键词
        """
        system_prompt = f"""你是一个关键词提取专家。
请从用户提供的文本中提取最重要的 {max_keywords} 个关键词。
只返回关键词，用逗号分隔，不要其他内容。"""
        
        response = self.chat(
            user_message=text,
            system_message=system_prompt
        )
        
        keywords = [kw.strip() for kw in response.split(",")]
        return keywords[:max_keywords]
    
    def generate_tags(self, content: str, max_tags: int = 5) -> List[str]:
        """
        为内容生成标签
        """
        system_prompt = f"""你是一个内容标签生成专家。
请为用户提供的内容生成 {max_tags} 个合适的标签。
标签要求：
1. 简洁明了（2-4个字）
2. 准确反映内容主题
3. 适合用于分类和检索
只返回标签，用逗号分隔。"""
        
        response = self.chat(
            user_message=content,
            system_message=system_prompt
        )
        
        tags = [tag.strip() for tag in response.split(",")]
        return tags[:max_tags]


def create_llm_service(temperature: float = 0.7, streaming: bool = False) -> LLMService:
    return LLMService(temperature=temperature, streaming=streaming)
