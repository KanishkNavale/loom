import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Lock
from typing import ClassVar

import colorlog


class OneLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        original_message = super().format(record)
        return " ".join(original_message.split())


class LoomLogger:
    _instances: ClassVar[dict[str, "LoomLogger"]] = {}
    _lock: ClassVar[Lock] = Lock()

    def __init__(
        self,
        name: str,
        level: int = logging.INFO,
        log_dir: Path = Path("logs"),
        log_file: str | None = None,
        max_file_size_mb: int = 10,
        backup_count: int = 5,
        enable_console: bool = True,
        enable_file: bool = True,
        one_line_file_format: bool = True,
    ) -> None:
        self.name = name
        self.level = level
        self.log_dir = log_dir
        self.log_file = log_file or f"{name}.log"
        self.max_file_size_mb = max_file_size_mb
        self.backup_count = backup_count
        self.enable_console = enable_console
        self.enable_file = enable_file
        self.one_line_file_format = one_line_file_format

        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)
        self._logger.propagate = False

        if not self._logger.handlers:
            self._setup_handlers()

    @property
    def log_format(self) -> str:
        return (
            "%(name)s | %(levelname)s | %(process)s | %(asctime)s | %(message)s"
        )

    @property
    def date_format(self) -> str:
        return "%d-%m-%Y | %H:%M:%S"

    @property
    def log_colors(self) -> dict[str, str]:
        return {
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bold",
        }

    def _setup_handlers(self) -> None:
        if self.enable_console:
            self._add_console_handler()
        if self.enable_file:
            self._add_file_handler()

    def _add_console_handler(self) -> None:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.level)
        console_formatter = colorlog.ColoredFormatter(
            f"%(log_color)s{self.log_format}",
            log_colors=self.log_colors,
            reset=True,
            style="%",
            datefmt=self.date_format,
        )
        console_handler.setFormatter(console_formatter)
        self._logger.addHandler(console_handler)

    def _add_file_handler(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)

        formatter_class = (
            OneLineFormatter if self.one_line_file_format else logging.Formatter
        )
        file_formatter = formatter_class(
            self.log_format, datefmt=self.date_format
        )

        log_path = self.log_dir / self.log_file
        file_handler = RotatingFileHandler(
            filename=log_path,
            maxBytes=self.max_file_size_mb * 1024 * 1024,
            backupCount=self.backup_count,
        )
        file_handler.setLevel(self.level)
        file_handler.setFormatter(file_formatter)
        self._logger.addHandler(file_handler)

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    def debug(self, msg: str, *args, **kwargs) -> None:
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        self._logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs) -> None:
        self._logger.critical(msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs) -> None:
        self._logger.exception(msg, *args, **kwargs)

    @classmethod
    def get_logger(cls, name: str, **kwargs) -> "LoomLogger":
        with cls._lock:
            if name not in cls._instances:
                instance = cls(name, **kwargs)
                cls._instances[name] = instance
            return cls._instances[name]

    @classmethod
    def clear_instances(cls) -> None:
        with cls._lock:
            for instance in cls._instances.values():
                if hasattr(instance, "_logger"):
                    for handler in instance._logger.handlers[:]:
                        handler.close()
                        instance._logger.removeHandler(handler)
            cls._instances.clear()
