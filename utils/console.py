#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
控制台输出工具
解决Windows终端中文乱码问题
"""

import sys
import os


def setup_console_encoding():
    """设置控制台编码为UTF-8"""
    if sys.platform == 'win32':
        # 设置控制台代码页为UTF-8
        os.system('chcp 65001 > nul')
        
        # 重新配置stdout和stderr为UTF-8
        if sys.stdout.encoding != 'utf-8':
            import io
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer,
                encoding='utf-8',
                errors='replace',
                line_buffering=True
            )
        
        if sys.stderr.encoding != 'utf-8':
            import io
            sys.stderr = io.TextIOWrapper(
                sys.stderr.buffer,
                encoding='utf-8',
                errors='replace',
                line_buffering=True
            )


def print_utf8(text):
    """
    安全地打印UTF-8文本
    
    Args:
        text: 要打印的文本
    """
    try:
        print(text)
    except UnicodeEncodeError:
        # 如果仍然出错，使用ASCII兼容模式
        print(text.encode('ascii', 'replace').decode('ascii'))


# 自动初始化
setup_console_encoding()

