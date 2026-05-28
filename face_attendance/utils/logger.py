"""
日志模块
提供统一的日志记录功能（控制台 + 文件轮转）
"""
import logging
import logging.handlers
import os
import config


def get_logger(name: str) -> logging.Logger:
    """
    获取日志记录器

    Args:
        name: 日志记录器名称（通常使用 __name__）

    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)

    # 避免重复添加handler
    if logger.handlers:
        return logger

    # 日志级别
    level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)

    # 控制台handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 文件handler (轮转)
    log_dir = os.path.join(config.BASE_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'face_attendance.log'),
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger