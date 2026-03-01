import logging
import logging.handlers
import tempfile
from pathlib import Path

import pytest

from loom.logger import LoomLogger, OneLineFormatter


@pytest.fixture
def temp_log_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(autouse=True)
def cleanup_logger_instances():
    yield
    LoomLogger.clear_instances()


def test_logger_creation(temp_log_dir):
    logger = LoomLogger("test_logger", log_dir=temp_log_dir)
    assert logger.name == "test_logger"
    assert logger.level == logging.INFO
    assert isinstance(logger.logger, logging.Logger)


def test_singleton_pattern(temp_log_dir):
    logger1 = LoomLogger.get_logger("singleton_test", log_dir=temp_log_dir)
    logger2 = LoomLogger.get_logger("singleton_test", log_dir=temp_log_dir)
    assert logger1 is logger2
    assert logger1._logger is logger2._logger


def test_different_logger_names(temp_log_dir):
    logger1 = LoomLogger.get_logger("logger1", log_dir=temp_log_dir)
    logger2 = LoomLogger.get_logger("logger2", log_dir=temp_log_dir)
    assert logger1 is not logger2
    assert logger1.name != logger2.name


def test_custom_log_level(temp_log_dir):
    logger = LoomLogger(
        "debug_logger", level=logging.DEBUG, log_dir=temp_log_dir
    )
    assert logger.level == logging.DEBUG
    assert logger._logger.level == logging.DEBUG


def test_console_handler_only(temp_log_dir):
    logger = LoomLogger(
        "console_only",
        enable_console=True,
        enable_file=False,
        log_dir=temp_log_dir,
    )
    handlers = logger._logger.handlers
    assert len(handlers) == 1
    assert isinstance(handlers[0], logging.StreamHandler)
    assert not isinstance(handlers[0], logging.handlers.RotatingFileHandler)


def test_file_handler_only(temp_log_dir):
    logger = LoomLogger(
        "file_only",
        enable_console=False,
        enable_file=True,
        log_dir=temp_log_dir,
    )
    handlers = logger._logger.handlers
    assert len(handlers) == 1
    assert isinstance(handlers[0], logging.handlers.RotatingFileHandler)


def test_both_handlers(temp_log_dir):
    logger = LoomLogger(
        "both_handlers",
        enable_console=True,
        enable_file=True,
        log_dir=temp_log_dir,
    )
    handlers = logger._logger.handlers
    assert len(handlers) == 2


def test_log_file_creation(temp_log_dir):
    logger = LoomLogger("file_test", log_dir=temp_log_dir)
    logger.info("Test message")
    log_file = temp_log_dir / "file_test.log"
    assert log_file.exists()


def test_custom_log_filename(temp_log_dir):
    logger = LoomLogger(
        "custom_name", log_file="custom.log", log_dir=temp_log_dir
    )
    logger.info("Test message")
    log_file = temp_log_dir / "custom.log"
    assert log_file.exists()


def test_log_methods(temp_log_dir):
    logger = LoomLogger("methods_test", log_dir=temp_log_dir)

    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")

    log_file = temp_log_dir / "methods_test.log"
    content = log_file.read_text()

    assert "Info message" in content
    assert "Warning message" in content
    assert "Error message" in content
    assert "Critical message" in content


def test_exception_logging(temp_log_dir):
    logger = LoomLogger("exception_test", log_dir=temp_log_dir)

    try:
        raise ValueError("Test exception")
    except ValueError:
        logger.exception("Caught an exception")

    log_file = temp_log_dir / "exception_test.log"
    content = log_file.read_text()

    assert "Caught an exception" in content
    assert "ValueError" in content
    assert "Test exception" in content


def test_one_line_formatter():
    formatter = OneLineFormatter("%(message)s")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Line 1\nLine 2\n  Line 3",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    assert "\n" not in formatted
    assert "Line 1 Line 2 Line 3" in formatted


def test_one_line_file_format_enabled(temp_log_dir):
    logger = LoomLogger(
        "one_line_test",
        log_dir=temp_log_dir,
        one_line_file_format=True,
    )
    logger.info("Message with\nmultiple\nlines")

    log_file = temp_log_dir / "one_line_test.log"
    content = log_file.read_text()
    lines = content.strip().split("\n")

    assert len(lines) == 1
    assert "Message with multiple lines" in lines[0]


def test_one_line_file_format_disabled(temp_log_dir):
    logger = LoomLogger(
        "multi_line_test",
        log_dir=temp_log_dir,
        one_line_file_format=False,
    )
    logger.info("Single line message")

    log_file = temp_log_dir / "multi_line_test.log"
    content = log_file.read_text()

    assert "Single line message" in content


def test_file_rotation_config(temp_log_dir):
    logger = LoomLogger(
        "rotation_test",
        log_dir=temp_log_dir,
        max_file_size_mb=5,
        backup_count=3,
    )

    file_handler = None
    for handler in logger._logger.handlers:
        if isinstance(handler, logging.handlers.RotatingFileHandler):
            file_handler = handler
            break

    assert file_handler is not None
    assert file_handler.maxBytes == 5 * 1024 * 1024
    assert file_handler.backupCount == 3


def test_log_directory_creation(temp_log_dir):
    nested_dir = temp_log_dir / "nested" / "logs"
    logger = LoomLogger("nested_test", log_dir=nested_dir)
    logger.info("Test message")

    assert nested_dir.exists()
    assert (nested_dir / "nested_test.log").exists()


def test_clear_instances(temp_log_dir):
    _ = LoomLogger.get_logger("clear_test1", log_dir=temp_log_dir)
    _ = LoomLogger.get_logger("clear_test2", log_dir=temp_log_dir)

    assert len(LoomLogger._instances) == 2

    LoomLogger.clear_instances()

    assert len(LoomLogger._instances) == 0


def test_logger_propagate_disabled(temp_log_dir):
    logger = LoomLogger("propagate_test", log_dir=temp_log_dir)
    assert logger._logger.propagate is False


def test_no_duplicate_handlers(temp_log_dir):
    logger = LoomLogger.get_logger("duplicate_test", log_dir=temp_log_dir)
    initial_handler_count = len(logger._logger.handlers)

    same_logger = LoomLogger.get_logger("duplicate_test", log_dir=temp_log_dir)
    final_handler_count = len(same_logger._logger.handlers)

    assert initial_handler_count == final_handler_count


def test_logger_property_access(temp_log_dir):
    loom_logger = LoomLogger("property_test", log_dir=temp_log_dir)
    underlying_logger = loom_logger.logger

    assert isinstance(underlying_logger, logging.Logger)
    assert underlying_logger.name == "property_test"


def test_logger_with_existing_handlers(temp_log_dir):
    base_logger = logging.getLogger("existing_handlers_test")
    base_logger.addHandler(logging.NullHandler())

    loom_logger = LoomLogger("existing_handlers_test", log_dir=temp_log_dir)

    assert loom_logger._logger is base_logger
    handler_count = len(loom_logger._logger.handlers)
    assert handler_count >= 1


def test_clear_instances_with_incomplete_instance(temp_log_dir):
    _ = LoomLogger.get_logger("normal_logger", log_dir=temp_log_dir)

    class FakeInstance:
        pass

    LoomLogger._instances["fake_logger"] = FakeInstance()  # type: ignore[assignment]

    assert len(LoomLogger._instances) == 2

    LoomLogger.clear_instances()

    assert len(LoomLogger._instances) == 0
