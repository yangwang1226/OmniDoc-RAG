#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基础 Service
提供通用的服务层功能
"""

from typing import Any, Optional
import logging


class BaseService:
    """基础服务类"""
    
    def __init__(self):
        """初始化服务"""
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def log_info(self, message: str):
        """记录信息日志"""
        self.logger.info(message)
    
    def log_error(self, message: str, exception: Optional[Exception] = None):
        """记录错误日志"""
        if exception:
            error_msg = f"{message}: {str(exception)}"
            self.logger.error(error_msg, exc_info=True)
        else:
            self.logger.error(message)
    
    def log_warning(self, message: str):
        """记录警告日志"""
        self.logger.warning(message)

