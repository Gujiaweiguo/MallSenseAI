from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class WeComNotifier:
    """Sends alert notifications via WeCom (企业微信) group webhook."""

    def __init__(self, webhook_url: str) -> None:
        self._webhook_url = webhook_url
        self._client = httpx.AsyncClient(timeout=10.0)

    async def send(
        self,
        message: str,
        mentioned_list: list[str] | None = None,
    ) -> bool:
        """Send a plain-text message via the WeCom webhook.

        Args:
            message: Text content to send.
            mentioned_list: User IDs or mobile numbers to @-mention.
                            Use ``["@all"]`` to mention everyone.

        Returns:
            True if the webhook responded with errcode 0, False otherwise.
        """
        text_body: dict[str, Any] = {"content": message}
        if mentioned_list:
            text_body["mentioned_list"] = mentioned_list

        payload = {"msgtype": "text", "text": text_body}
        return await self._post(payload)

    async def send_markdown(self, content: str) -> bool:
        """Send a markdown-formatted message via the WeCom webhook.

        Args:
            content: Markdown content (WeCom subset).

        Returns:
            True on success, False on failure.
        """
        payload = {"msgtype": "markdown", "markdown": {"content": content}}
        return await self._post(payload)

    @staticmethod
    def format_alert(
        *,
        camera_name: str,
        severity: str,
        roi_name: str | None = None,
        timestamp: str | None = None,
        details: str | None = None,
    ) -> str:
        """Build a markdown-formatted alert message for WeCom.

        Returns:
            Markdown string suitable for ``send_markdown``.
        """
        parts = [
            f"### 🚨 告警通知",
            f"> **摄像头**: {camera_name}",
            f"> **严重级别**: {severity}",
        ]
        if roi_name:
            parts.append(f"> **区域**: {roi_name}")
        if timestamp:
            parts.append(f"> **时间**: {timestamp}")
        if details:
            parts.append(f"> **详情**: {details}")
        return "\n".join(parts)

    async def _post(self, payload: dict[str, Any]) -> bool:
        """POST *payload* to the webhook URL.  Returns True on success."""
        try:
            logger.info("WeCom POST %s  msgtype=%s", self._webhook_url[:60], payload.get("msgtype"))
            response = await self._client.post(self._webhook_url, json=payload)
            result = response.json()
            if result.get("errcode") == 0:
                logger.info("WeCom send success")
                return True
            logger.warning("WeCom send failed: %s", result.get("errmsg", "unknown"))
            return False
        except httpx.HTTPError as exc:
            logger.error("WeCom HTTP error: %s", exc)
            return False
        except Exception as exc:  # pragma: no cover
            logger.exception("WeCom unexpected error: %s", exc)
            return False

    async def close(self) -> None:
        """Gracefully close the underlying HTTP client."""
        await self._client.aclose()
