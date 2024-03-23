from loguru import logger


class PCRLogger:
    def __init__(self, name: str) -> None:
        self.name = name

    def exception(self, message: str, exception=True):
        return logger.opt(colors=True, exception=exception).exception(
            f"<r><y><b>{self.name}</b></> | {message}</>"
        )

    def error(self, message: str, exception=True):
        return logger.opt(colors=True, exception=exception).error(
            f"<r><y><b>{self.name}</b></> | {message}</>"
        )

    def critical(self, message: str):
        return logger.opt(colors=True).critical(
            f"<ly><y><b>{self.name}</b></y> | {message}</>"
        )

    def warning(self, message: str):
        return logger.opt(colors=True).warning(
            f"<ly><y><b>{self.name}</b></y> | {message}</>"
        )

    def success(self, message: str):
        return logger.opt(colors=True).success(f"<y><b>{self.name}</b></y> | {message}")

    def info(self, message: str):
        return logger.opt(colors=True).info(f"<y><b>{self.name}</b></y> | {message}")

    def debug(self, message: str):
        return logger.opt(colors=True).debug(f"<y><b>{self.name}</b></y> | {message}")
