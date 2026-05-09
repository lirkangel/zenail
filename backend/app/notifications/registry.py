from __future__ import annotations

from app.core.config import settings
from app.models.notification import NotificationChannel
from app.notifications.providers.base import NotificationProvider
from app.notifications.providers.esms_stub import EsmsProvider
from app.notifications.providers.log import LogProvider
from app.notifications.providers.smtp_stub import SmtpProvider
from app.notifications.providers.zalo_stub import ZaloZnsProvider


def _build_email_provider() -> NotificationProvider:
    if settings.notification_provider_email == "smtp":
        return SmtpProvider()
    return LogProvider()


def _build_sms_provider() -> NotificationProvider:
    if settings.notification_provider_sms == "esms":
        return EsmsProvider()
    return LogProvider()


def _build_zns_provider() -> NotificationProvider:
    if settings.notification_provider_zns == "zalo":
        return ZaloZnsProvider()
    return LogProvider()


def get_provider(channel: NotificationChannel) -> NotificationProvider:
    if channel == NotificationChannel.email:
        return _build_email_provider()
    if channel == NotificationChannel.sms:
        return _build_sms_provider()
    if channel == NotificationChannel.zalo_zns:
        return _build_zns_provider()
    raise ValueError(f"Unknown channel: {channel}")
