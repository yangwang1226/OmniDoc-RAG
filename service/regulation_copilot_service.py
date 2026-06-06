import json
import re
from typing import List, Dict
from service.llm_service import LLMService

class RegulationCopilotService:
    """
    规章制度伴写专属服务
    专注于构建企业管理制度伴写工作流的大模型提示词和结构化结果解析
    """
    
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service
        
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
        
        # 调用基础大模型
        response = self.llm.chat(
            user_message=user_message,
            system_message=system_prompt
        )
        
        try:
            json_match = re.search(r'```json\s*(.+?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response
            return json.loads(json_str)
        except Exception as e:
            self.llm.log_error("解析大纲JSON失败", e)
            return {
                "outline": [
                    {"chapter": "第一章 总则", "sub_topics": ["1.1 目的", "1.2 范围"]},
                    {"chapter": "第二章 基础管理", "sub_topics": ["解析失败或未提取到有效内容，请手动添加"]}
                ]
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
你的任务是：基于检索到的其他物业公司的历史档案片段，为我司起草/重写【特定领域的规章制度章节】。

起草要求：
1. 央企风格：必须使用严谨、规范的公文语言（如：严禁、应当、落实、台账、闭环管理等）。
2. 去粗取精：提取参考片段中的核心技术参数（如温度标准、频次要求），但剔除原公司特定的名称、不适用央企国资监管的违规流程。
3. 强化红线：在条款中务必突出“安全责任落实到人”和“合规留痕（台账记录）”。
4. 结构清晰：正文条款使用 1.1, 1.2 等条目式编写。

请以JSON格式返回，严格包含以下结构：
{
  "chapter_title": "建议的章节名称，例如：2. 暖通设备日常巡检管理",
  "draft_content": "起草的具体制度正文（条目式，清晰严谨，字数控制在400-800字之间）",
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
        
        response = self.llm.chat(
            user_message=user_message,
            system_message=system_prompt
        )
        
        try:
            json_match = re.search(r'```json\s*(.+?)\s*```', response, re.DOTALL)
            json_str = json_match.group(1) if json_match else response
            result = json.loads(json_str)
            return result
        except Exception as e:
            self.llm.log_error("伴写章节JSON解析失败", e)
            return {
                "chapter_title": chapter_title,
                "draft_content": response,
                "extracted_parameters": [],
                "human_review_needed": ["解析JSON失败，上方可能为原始输出"]
            }
