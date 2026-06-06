"""
Qdrant 适配器 - 兼容 MilvusClient 接口
"""
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any
import uuid

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from config.env_loader import EnvLoader
logger = logging.getLogger(__name__)

class QdrantAdapter:
    """
    Qdrant 适配器，提供与 MilvusClient 兼容的接口
    """
    
    def __init__(self):
        """初始化 Qdrant 客户端"""
        EnvLoader.load()
        
        self.client = None
        self.config = {
            'host': EnvLoader.get('QDRANT_HOST', 'localhost'),
            'port': int(EnvLoader.get('QDRANT_PORT', '6333'))
        }
        
        logger.info("QdrantAdapter 初始化完成")
    
    def connect(self) -> bool:
        """连接到 Qdrant"""
        try:
            self.client = QdrantClient(
                host=self.config['host'],
                port=self.config['port']
            )
            
            # 测试连接
            collections = self.client.get_collections()
            
            logger.info(f"✅ 已连接到 Qdrant")
            logger.info(f"  Host: {self.config['host']}")
            logger.info(f"  Port: {self.config['port']}")
            logger.info(f"  现有集合数: {len(collections.collections)}")
            
            return True
        except Exception as e:
            logger.error(f"❌ Qdrant 连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.client:
            self.client.close()
            self.client = None
            logger.info("Qdrant 连接已断开")
    
    def collection_exists(self, collection_name: str) -> bool:
        """检查集合是否存在"""
        try:
            self.client.get_collection(collection_name)
            return True
        except Exception:
            return False
    
    def create_collection(self, collection_name: str, dimension: int = 1536, **kwargs):
        """
        创建集合
        
        Args:
            collection_name: 集合名称
            dimension: 向量维度
        """
        try:
            if self.collection_exists(collection_name):
                logger.info(f"集合 {collection_name} 已存在")
                return True
            
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE)
            )
            logger.info(f"✅ 集合 {collection_name} 创建成功 (维度: {dimension})")
            return True
        except Exception as e:
            logger.error(f"创建集合失败: {e}")
            return False
    
    def insert_data(self, collection_name: str, data: List[Dict]) -> bool:
        """
        兼容 MilvusClient 的 insert_data 接口
        Args:
            collection_name: 集合名称
            data: 字典列表，每个字典是一条记录，包含 embedding_vector 和其他元数据
        """
        try:
            # 如果集合不存在，自动创建（1024维，因为使用百炼 API）
            if not self.collection_exists(collection_name):
                logger.info(f"集合 {collection_name} 不存在，自动创建")
                self.create_collection(collection_name, dimension=1024)
            
            vectors = []
            metadata = []
            ids = []
            
            for item in data:
                # 提取并移除向量字段
                item_copy = item.copy()
                vector = item_copy.pop('embedding_vector', None)
                if vector is None:
                    logger.warning("数据中没有 embedding_vector 字段")
                    continue
                
                # Qdrant 要求 ID 必须是严格的 UUID 格式字符串或整数
                # 原来的 chunk_id 如果不是 UUID 格式，会导致插入失败
                # 所以我们重新生成标准 UUID 作为主键，保留原 chunk_id 到 payload 中
                point_id = str(uuid.uuid4())
                
                vectors.append(vector)
                metadata.append(item_copy)
                ids.append(point_id)
                
            # 如果使用 points 方式插入
            points = []
            for i, (vector, meta) in enumerate(zip(vectors, metadata)):
                points.append(PointStruct(
                    id=ids[i],
                    vector=vector,
                    payload=meta
                ))
                
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            logger.info(f"✅ 成功插入 {len(points)} 条数据到 {collection_name}")
            return True
            
        except Exception as e:
            # 记录详细的异常信息，帮助排查问题
            logger.error(f"插入数据失败: {e}", exc_info=True)
            return False

    def insert_vectors(self, collection_name: str, vectors: List[List[float]], 
                      metadata: List[Dict], **kwargs) -> List[str]:
        """
        插入向量
        
        Args:
            collection_name: 集合名称
            vectors: 向量列表
            metadata: 元数据列表
            
        Returns:
            插入的 ID 列表
        """
        points = []
        ids = []
        
        for i, (vector, meta) in enumerate(zip(vectors, metadata)):
            # 生成唯一 ID
            point_id = str(uuid.uuid4())
            ids.append(point_id)
            
            points.append(PointStruct(
                id=point_id,
                vector=vector,
                payload=meta
            ))
        
        try:
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            logger.info(f"✅ 插入 {len(points)} 条向量到 {collection_name}")
            return ids
        except Exception as e:
            logger.error(f"插入向量失败: {e}")
            return []
    
    def search_vectors(self, collection_name: str, query_vectors: List[List[float]], 
                      top_k: int = 5, output_fields: List[str] = None,
                      filter_expr: str = None, search_params: Dict = None, **kwargs) -> List[List[Dict]]:
        """
        搜索向量
        
        Args:
            collection_name: 集合名称
            query_vectors: 查询向量列表
            top_k: 返回结果数量
            output_fields: 输出字段（Qdrant 会返回所有 payload）
            filter_expr: 过滤表达式（如 "category == 'xxx'"）
            
        Returns:
            搜索结果列表
        """
        results = []
        
        for query_vector in query_vectors:
            # 构建过滤条件
            query_filter = None
            if filter_expr:
                # 简单解析 filter_expr，如 "category == 'xxx'"
                try:
                    if "==" in filter_expr:
                        field, value = filter_expr.split("==")
                        field = field.strip()
                        value = value.strip().strip("'\"")
                        query_filter = Filter(
                            must=[FieldCondition(key=field, match=MatchValue(value=value))]
                        )
                except Exception as e:
                    logger.warning(f"解析过滤条件失败: {e}")
            
            try:
                # 执行搜索（兼容新版 qdrant-client API）
                search_result = self.client.query_points(
                    collection_name=collection_name,
                    query=query_vector,
                    limit=top_k,
                    query_filter=query_filter
                ).points
                
                # 转换结果格式，兼容 Milvus 格式
                hits = []
                for hit in search_result:
                    result_dict = {
                        'id': hit.id,
                        'distance': hit.score,  # Qdrant 用 score，Milvus 用 distance
                        **hit.payload
                    }
                    hits.append(result_dict)
                
                results.append(hits)
                
            except Exception as e:
                logger.error(f"搜索失败: {e}")
                results.append([])
        
        return results
    
    # ================= 向量化双引擎支持 =================
    
    def text_to_vector(self, text: str) -> list[float]:
        """统一单文本向量化入口"""
        from config.env_loader import EnvLoader
        provider = EnvLoader.get("LLM_PROVIDER", "dashscope").lower()
        if provider == "azure":
            return self.text_to_vector_azure_api(text)
        else:
            return self.text_to_vector_dashscope_api(text)

    def texts_to_vectors(self, texts: list[str]) -> list[list[float]]:
        """统一批量文本向量化入口"""
        from config.env_loader import EnvLoader
        provider = EnvLoader.get("LLM_PROVIDER", "dashscope").lower()
        if provider == "azure":
            return self.texts_to_vectors_azure_api(texts)
        else:
            return self.texts_to_vectors_dashscope_api(texts)

    def text_to_vector_azure_api(self, text: str) -> list[float]:
        """Azure 单文本向量化"""
        return self.texts_to_vectors_azure_api([text])[0]

    def texts_to_vectors_azure_api(self, texts: list[str]) -> list[list[float]]:
        """Azure 批量文本向量化"""
        if not texts:
            return []
        import requests
        from config.env_loader import EnvLoader
        
        api_key = EnvLoader.get("AZURE_OPENAI_API_KEY")
        base_url = EnvLoader.get("AZURE_OPENAI_ENDPOINT")
        model = EnvLoader.get("QWEN_EMBEDDING_MODEL", "text-embedding-v4")
        
        if not api_key or not base_url:
            raise ValueError("缺少 AZURE_OPENAI 向量化配置")
            
        url = f"{base_url}v1/embeddings" if base_url.endswith('/') else f"{base_url}/v1/embeddings"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": model, "input": texts}
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            if response.status_code == 200:
                data = response.json().get('data', [])
                data.sort(key=lambda x: x['index'])
                return [item['embedding'] for item in data]
            else:
                raise ValueError(f"Azure API 失败: {response.text}")
        except Exception as e:
            logger.error(f"Azure 批量向量化失败: {e}")
            raise e

    # ================= 下面保留原先的 dashscope 向量化逻辑 =================

    def text_to_vector_dashscope_api(self, text: str) -> List[float]:
        """
        单条文本转向量（阿里云百炼 API）
        """
        try:
            import dashscope
            from dashscope import TextEmbedding
            from config.env_loader import EnvLoader
            
            api_key = EnvLoader.get("DASHSCOPE_API_KEY")
            if not api_key:
                raise ValueError("缺少 DASHSCOPE_API_KEY 配置")
            dashscope.api_key = api_key
            
            response = TextEmbedding.call(
                model=TextEmbedding.Models.text_embedding_v3,
                input=text,
                dimension=1024
            )
            
            if response.status_code == 200:
                return response.output['embeddings'][0]['embedding']
            else:
                raise ValueError(f"DashScope API 调用失败: {response.message}")
        except Exception as e:
            logger.error(f"单条文本向量化失败: {str(e)}")
            raise

    def texts_to_vectors_dashscope_api(self, texts: List[str]) -> List[List[float]]:
        """
        【批量版】使用阿里云百炼 API 批量将文本转换为向量
        每次最多支持 25 个文本
        """
        if not texts:
            return []
            
        try:
            import dashscope
            from dashscope import TextEmbedding
            from config.env_loader import EnvLoader
            
            api_key = EnvLoader.get("DASHSCOPE_API_KEY")
            if not api_key:
                raise ValueError("缺少 DASHSCOPE_API_KEY 配置")
            dashscope.api_key = api_key
            
            response = TextEmbedding.call(
                model=TextEmbedding.Models.text_embedding_v3,
                input=texts,
                dimension=1024
            )
            
            if response.status_code == 200:
                embeddings_info = response.output['embeddings']
                embeddings_info.sort(key=lambda x: x['text_index'])
                return [item['embedding'] for item in embeddings_info]
            else:
                raise ValueError(f"DashScope API 批量调用失败: {response.message}")
                
        except Exception as e:
            logger.error(f"批量文本向量化失败: {str(e)}")
            raise

    # 保留旧方法名以防有遗漏的调用，重定向到新方法
    def text_to_vector_qwen_api(self, text: str) -> List[float]:
        return self.text_to_vector_dashscope_api(text)
    
    def delete_by_ids(self, collection_name: str, ids: List[str], **kwargs):
        """删除向量"""
        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=ids
            )
            logger.info(f"✅ 删除了 {len(ids)} 条记录")
        except Exception as e:
            logger.error(f"删除失败: {e}")
    
    def drop_collection(self, collection_name: str):
        """删除集合"""
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"✅ 集合 {collection_name} 已删除")
        except Exception as e:
            logger.error(f"删除集合失败: {e}")
    
    def get_collection_stats(self, collection_name: str) -> Dict:
        """获取集合统计信息"""
        try:
            collection_info = self.client.get_collection(collection_name)
            return {
                'row_count': collection_info.points_count,
                'collection_name': collection_name
            }
        except Exception as e:
            logger.error(f"获取集合统计失败: {e}")
            return {}


if __name__ == "__main__":
    # 测试代码
    print("测试 Qdrant 适配器...")
    
    adapter = QdrantAdapter()
    
    # 连接
    if adapter.connect():
        print("✅ 连接成功")
        
        # 创建测试集合
        test_collection = "test_collection"
        adapter.create_collection(test_collection, dimension=3)
        
        # 插入测试数据
        test_vectors = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
        test_metadata = [
            {"text": "测试1", "category": "A"},
            {"text": "测试2", "category": "B"}
        ]
        
        ids = adapter.insert_vectors(test_collection, test_vectors, test_metadata)
        print(f"✅ 插入成功，IDs: {ids}")
        
        # 搜索
        results = adapter.search_vectors(test_collection, [[1.0, 2.0, 3.0]], top_k=2)
        print(f"✅ 搜索结果: {results}")
        
        # 清理
        adapter.drop_collection(test_collection)
        adapter.disconnect()
        print("✅ 测试完成")