"""로깅 설정 및 유틸리티.

구조화된 로그 포맷과 로거 인스턴스를 제공합니다.
"""

import logging
import sys
from typing import Any

# 로그 포맷 설정
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """로거 인스턴스를 생성하여 반환합니다.

    Args:
        name: 로거 이름 (일반적으로 __name__ 사용)
        level: 로그 레벨 (기본값: INFO)

    Returns:
        설정된 Logger 인스턴스

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("애플리케이션 시작")
    """
    logger = logging.getLogger(name)

    # 이미 핸들러가 설정되어 있으면 중복 설정 방지
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # 콘솔 핸들러 생성
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # 포매터 설정
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    console_handler.setFormatter(formatter)

    # 핸들러 추가
    logger.addHandler(console_handler)

    # 상위 로거로 전파 방지 (중복 로그 방지)
    logger.propagate = False

    return logger


def log_with_context(
    logger: logging.Logger, level: int, message: str, **context: Any
) -> None:
    """컨텍스트 정보와 함께 로그를 기록합니다.

    Args:
        logger: Logger 인스턴스
        level: 로그 레벨
        message: 로그 메시지
        **context: 추가 컨텍스트 정보 (key-value)

    Example:
        >>> logger = get_logger(__name__)
        >>> log_with_context(
        ...     logger,
        ...     logging.INFO,
        ...     "메시지 처리 완료",
        ...     session_id="abc123",
        ...     user_id="user1",
        ...     duration_ms=150
        ... )
    """
    context_str = " | ".join(f"{k}={v}" for k, v in context.items())
    full_message = f"{message} | {context_str}" if context else message
    logger.log(level, full_message)


# 기본 로거 인스턴스
_default_logger = get_logger("prototype")


def debug(message: str, **context: Any) -> None:
    """DEBUG 레벨 로그를 기록합니다."""
    log_with_context(_default_logger, logging.DEBUG, message, **context)


def info(message: str, **context: Any) -> None:
    """INFO 레벨 로그를 기록합니다."""
    log_with_context(_default_logger, logging.INFO, message, **context)


def warning(message: str, **context: Any) -> None:
    """WARNING 레벨 로그를 기록합니다."""
    log_with_context(_default_logger, logging.WARNING, message, **context)


def error(message: str, **context: Any) -> None:
    """ERROR 레벨 로그를 기록합니다."""
    log_with_context(_default_logger, logging.ERROR, message, **context)


def critical(message: str, **context: Any) -> None:
    """CRITICAL 레벨 로그를 기록합니다."""
    log_with_context(_default_logger, logging.CRITICAL, message, **context)
