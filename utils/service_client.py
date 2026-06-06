"""
服务客户端
提供类似 Java OpenFeign 的声明式服务调用功能
"""
import random
import requests
from typing import Dict, Any, Optional, List, Callable
from functools import wraps
import logging
from nacos_client.nacos_client import Nacos_Client
from config import nacos_config

logger = logging.getLogger(__name__)


class ServiceDiscovery:
    """服务发现客户端"""
    
    def __init__(self):
        # 检查 Nacos 是否启用
        from config.env_loader import EnvLoader
        self.nacos_enabled = EnvLoader.get('NACOS_ENABLED', 'true').lower() == 'true'
        
        if not self.nacos_enabled:
            logger.warning("Nacos 已禁用，ServiceDiscovery 将无法使用")
            self.nacos_client = None
            self.group_name = None
            return
        
        nacos_client_wrapper = Nacos_Client()
        
        # 适配多命名空间架构：使用主命名空间（第一个）的客户端
        # 如果 clients 字典为空，说明初始化失败
        if not nacos_client_wrapper.clients:
            raise RuntimeError("Nacos 客户端初始化失败，未找到可用的命名空间客户端")
        
        # 使用配置的主命名空间
        from config import nacos_config
        primary_namespace = nacos_config.NACOS_NAMESPACE  # 第一个命名空间
        
        if primary_namespace in nacos_client_wrapper.clients:
            self.nacos_client = nacos_client_wrapper.clients[primary_namespace]
        else:
            # 如果主命名空间不存在，使用第一个可用的客户端
            self.nacos_client = next(iter(nacos_client_wrapper.clients.values()))
            logger.warning(
                f"未找到主命名空间 {primary_namespace} 的客户端，"
                f"使用第一个可用的命名空间"
            )
        
        self.group_name = nacos_config.NACOS_GROUP
        
        logger.info(
            f"ServiceDiscovery 初始化成功，"
            f"使用命名空间: {self._get_namespace_name()}"
        )
    
    def _get_namespace_name(self) -> str:
        """获取当前使用的命名空间名称（用于日志）"""
        for ns_name, client in Nacos_Client.clients.items():
            if client == self.nacos_client:
                return ns_name
        return "unknown"
    
    def get_service_instances(self, service_name: str) -> List[Dict[str, Any]]:
        """
        获取服务的所有健康实例
        
        Args:
            service_name: 服务名称
            
        Returns:
            List[Dict]: 服务实例列表
        """
        try:
            instances = self.nacos_client.list_naming_instance(
                service_name=service_name,
                group_name=self.group_name,
                healthy_only=True
            )
            
            if not instances or not instances.get('hosts'):
                logger.warning(f"未找到服务实例: {service_name}")
                return []
            
            # 过滤出健康的实例
            healthy_instances = [
                inst for inst in instances['hosts']
                if inst.get('healthy', False) and inst.get('enabled', True)
            ]
            
            logger.info(f"服务 {service_name} 有 {len(healthy_instances)} 个健康实例")
            return healthy_instances
            
        except Exception as e:
            logger.error(f"获取服务实例失败 [{service_name}]: {e}")
            return []
    
    def choose_instance(self, service_name: str, strategy: str = 'random') -> Optional[Dict[str, Any]]:
        """
        选择一个服务实例（负载均衡）
        
        Args:
            service_name: 服务名称
            strategy: 负载均衡策略 ('random', 'round_robin')
            
        Returns:
            Optional[Dict]: 选中的服务实例，如果没有可用实例则返回 None
        """
        instances = self.get_service_instances(service_name)
        
        if not instances:
            return None
        
        if strategy == 'random':
            return random.choice(instances)
        elif strategy == 'round_robin':
            # 简单的轮询实现
            if not hasattr(self, '_round_robin_index'):
                self._round_robin_index = {}
            
            index = self._round_robin_index.get(service_name, 0)
            instance = instances[index % len(instances)]
            self._round_robin_index[service_name] = (index + 1) % len(instances)
            return instance
        else:
            return random.choice(instances)
    
    def get_service_url(self, service_name: str, strategy: str = 'random') -> Optional[str]:
        """
        获取服务的基础URL
        
        Args:
            service_name: 服务名称
            strategy: 负载均衡策略
            
        Returns:
            Optional[str]: 服务的基础URL，例如 http://192.168.1.100:8080
        """
        instance = self.choose_instance(service_name, strategy)
        
        if not instance:
            logger.error(f"无法获取服务实例: {service_name}")
            return None
        
        ip = instance.get('ip')
        port = instance.get('port')
        
        # 检查是否使用 HTTPS（从元数据中获取）
        metadata = instance.get('metadata', {})
        protocol = metadata.get('protocol', 'http')
        
        url = f"{protocol}://{ip}:{port}"
        logger.debug(f"选择服务实例: {service_name} -> {url}")
        return url


class FeignClient:
    """
    声明式服务客户端（类似 OpenFeign）
    
    使用示例:
        @feign_client(service_name="user-service", path="/api/users")
        class UserClient:
            @get("/{user_id}")
            def get_user(self, user_id: int):
                pass
            
            @post("/")
            def create_user(self, user_data: dict):
                pass
    """
    
    def __init__(self, service_name: str, base_path: str = "", 
                 timeout: int = 30, load_balance: str = 'random'):
        """
        Args:
            service_name: 服务名称（在 Nacos 中注册的名称）
            base_path: 基础路径，例如 "/api"
            timeout: 请求超时时间（秒）
            load_balance: 负载均衡策略 ('random', 'round_robin')
        """
        self.service_name = service_name
        self.base_path = base_path.rstrip('/')
        self.timeout = timeout
        self.load_balance = load_balance
        self.service_discovery = ServiceDiscovery()
    
    def _get_base_url(self) -> str:
        """获取服务的基础URL"""
        url = self.service_discovery.get_service_url(
            self.service_name, 
            strategy=self.load_balance
        )
        if not url:
            raise Exception(f"无法获取服务 {self.service_name} 的实例")
        return url
    
    def _build_url(self, path: str, path_params: Dict = None) -> str:
        """构建完整的请求URL"""
        base_url = self._get_base_url()
        
        # 替换路径参数，例如 /users/{id} -> /users/123
        if path_params:
            for key, value in path_params.items():
                path = path.replace(f"{{{key}}}", str(value))
        
        full_path = f"{self.base_path}{path}"
        return f"{base_url}{full_path}"
    
    def request(self, method: str, path: str, **kwargs) -> Any:
        """
        发送 HTTP 请求
        
        Args:
            method: HTTP 方法 ('GET', 'POST', 'PUT', 'DELETE' 等)
            path: 请求路径
            **kwargs: 其他请求参数（params, json, headers 等）
            
        Returns:
            响应数据（自动解析 JSON）
        """
        # 提取路径参数
        path_params = kwargs.pop('path_params', {})
        
        # 构建URL
        url = self._build_url(path, path_params)
        
        # 设置默认超时
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
        
        # 设置默认请求头
        headers = kwargs.get('headers', {})
        if 'Content-Type' not in headers and method in ['POST', 'PUT', 'PATCH']:
            headers['Content-Type'] = 'application/json'
        kwargs['headers'] = headers
        
        try:
            logger.info(f"调用服务: {method} {url}")
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            
            # 尝试解析 JSON 响应
            try:
                return response.json()
            except:
                return response.text
                
        except requests.exceptions.RequestException as e:
            logger.error(f"服务调用失败: {method} {url}, 错误: {e}")
            raise
    
    def get(self, path: str, **kwargs) -> Any:
        """GET 请求"""
        return self.request('GET', path, **kwargs)
    
    def post(self, path: str, **kwargs) -> Any:
        """POST 请求"""
        return self.request('POST', path, **kwargs)
    
    def put(self, path: str, **kwargs) -> Any:
        """PUT 请求"""
        return self.request('PUT', path, **kwargs)
    
    def delete(self, path: str, **kwargs) -> Any:
        """DELETE 请求"""
        return self.request('DELETE', path, **kwargs)
    
    def patch(self, path: str, **kwargs) -> Any:
        """PATCH 请求"""
        return self.request('PATCH', path, **kwargs)


def feign_client(service_name: str, path: str = "", **client_kwargs):
    """
    装饰器：创建声明式服务客户端
    
    使用示例:
        @feign_client(service_name="user-service", path="/api")
        class UserServiceClient:
            pass
    """
    def decorator(cls):
        # 为类添加 FeignClient 实例
        client = FeignClient(service_name, path, **client_kwargs)
        cls._feign_client = client
        
        # 为类添加方法代理
        original_init = cls.__init__ if hasattr(cls, '__init__') else None
        
        def new_init(self, *args, **kwargs):
            if original_init:
                original_init(self, *args, **kwargs)
            self._client = client
        
        cls.__init__ = new_init
        return cls
    
    return decorator


# HTTP 方法装饰器
def http_method(method: str, path: str):
    """通用 HTTP 方法装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # 获取路径参数（从函数参数中提取）
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(self, *args, **kwargs)
            bound_args.apply_defaults()
            
            # 构建路径参数
            path_params = {}
            request_params = {}
            request_json = None
            
            for param_name, param_value in bound_args.arguments.items():
                if param_name == 'self':
                    continue
                
                # 检查参数是否在路径中
                if f"{{{param_name}}}" in path:
                    path_params[param_name] = param_value
                elif method in ['GET', 'DELETE']:
                    # GET/DELETE 参数作为查询参数
                    request_params[param_name] = param_value
                else:
                    # POST/PUT/PATCH 参数作为请求体
                    if request_json is None:
                        request_json = {}
                    request_json[param_name] = param_value
            
            # 准备请求参数
            kwargs_to_send = {
                'path_params': path_params
            }
            if request_params:
                kwargs_to_send['params'] = request_params
            if request_json:
                kwargs_to_send['json'] = request_json
            
            # 调用 FeignClient
            return self._client.request(method, path, **kwargs_to_send)
        
        return wrapper
    return decorator


def get(path: str):
    """GET 请求装饰器"""
    return http_method('GET', path)


def post(path: str):
    """POST 请求装饰器"""
    return http_method('POST', path)


def put(path: str):
    """PUT 请求装饰器"""
    return http_method('PUT', path)


def delete(path: str):
    """DELETE 请求装饰器"""
    return http_method('DELETE', path)


def patch(path: str):
    """PATCH 请求装饰器"""
    return http_method('PATCH', path)