"""Console logging shared by startup and runtime diagnostics."""
import logging
import os
import sys
from contextlib import contextmanager
from time import perf_counter


def configure_logging():
    started = perf_counter()

    class ElapsedFilter(logging.Filter):
        def filter(self, record):
            record.elapsed = perf_counter() - started
            return True

    logger = logging.getLogger("martian_map")
    logger.setLevel(logging.DEBUG if os.environ.get("MARTIAN_MAP_LOG_LEVEL", "INFO").upper() == "DEBUG" else logging.INFO)
    logger.propagate = False
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(ElapsedFilter())
    handler.setFormatter(logging.Formatter(
        "[%(elapsed)8.2fs] %(levelname)-7s %(name)s | %(message)s"
    ))
    logger.addHandler(handler)

    def unhandled(exc_type, value, traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, value, traceback)
        else:
            logger.critical("Unhandled exception", exc_info=(exc_type, value, traceback))
    sys.excepthook = unhandled
    return logger


@contextmanager
def stage(logger, name):
    started = perf_counter()
    logger.info("Starting: %s", name)
    try:
        yield
    except Exception:
        logger.error("Failed: %s (%.2fs)", name, perf_counter() - started)
        raise
    else:
        logger.info("Finished: %s (%.2fs)", name, perf_counter() - started)
