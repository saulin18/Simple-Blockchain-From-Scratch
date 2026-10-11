

LOGGING_CONFIG = {
    "version": 1,
    # "disable_existing_loggers": True,
    "filters": {
        "request_context": {
            "()": "middlewares.RequestContextFilter",
        },
    },
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s"
        },
        "custom_formatter": {
            "format": "%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s"
        },
    },
    "handlers": {
        "default": {
            "formatter": "standard",
            "filters": ["request_context"],
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "stream_handler": {
            "formatter": "custom_formatter",
            "filters": ["request_context"],
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "file_handler": {
            "formatter": "custom_formatter",
            "filters": ["request_context"],
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "app.log",
            "maxBytes": 1024 * 1024 * 1,  # = 1MB
            "backupCount": 3,
        },
    },
    "loggers": {
        "uvicorn": {
            "handlers": ["default", "file_handler"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["stream_handler", "file_handler"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.error": {
            "handlers": ["stream_handler", "file_handler"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.asgi": {
            "handlers": ["stream_handler", "file_handler"],
            "level": "INFO",
            "propagate": False,
        },
        "core": {
            "handlers": ["stream_handler", "file_handler"],
            "level": "DEBUG",
            "propagate": False,
        },
        "main": {
            "handlers": ["stream_handler", "file_handler"],
            "level": "INFO",
            "propagate": False,
        },
        "middlewares": {
            "handlers": ["stream_handler", "file_handler"],
            "level": "INFO",
            "propagate": False,
        },
        "__main__": {
            "handlers": ["stream_handler", "file_handler"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
