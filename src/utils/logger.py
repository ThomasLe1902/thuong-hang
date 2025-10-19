from datetime import datetime
import pytz
import logging
import os
from datetime import datetime
from pathlib import Path
from logging_loki import LokiHandler


def get_date_time():
    return datetime.now(pytz.timezone("Asia/Ho_Chi_Minh"))


class CoreCFG:
    PROJECT_NAME = "AI FTES"
    BOT_NAME = str("AI FTES")


def get_date_time():
    return datetime.now(pytz.timezone("Asia/Ho_Chi_Minh"))


DATE_TIME = get_date_time().date()
BASE_DIR = os.path.dirname(Path(__file__).parent.parent)
LOG_DIR = os.path.join(BASE_DIR, "logs")


class CustomFormatter(logging.Formatter):
    green = "\x1b[0;32m"
    grey = "\x1b[38;5;248m"
    yellow = "\x1b[38;5;229m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    blue = "\x1b[38;5;31m"
    white = "\x1b[38;5;255m"
    reset = "\x1b[38;5;15m"

    base_format = f"{grey}%(asctime)s | %(name)s | %(threadName)s | {{level_color}}%(levelname)-8s{grey} | {blue}%(module)s:%(lineno)d{grey} - {white}%(message)s"

    FORMATS = {
        logging.INFO: base_format.format(level_color=green),
        logging.WARNING: base_format.format(level_color=yellow),
        logging.ERROR: base_format.format(level_color=red),
        logging.CRITICAL: base_format.format(level_color=bold_red),
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def custom_logger(app_name="APP"):
    logger_r = logging.getLogger(name=app_name)
    # Set the timezone to Ho_Chi_Minh
    tz = pytz.timezone("Asia/Ho_Chi_Minh")

    logging.Formatter.converter = lambda *args: datetime.now(tz).timetuple()

    # Console handler with custom formatter
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(CustomFormatter())

    # File handler for local log files
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    file_handler = logging.FileHandler(
        os.path.join(LOG_DIR, f"{app_name}_{DATE_TIME}.log"), encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)-8s | %(module)s:%(lineno)d - %(message)s"
    )
    file_handler.setFormatter(file_formatter)

    # Loki handler for log aggregation
    # loki_url = os.getenv("LOKI_URL", "http://localhost:3100/loki/api/v1/push")
    loki_url = os.getenv("LOKI_URL", "http://loki:3100/loki/api/v1/push")
    environment = os.getenv("ENVIRONMENT", "development")

    try:
        loki_handler = LokiHandler(
            url=loki_url,
            tags={
                "application": app_name,
                "environment": environment,
                "host": os.getenv("HOSTNAME", "localhost"),
                "service": "ai-ftes-backend",
            },
            version="1",
        )
        loki_handler.setLevel(logging.INFO)
        loki_formatter = logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(module)s:%(lineno)d - %(message)s"
        )
        loki_handler.setFormatter(loki_formatter)
        logger_r.addHandler(loki_handler)
        print(f"✅ Loki handler configured successfully - URL: {loki_url}")
    except Exception as e:
        print(f"❌ Failed to setup Loki handler: {e}")

    logger_r.setLevel(logging.INFO)
    logger_r.addHandler(ch)
    logger_r.addHandler(file_handler)

    return logger_r


dev_mode = os.getenv("DEV", "false")
if dev_mode == "false":
    logger = custom_logger(app_name=CoreCFG.PROJECT_NAME)
else:
    from loguru import logger

    logger = logger
# from loguru import logger
# logger = logger
