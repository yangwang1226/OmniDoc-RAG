"""
日志配置模块
提供统一的日志配置，支持同时输出到控制台和文件
"""
import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime


def setup_logging(
    log_level=logging.INFO,
    log_dir="logs",
    log_filename=None,
    console_output=True,
    file_output=True,
    max_bytes=10*1024*1024,  # 10MB
    backup_count=5
):
    """
    配置日志系统
    
    Args:
        log_level: 日志级别（默认 INFO）
        log_dir: 日志文件目录（默认 logs）
        log_filename: 日志文件名（默认使用日期）
        console_output: 是否输出到控制台（默认 True）
        file_output: 是否输出到文件（默认 True）
        max_bytes: 单个日志文件最大大小（默认 10MB）
        backup_count: 保留的日志文件数量（默认 5）
    """
    # 创建日志目录
    if file_output:
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)
    
    # 生成日志文件名
    if log_filename is None:
        today = datetime.now().strftime("%Y-%m-%d")
        log_filename = f"scrm-ai-knowledge-{today}.log"
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 清除已有的处理器（避免重复添加）
    root_logger.handlers.clear()
    
    # 定义日志格式
    # 控制台格式：简洁，带颜色支持
    console_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 文件格式：详细，包含更多信息
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 1. 控制台处理器
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # 2. 文件处理器（带日志轮转）
    if file_output:
        log_file_path = Path(log_dir) / log_filename
        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(log_file_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # 配置第三方库的日志级别（避免过多日志）
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    
    # 记录日志配置完成
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("日志系统初始化完成")
    logger.info(f"  日志级别: {logging.getLevelName(log_level)}")
    if console_output:
        logger.info("  控制台输出: 已启用")
    if file_output:
        logger.info(f"  文件输出: {log_file_path}")
        logger.info(f"  文件大小限制: {max_bytes / (1024*1024):.1f}MB")
        logger.info(f"  备份数量: {backup_count}")
    logger.info("=" * 60)


def get_logger(name=None):
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称（通常传入 __name__）
        
    Returns:
        logging.Logger: 日志记录器实例
    """
    return logging.getLogger(name)


# 在模块导入时自动初始化日志配置
if __name__ != "__main__":
    # 只在被导入时自动配置，测试时不自动配置
    setup_logging()


if __name__ == "__main__":
    # 测试日志配置
    setup_logging(log_level=logging.DEBUG)
    
    logger = get_logger(__name__)
    
    logger.debug("这是一条调试信息")
    logger.info("这是一条普通信息")
    logger.warning("这是一条警告信息")
    logger.error("这是一条错误信息")
    
    print("\n日志文件已创建在 logs 目录中")

