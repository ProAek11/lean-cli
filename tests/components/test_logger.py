from unittest import mock

from _pytest.capture import CaptureFixture

from lean.components.logger import Logger


def assert_stdout_stderr(capsys: CaptureFixture, stdout: str, stderr: str) -> None:
    out, err = capsys.readouterr()
    assert out == stdout
    assert err == stderr


def test_logger_info_should_log_message_to_stdout(capsys: CaptureFixture) -> None:
    logger = Logger()
    logger.info("Message")

    assert_stdout_stderr(capsys, "Message\n", "")


def test_logger_info_should_not_add_newline_when_newline_is_false(capsys: CaptureFixture) -> None:
    logger = Logger()
    logger.info("Message", newline=False)

    assert_stdout_stderr(capsys, "Message", "")


def test_logger_error_should_log_message_to_stderr(capsys: CaptureFixture) -> None:
    logger = Logger()
    logger.error("Message")

    assert_stdout_stderr(capsys, "", "Message\n")


def test_logger_error_should_not_add_newline_when_newline_is_false(capsys: CaptureFixture) -> None:
    logger = Logger()
    logger.error("Message", newline=False)

    assert_stdout_stderr(capsys, "", "Message")


def test_logger_debug_should_log_message_to_stdout(capsys: CaptureFixture) -> None:
    logger = Logger()
    logger.enable_debug_logging()
    logger.debug("Message")

    assert_stdout_stderr(capsys, "Message\n", "")


def test_logger_debug_should_not_add_newline_when_newline_is_false(capsys: CaptureFixture) -> None:
    logger = Logger()
    logger.enable_debug_logging()
    logger.debug("Message", newline=False)

    assert_stdout_stderr(capsys, "Message", "")


def test_logger_debug_should_not_log_until_enable_debug_logging_is_called(capsys: CaptureFixture) -> None:
    logger = Logger()
    logger.debug("Message")

    assert_stdout_stderr(capsys, "", "")


@mock.patch("sys.stdout.flush")
def test_logger_flush_should_flush_stdout(flush) -> None:
    logger = Logger()
    logger.flush()

    flush.assert_called_once()


@mock.patch("sys.stderr.flush")
def test_logger_flush_should_flush_stderr(flush) -> None:
    logger = Logger()
    logger.flush()

    flush.assert_called_once()
