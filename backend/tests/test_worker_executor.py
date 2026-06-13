"""Unit tests for workers.executor.InspectionExecutor and BatchExecutor."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from workers.models import InspectionResult


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# InspectionExecutor.execute — success path
# ---------------------------------------------------------------------------


class TestInspectionExecutorSuccess:
    @patch("workers.executor.SessionLocal")
    @patch("workers.executor.CaptureService")
    @patch("workers.executor.HealthCheckService")
    def test_returns_success_result(self, mock_health_cls, mock_capture_cls, mock_session_cls):
        mock_capture = MagicMock()
        mock_capture.capture = AsyncMock(return_value=MagicMock(image_bytes=b"snapshot"))
        mock_capture_cls.return_value = mock_capture

        mock_health = MagicMock()
        mock_health.check_camera = AsyncMock(return_value=None)
        mock_health_cls.return_value = mock_health

        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        from workers.executor import InspectionExecutor
        executor = InspectionExecutor()
        result = run(executor.execute(camera_id=1))

        assert isinstance(result, InspectionResult)
        assert result.camera_id == 1
        assert result.success is True
        assert result.image_bytes == b"snapshot"
        assert result.error is None
        assert result.duration_ms >= 0
        assert isinstance(result.timestamp, datetime)
        mock_db.close.assert_called_once()

    @patch("workers.executor.SessionLocal")
    @patch("workers.executor.CaptureService")
    @patch("workers.executor.HealthCheckService")
    def test_health_check_not_called_on_success(self, mock_health_cls, mock_capture_cls, mock_session_cls):
        mock_capture = MagicMock()
        mock_capture.capture = AsyncMock(return_value=MagicMock(image_bytes=b"img"))
        mock_capture_cls.return_value = mock_capture

        mock_health = MagicMock()
        mock_health.check_camera = AsyncMock()
        mock_health_cls.return_value = mock_health

        mock_session_cls.return_value = MagicMock()

        from workers.executor import InspectionExecutor
        executor = InspectionExecutor()
        run(executor.execute(camera_id=1))

        mock_health.check_camera.assert_not_called()


# ---------------------------------------------------------------------------
# InspectionExecutor.execute — failure path
# ---------------------------------------------------------------------------


class TestInspectionExecutorFailure:
    @patch("workers.executor.SessionLocal")
    @patch("workers.executor.CaptureService")
    @patch("workers.executor.HealthCheckService")
    def test_returns_failure_on_capture_error(self, mock_health_cls, mock_capture_cls, mock_session_cls):
        mock_capture = MagicMock()
        mock_capture.capture = AsyncMock(side_effect=RuntimeError("camera offline"))
        mock_capture_cls.return_value = mock_capture

        mock_health = MagicMock()
        mock_health.check_camera = AsyncMock(return_value=None)
        mock_health_cls.return_value = mock_health

        mock_session_cls.return_value = MagicMock()

        from workers.executor import InspectionExecutor
        executor = InspectionExecutor()
        result = run(executor.execute(camera_id=5))

        assert result.success is False
        assert "camera offline" in result.error
        assert result.image_bytes is None
        assert result.camera_id == 5

    @patch("workers.executor.SessionLocal")
    @patch("workers.executor.CaptureService")
    @patch("workers.executor.HealthCheckService")
    def test_health_check_called_on_failure(self, mock_health_cls, mock_capture_cls, mock_session_cls):
        mock_capture = MagicMock()
        mock_capture.capture = AsyncMock(side_effect=Exception("fail"))
        mock_capture_cls.return_value = mock_capture

        mock_health = MagicMock()
        mock_health.check_camera = AsyncMock(return_value=None)
        mock_health_cls.return_value = mock_health

        mock_session_cls.return_value = MagicMock()

        from workers.executor import InspectionExecutor
        executor = InspectionExecutor()
        run(executor.execute(camera_id=1))

        mock_health.check_camera.assert_called_once()

    @patch("workers.executor.SessionLocal")
    @patch("workers.executor.CaptureService")
    @patch("workers.executor.HealthCheckService")
    def test_health_check_failure_does_not_crash(self, mock_health_cls, mock_capture_cls, mock_session_cls):
        mock_capture = MagicMock()
        mock_capture.capture = AsyncMock(side_effect=Exception("capture fail"))
        mock_capture_cls.return_value = mock_capture

        mock_health = MagicMock()
        mock_health.check_camera = AsyncMock(side_effect=Exception("health fail"))
        mock_health_cls.return_value = mock_health

        mock_session_cls.return_value = MagicMock()

        from workers.executor import InspectionExecutor
        executor = InspectionExecutor()
        result = run(executor.execute(camera_id=1))

        # Should still return a failure result, not raise
        assert result.success is False
        assert "capture fail" in result.error

    @patch("workers.executor.SessionLocal")
    @patch("workers.executor.CaptureService")
    @patch("workers.executor.HealthCheckService")
    def test_db_closed_on_failure(self, mock_health_cls, mock_capture_cls, mock_session_cls):
        mock_capture = MagicMock()
        mock_capture.capture = AsyncMock(side_effect=Exception("fail"))
        mock_capture_cls.return_value = mock_capture

        mock_health = MagicMock()
        mock_health.check_camera = AsyncMock()
        mock_health_cls.return_value = mock_health

        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        from workers.executor import InspectionExecutor
        executor = InspectionExecutor()
        run(executor.execute(camera_id=1))

        mock_db.close.assert_called_once()


# ---------------------------------------------------------------------------
# InspectionExecutor — dependency injection
# ---------------------------------------------------------------------------


class TestInspectionExecutorInjection:
    @patch("workers.executor.SessionLocal")
    def test_custom_services_injected(self, mock_session_cls):
        mock_capture = MagicMock()
        mock_capture.capture = AsyncMock(return_value=MagicMock(image_bytes=b"custom"))
        mock_health = MagicMock()
        mock_health.check_camera = AsyncMock()

        mock_session_cls.return_value = MagicMock()

        from workers.executor import InspectionExecutor
        executor = InspectionExecutor(
            capture_service=mock_capture,
            health_service=mock_health,
        )
        result = run(executor.execute(camera_id=1))

        assert result.success is True
        assert result.image_bytes == b"custom"
        mock_capture.capture.assert_called_once()


# ---------------------------------------------------------------------------
# BatchExecutor.execute_batch
# ---------------------------------------------------------------------------


class TestBatchExecutor:
    def test_empty_list_returns_empty(self):
        from workers.executor import BatchExecutor
        executor = MagicMock(spec=[])
        batch = BatchExecutor(executor=None)
        # Patch the internal executor to avoid real imports
        batch._executor = MagicMock()
        result = run(batch.execute_batch([]))
        assert result == []

    @patch("workers.executor.SessionLocal")
    @patch("workers.executor.CaptureService")
    @patch("workers.executor.HealthCheckService")
    def test_single_camera(self, mock_health_cls, mock_capture_cls, mock_session_cls):
        mock_capture = MagicMock()
        mock_capture.capture = AsyncMock(return_value=MagicMock(image_bytes=b"img"))
        mock_capture_cls.return_value = mock_capture
        mock_health_cls.return_value = MagicMock()
        mock_session_cls.return_value = MagicMock()

        from workers.executor import BatchExecutor
        batch = BatchExecutor()
        results = run(batch.execute_batch([1]))

        assert len(results) == 1
        assert results[0].camera_id == 1
        assert results[0].success is True

    @patch("workers.executor.SessionLocal")
    @patch("workers.executor.CaptureService")
    @patch("workers.executor.HealthCheckService")
    def test_multiple_cameras(self, mock_health_cls, mock_capture_cls, mock_session_cls):
        mock_capture = MagicMock()
        mock_capture.capture = AsyncMock(return_value=MagicMock(image_bytes=b"img"))
        mock_capture_cls.return_value = mock_capture
        mock_health_cls.return_value = MagicMock()
        mock_session_cls.return_value = MagicMock()

        from workers.executor import BatchExecutor
        batch = BatchExecutor()
        results = run(batch.execute_batch([1, 2, 3]))

        assert len(results) == 3
        assert [r.camera_id for r in results] == [1, 2, 3]
        assert all(r.success for r in results)

    @patch("workers.executor.SessionLocal")
    @patch("workers.executor.CaptureService")
    @patch("workers.executor.HealthCheckService")
    def test_one_failure_does_not_affect_others(self, mock_health_cls, mock_capture_cls, mock_session_cls):
        call_count = 0

        async def mock_capture_fn(camera_id, db):
            nonlocal call_count
            call_count += 1
            if camera_id == 2:
                raise RuntimeError("camera 2 down")
            return MagicMock(image_bytes=f"cam{camera_id}".encode())

        mock_capture = MagicMock()
        mock_capture.capture = mock_capture_fn
        mock_capture_cls.return_value = mock_capture
        mock_health_cls.return_value = MagicMock()
        mock_session_cls.return_value = MagicMock()

        from workers.executor import BatchExecutor
        batch = BatchExecutor()
        results = run(batch.execute_batch([1, 2, 3]))

        assert len(results) == 3
        by_id = {r.camera_id: r for r in results}
        assert by_id[1].success is True
        assert by_id[2].success is False
        assert "camera 2 down" in by_id[2].error
        assert by_id[3].success is True

    @patch("workers.executor.SessionLocal")
    @patch("workers.executor.CaptureService")
    @patch("workers.executor.HealthCheckService")
    def test_executor_exception_isolation(self, mock_health_cls, mock_capture_cls, mock_session_cls):
        """If executor.execute itself raises (final isolation guard in BatchExecutor)."""
        mock_executor = MagicMock()
        mock_executor.execute = AsyncMock(side_effect=RuntimeError("unexpected"))

        from workers.executor import BatchExecutor
        batch = BatchExecutor(executor=mock_executor)
        results = run(batch.execute_batch([1]))

        assert len(results) == 1
        assert results[0].success is False
        assert "unexpected" in results[0].error
        assert results[0].duration_ms == 0.0
