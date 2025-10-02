from collections.abc import Sequence
from typing import Optional


class Logger:
    def info(
        self, message: str, *, category: Optional[str] = None, tags: Sequence[str] = []
    ) -> str:
        print(message, category, tags)

    def debug(
        self, message: str, *, category: Optional[str] = None, tags: Sequence[str] = []
    ) -> str:
        print(message, category, tags)

    def warning(
        self, message: str, *, category: Optional[str] = None, tags: Sequence[str] = []
    ) -> str:
        print(message, category, tags)

    def error(
        self, message: str, *, category: Optional[str] = None, tags: Sequence[str] = []
    ) -> str:
        print(message, category, tags)

    def critical(
        self, message: str, *, category: Optional[str] = None, tags: Sequence[str] = []
    ) -> str:
        print(message, category, tags)
