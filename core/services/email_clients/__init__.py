"""Factory for email client implementations."""

from core.services.email_clients.resend_client import ResendClient, get_resend_client

__all__ = ["ResendClient", "get_resend_client"]
