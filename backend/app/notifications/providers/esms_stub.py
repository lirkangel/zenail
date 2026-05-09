from app.models.notification import Notification
from app.notifications.providers.base import NotificationProvider, ProviderResult


class EsmsProvider(NotificationProvider):
    async def send(self, notification: Notification, body: str, *, subject: str | None = None) -> ProviderResult:
        raise NotImplementedError("eSMS provider not wired in phase 1")
