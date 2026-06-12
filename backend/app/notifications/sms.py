from __future__ import annotations

import abc
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class SMSNotifier(abc.ABC):
    """Abstract base for SMS notification providers.

    Subclass and implement :meth:`send` to plug in a real provider.
    The default :class:`StubSMSNotifier` simply logs the message.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    @abc.abstractmethod
    async def send(self, phone_numbers: list[str], message: str) -> bool:
        """Send *message* to every number in *phone_numbers*.

        Returns:
            True if *all* messages were accepted by the provider, False
            otherwise.
        """
        ...  # pragma: no cover


class StubSMSNotifier(SMSNotifier):
    """Stub implementation that logs SMS messages instead of sending them.

    Use this during development or when no SMS provider is configured.
    """

    async def send(self, phone_numbers: list[str], message: str) -> bool:
        for phone in phone_numbers:
            logger.info(
                "[SMS-Stub] To: %s | Message: %s",
                phone,
                message[:200],
            )
        return True


class TwilioSMSNotifier(SMSNotifier):
    """Twilio-based SMS notifier.

    Expected *config* keys:
        - ``account_sid``: Twilio Account SID
        - ``auth_token``:  Twilio Auth Token
        - ``from_number``:  Sender phone number (E.164 format)
        - ``base_url`` (optional): Override Twilio API base URL
    """

    _DEFAULT_BASE_URL = "https://api.twilio.com/2010-04-01"

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._account_sid: str = config.get("account_sid", "")
        self._auth_token: str = config.get("auth_token", "")
        self._from_number: str = config.get("from_number", "")
        base_url = config.get("base_url", self._DEFAULT_BASE_URL)
        self._client = httpx.AsyncClient(
            base_url=base_url,
            auth=(self._account_sid, self._auth_token),
            timeout=15.0,
        )

    async def send(self, phone_numbers: list[str], message: str) -> bool:
        if not self._account_sid or not self._auth_token or not self._from_number:
            logger.error("TwilioSMSNotifier: missing account_sid, auth_token, or from_number in config")
            return False

        all_ok = True
        for phone in phone_numbers:
            success = await self._send_single(phone, message)
            if not success:
                all_ok = False
        return all_ok

    async def _send_single(self, to: str, body: str) -> bool:
        url = f"/Accounts/{self._account_sid}/Messages.json"
        data = {"To": to, "From": self._from_number, "Body": body}
        try:
            logger.info("Twilio SMS to %s", to)
            response = await self._client.post(url, data=data)
            if response.status_code in (200, 201):
                logger.info("Twilio SMS sent to %s", to)
                return True
            logger.warning(
                "Twilio SMS failed for %s: HTTP %s — %s",
                to,
                response.status_code,
                response.text[:200],
            )
            return False
        except httpx.HTTPError as exc:
            logger.error("Twilio HTTP error for %s: %s", to, exc)
            return False
        except Exception as exc:  # pragma: no cover
            logger.exception("Twilio unexpected error for %s: %s", to, exc)
            return False

    async def close(self) -> None:
        await self._client.aclose()
