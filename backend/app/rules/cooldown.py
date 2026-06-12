"""In-memory cooldown tracking for obstruction alerts."""

from __future__ import annotations

import time


class CooldownTracker:
    """Track last alert timestamps by ``(rule_id, roi_id)`` in memory."""

    def __init__(self) -> None:
        self._last_alert_at: dict[tuple[int, int], float] = {}

    def is_cooled_down(self, rule_id: int, roi_id: int, cooldown_seconds: float) -> bool:
        """Return whether a rule/ROI pair may alert at the current time."""
        last_alert_at = self._last_alert_at.get((rule_id, roi_id))
        if last_alert_at is None:
            return True
        return (time.time() - last_alert_at) >= cooldown_seconds

    def record_alert(self, rule_id: int, roi_id: int) -> None:
        """Record an alert for the current timestamp."""
        self._last_alert_at[(rule_id, roi_id)] = time.time()

    def cleanup(self, max_age_seconds: float = 3600) -> None:
        """Remove entries older than ``max_age_seconds``."""
        now = time.time()
        stale_keys = [
            key for key, last_alert_at in self._last_alert_at.items()
            if (now - last_alert_at) > max_age_seconds
        ]
        for key in stale_keys:
            del self._last_alert_at[key]
