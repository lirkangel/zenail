from __future__ import annotations

import logging

from app.models.notification import Notification
from app.notifications.providers.base import NotificationProvider, ProviderResult


_logger = logging.getLogger("zenail.notifications")


class LogProvider(NotificationProvider):
    async def send(
        self,
        notification: Notification,
        body: str,
        *,
        subject: str | None = None,
    ) -> ProviderResult:
        _logger.info(
            "notification.log_provider_send id=%s channel=%s template=%s to=%s subject=%r body=%r",
            notification.id,
            notification.channel.value,
            notification.template_key,
            notification.recipient_address,
            subject,
            body,
        )
        return ProviderResult(ok=True, detail="logged")
