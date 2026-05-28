"""Tests for Symphony backend fetch_messages pagination logic."""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatom.symphony.backend import SymphonyBackend


def _make_v4_message(message_id: str, timestamp_ms: int, user_id: int = 1001):
    """Create a mock V4Message-like object."""
    msg = SimpleNamespace()
    msg.message_id = message_id
    msg.message = f"<messageML>Message {message_id}</messageML>"
    msg.timestamp = timestamp_ms
    msg.user = SimpleNamespace(user_id=user_id)
    return msg


def _make_messages_in_range(start_ms: int, end_ms: int, count: int):
    """Create `count` messages evenly spaced between start_ms and end_ms."""
    if count == 0:
        return []
    step = (end_ms - start_ms) // max(count, 1)
    return [_make_v4_message(f"msg_{i}", start_ms + i * step) for i in range(count)]


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


@pytest.fixture
def backend():
    """Create a SymphonyBackend with mocked internals."""
    b = object.__new__(SymphonyBackend)
    b._bdk = MagicMock()
    b._bot_user_id_int = 9999
    b._stream_cache = {}
    b._connected = True
    return b


@pytest.fixture
def mock_list_messages(backend):
    """Set up the mock for message_service.list_messages."""
    msg_service = MagicMock()
    msg_service.list_messages = AsyncMock()
    backend._bdk.messages.return_value = msg_service
    return msg_service.list_messages


def _make_side_effect(all_messages):
    """Build a side_effect that simulates the Symphony API.

    Returns messages with timestamp >= since, oldest-first, paginated via skip/limit.
    """

    async def _side_effect(stream_id, since, skip=0, limit=500):
        matching = [m for m in all_messages if m.timestamp >= since]
        return matching[skip : skip + limit]

    return _side_effect


class TestFetchRecentMessages:
    """Test _fetch_recent_messages pagination logic."""

    def test_all_messages_fit_in_first_window(self, backend, mock_list_messages):
        """When the first 1h window has enough messages, return them directly."""
        now = datetime.now(timezone.utc)
        messages = _make_messages_in_range(
            _ms(now - timedelta(minutes=30)),
            _ms(now - timedelta(minutes=5)),
            30,
        )
        mock_list_messages.side_effect = _make_side_effect(messages)

        result = asyncio.run(backend._fetch_recent_messages("stream123", limit=30))

        assert len(result) == 30
        # Verify chronological order
        timestamps = [m.created_at for m in result]
        assert timestamps == sorted(timestamps)

    def test_messages_span_multiple_windows(self, backend, mock_list_messages):
        """When recent window is empty, widens backward to find messages."""
        now = datetime.now(timezone.utc)
        # Messages are 3 days old — first few windows will be empty
        old_messages = _make_messages_in_range(
            _ms(now - timedelta(days=3, hours=12)),
            _ms(now - timedelta(days=3)),
            20,
        )
        mock_list_messages.side_effect = _make_side_effect(old_messages)

        result = asyncio.run(backend._fetch_recent_messages("stream123", limit=20))

        assert len(result) == 20
        timestamps = [m.created_at for m in result]
        assert timestamps == sorted(timestamps)

    def test_no_duplicate_messages(self, backend, mock_list_messages):
        """Pagination must not return duplicate messages."""
        now = datetime.now(timezone.utc)
        all_messages = _make_messages_in_range(
            _ms(now - timedelta(days=2)),
            _ms(now - timedelta(hours=1)),
            100,
        )
        mock_list_messages.side_effect = _make_side_effect(all_messages)

        result = asyncio.run(backend._fetch_recent_messages("stream123", limit=50))

        ids = [m.id for m in result]
        assert len(ids) == len(set(ids)), f"Duplicate messages: {len(ids)} total, {len(set(ids))} unique"

    def test_returns_most_recent_messages(self, backend, mock_list_messages):
        """Result should be the MOST RECENT limit messages, not the oldest."""
        now = datetime.now(timezone.utc)
        all_messages = _make_messages_in_range(
            _ms(now - timedelta(minutes=30)),
            _ms(now - timedelta(minutes=1)),
            200,
        )
        mock_list_messages.side_effect = _make_side_effect(all_messages)

        result = asyncio.run(backend._fetch_recent_messages("stream123", limit=50))

        assert len(result) == 50
        expected_ids = {m.message_id for m in all_messages[-50:]}
        result_ids = {m.id for m in result}
        assert result_ids == expected_ids

    def test_fewer_messages_than_limit(self, backend, mock_list_messages):
        """If fewer messages exist than limit, return all of them."""
        now = datetime.now(timezone.utc)
        messages = _make_messages_in_range(
            _ms(now - timedelta(hours=6)),
            _ms(now - timedelta(minutes=10)),
            15,
        )
        mock_list_messages.side_effect = _make_side_effect(messages)

        result = asyncio.run(backend._fetch_recent_messages("stream123", limit=50))

        assert len(result) == 15

    def test_empty_channel(self, backend, mock_list_messages):
        """Empty channel returns empty list without infinite loop."""
        mock_list_messages.side_effect = _make_side_effect([])

        result = asyncio.run(backend._fetch_recent_messages("stream123", limit=50))

        assert result == []

    def test_backstop_prevents_infinite_pagination(self, backend, mock_list_messages):
        """Pagination stops at the 90-day backstop even if limit not reached."""
        mock_list_messages.side_effect = _make_side_effect([])

        result = asyncio.run(backend._fetch_recent_messages("stream123", limit=50))

        assert result == []
        # Should not make excessive calls — window doubles each time
        # 1h -> 2h -> 4h -> ... -> 2160h covers 90 days in ~12 doublings
        assert mock_list_messages.call_count <= 15

    def test_busy_channel_with_many_messages_per_hour(self, backend, mock_list_messages):
        """Channel with >500 messages per hour still returns correct most-recent."""
        now = datetime.now(timezone.utc)
        # 1000 messages in the last 30 minutes
        all_messages = _make_messages_in_range(
            _ms(now - timedelta(minutes=30)),
            _ms(now - timedelta(minutes=1)),
            1000,
        )
        mock_list_messages.side_effect = _make_side_effect(all_messages)

        result = asyncio.run(backend._fetch_recent_messages("stream123", limit=50))

        assert len(result) == 50
        expected_ids = {m.message_id for m in all_messages[-50:]}
        result_ids = {m.id for m in result}
        assert result_ids == expected_ids

    def test_chronological_order(self, backend, mock_list_messages):
        """Results are always in chronological (oldest-first) order."""
        now = datetime.now(timezone.utc)
        all_messages = _make_messages_in_range(
            _ms(now - timedelta(days=5)),
            _ms(now - timedelta(hours=1)),
            80,
        )
        mock_list_messages.side_effect = _make_side_effect(all_messages)

        result = asyncio.run(backend._fetch_recent_messages("stream123", limit=50))

        timestamps = [m.created_at for m in result]
        assert timestamps == sorted(timestamps)

    def test_skip_pagination_within_window(self, backend, mock_list_messages):
        """Verifies skip-based pagination fetches all messages in a large window."""
        now = datetime.now(timezone.utc)
        # 800 messages in the last 30 minutes — requires skip pagination
        all_messages = _make_messages_in_range(
            _ms(now - timedelta(minutes=30)),
            _ms(now - timedelta(minutes=1)),
            800,
        )
        mock_list_messages.side_effect = _make_side_effect(all_messages)

        result = asyncio.run(backend._fetch_recent_messages("stream123", limit=100))

        assert len(result) == 100
        expected_ids = {m.message_id for m in all_messages[-100:]}
        result_ids = {m.id for m in result}
        assert result_ids == expected_ids
        # Should have used skip pagination (at least 2 calls for 800 messages)
        assert mock_list_messages.call_count >= 2


class TestFetchMessagesSince:
    """Test _fetch_messages_since (the after= parameter path)."""

    def test_fetches_from_timestamp(self, backend, mock_list_messages):
        """Fetches messages after a given timestamp."""
        now = datetime.now(timezone.utc)
        messages = _make_messages_in_range(
            _ms(now - timedelta(hours=2)),
            _ms(now - timedelta(minutes=5)),
            10,
        )
        mock_list_messages.return_value = messages

        since_ms = _ms(now - timedelta(hours=3))
        result = asyncio.run(backend._fetch_messages_since("stream123", since_ms, limit=50))

        assert len(result) == 10
        mock_list_messages.assert_called_once_with(stream_id="stream123", since=since_ms, limit=50)


class TestFetchMessagesDispatch:
    """Test the public fetch_messages method dispatch logic."""

    def test_with_after_string_uses_since_path(self, backend, mock_list_messages):
        """When after= is a string timestamp, uses _fetch_messages_since."""
        mock_list_messages.return_value = []

        # Patch at class level to avoid pydantic __getattr__ issues
        with patch(
            "chatom.symphony.backend.SymphonyBackend._resolve_channel_id",
            new_callable=lambda: lambda: AsyncMock(return_value="stream123"),
        ):
            asyncio.run(backend._fetch_messages_since("stream123", 1716850000000, limit=10))

        mock_list_messages.assert_called_once_with(stream_id="stream123", since=1716850000000, limit=10)

    def test_without_after_uses_recent_path(self, backend, mock_list_messages):
        """When no after= is given, uses _fetch_recent_messages."""
        now = datetime.now(timezone.utc)
        messages = _make_messages_in_range(
            _ms(now - timedelta(minutes=10)),
            _ms(now - timedelta(minutes=1)),
            10,
        )
        mock_list_messages.side_effect = _make_side_effect(messages)

        result = asyncio.run(backend._fetch_recent_messages("stream123", limit=10))

        assert len(result) == 10
