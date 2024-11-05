import logging

from enum import StrEnum


class LoggingColor(StrEnum):
    DEBUG = "\033[34m"    # 파랑
    INFO = "\033[32m"     # 초록
    WARNING = "\033[33m"  # 노랑
    ERROR = "\033[31m"    # 빨강
    CRITICAL = "\033[41m" # 빨간 배경


class LoggingStyle(StrEnum):
    DEBUG = "\033[1m"         # 굵게
    INFO = "\033[3m"          # 이탤릭 (일부 터미널만 지원)
    WARNING = "\033[4m"       # 밑줄
    ERROR = "\033[1;31m"      # 굵은 빨강
    CRITICAL = "\033[1;41m"   # 굵은 흰 글씨에 빨강 배경


class LevelBasedFormatter(logging.Formatter):

    def __init__(self, fmt: str | None = None) -> None:
        super().__init__(fmt)
        self.formats = {
            logging.DEBUG: logging.Formatter(fmt),  # 굵게
            logging.INFO: logging.Formatter(fmt),
            logging.WARNING: logging.Formatter("\033[33m%(levelname)s - %(name)s - %(message)s\033[0m"),  # 노란색
            logging.ERROR: logging.Formatter("\033[31m%(levelname)s - %(name)s - %(message)s\033[0m"),    # 빨간색
            logging.CRITICAL: logging.Formatter("\033[1;41m%(levelname)s - %(name)s - %(message)s\033[0m")  # 빨간 배경
        }

    def format(self, record):
        # 레벨에 따라 다른 포맷 선택
        formatter = self.formats[record.levelno]
        return formatter.format(record)


class ArbiterLogger:
    def __init__(
        self,
        name: str,
        formatter: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level: int = logging.INFO
    ) -> None:
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.reset = "\033[0m"  # 기본 색상 (리셋)

        # 콘솔 핸들러와 포맷터 설정
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(LevelBasedFormatter(formatter))
        self.logger.addHandler(console_handler)

    def debug(self, message: str):
        self.logger.debug(
            f"{LoggingColor.DEBUG}{LoggingStyle.DEBUG}{message}{self.reset}"
        )

    def info(self, message: str):
        self.logger.info(
            f"{LoggingColor.INFO}{LoggingStyle.INFO}{message}{self.reset}"
        )

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str):
        self.logger.error(message)

    def critical(self, message: str):
        self.logger.critical(message)
