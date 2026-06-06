"""
工具模块
包含各种辅助工具函数
"""

from .console import setup_console_encoding, print_utf8


__all__ = [
    'setup_console_encoding', 
    'print_utf8',
    'KeywordMatcher',
    'quick_match',
    'quick_find_keywords',
    'ServiceDiscovery',
    'FeignClient',
    'feign_client',
    'get',
    'post',
    'put',
    'delete',
    'patch'
]

