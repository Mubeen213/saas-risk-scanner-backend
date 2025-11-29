import logging

import colorlog


def setup_logging(level: str = "INFO") -> None:
    log_colors = {
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold_red",
    }

    formatter = colorlog.ColoredFormatter(
        fmt="%(asctime)s | %(log_color)s%(levelname)-8s%(reset)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors=log_colors,
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        handlers=[handler],
    )

    logging.getLogger("uvicorn").setLevel(logging.WARNING)
