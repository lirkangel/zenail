from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models.notification import Notification


class ProviderTransientError(Exception):
    """Retry with backoff."""


class ProviderPermanentError(Exception):
    """Do not retry."""


@dataclass
class ProviderResult:
    ok: bool
    detail: str = ""


class NotificationProvider(ABC):
    @abstractmethod
    async def send(self, notification: Notification, body: str, *, subject: str | None = None) -> ProviderResult: ...
