import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import colorlog


class OneLineFormatter(logging.Formatter):
    def format(self, record):
        original_message = super().format(record)
        single_line_message = " ".join(original_message.split())
        return single_line_message


class CustomLogger(logging.Logger):
    def __init__(
        self,
        name: str = "custom_logger",
        log_file: str = "clog.log",
        max_file_size: int = 10,
    ) -> None:
        super().__init__(name)
        self.log_filename = log_file
        self.max_file_size = max_file_size
        self.level = logging.DEBUG
        self.setLevel(self.level)

        self.set_console_handler()
        self.set_file_handler()

    def set_console_handler(self) -> None:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.level)
        console_formatter = colorlog.ColoredFormatter(
            "%(log_color)s %(name)s | %(levelname)s | %(process)s | %(asctime)s | %(message)s",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
            },
            reset=True,
            style="%",
            datefmt="%d-%m-%Y | %H:%M:%S",
        )
        console_handler.setFormatter(console_formatter)
        self.addHandler(console_handler)

    def set_file_handler(self) -> None:
        file_formatter = OneLineFormatter(
            "%(name)s | %(levelname)s | %(process)s | %(asctime)s | %(message)s",
            datefmt="%d-%m-%Y | %H:%M:%S",
        )

        folder = Path("logs")
        folder.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            filename=Path.joinpath(folder, self.log_filename),
            maxBytes=self.max_file_size * 1024 * 1024,
            backupCount=5,
        )
        file_handler.setFormatter(file_formatter)
        self.addHandler(file_handler)

    @classmethod
    def get_logger(cls, name: str, **kwargs) -> "CustomLogger":
        logging.setLoggerClass(cls)
        logger = cls(name, **kwargs)

        return logger

    @classmethod
    def __call__(cls, name: str, **kwargs) -> "CustomLogger":
        return cls.get_logger(name, **kwargs)
